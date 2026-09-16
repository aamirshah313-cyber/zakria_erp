#ifndef ZAKARIA_DESKTOP_SERVICE_H_
#define ZAKARIA_DESKTOP_SERVICE_H_
#include <windows.h>
#include <winhttp.h>
#include <filesystem>
#include <fstream>
#include <string>

// Lifetime belongs to this native window; do not reuse or terminate a service
// belonging to another application. A job cleans up the owned child on exit.
class DesktopService {
 public:
  ~DesktopService() {
    if (job_) CloseHandle(job_);
    if (process_) CloseHandle(process_);
    if (mutex_) CloseHandle(mutex_);
  }

  bool Start() {
    wchar_t buffer[32768];
    DWORD length = GetModuleFileNameW(nullptr, buffer, 32768);
    if (!length || length == 32768) return Fail(L"Cannot locate the application folder.");
    const auto folder = std::filesystem::path(buffer).parent_path();
    SetCurrentDirectoryW(folder.c_str());
    const auto backend = folder / L"backend" / L"zakaria_service.exe";
    const auto config = folder / L"data-directory.txt";
    if (!std::filesystem::exists(backend) && !std::filesystem::exists(config)) {
      return true;  // Developer client without the packaged service.
    }
    mutex_ = CreateMutexW(nullptr, TRUE, L"Local\\ZakariaERP-V2-Native");
    if (!mutex_ || GetLastError() == ERROR_ALREADY_EXISTS) {
      return Fail(L"Zakaria ERP is already open. Use the existing application window.");
    }
    std::ifstream input(config, std::ios::binary);
    std::string encoded;
    std::getline(input, encoded);
    if (!encoded.empty() && encoded.back() == '\r') encoded.pop_back();
    const int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, encoded.data(), static_cast<int>(encoded.size()), nullptr, 0);
    if (!count || !std::filesystem::exists(backend)) return Fail(L"The desktop package is incomplete. Keep its backend, data and DLL folders together.");
    std::wstring data(count, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, encoded.data(), static_cast<int>(encoded.size()), data.data(), count);
    if (data.find(L'"') != std::wstring::npos || !std::filesystem::path(data).is_absolute()) return Fail(L"The V2 data-folder configuration is invalid.");
    // Refuse a occupied port rather than attaching to an unrelated local server.
    if (Healthy()) return Fail(L"A desktop service is already using port 8765. Close the earlier desktop service before opening this package.");
    job_ = CreateJobObjectW(nullptr, nullptr);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job_ || !SetInformationJobObject(job_, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) return Fail(L"Cannot prepare the private desktop service.");
    std::wstring command = L"\"" + backend.wstring() + L"\" --data-dir \"" + data + L"\" --port 8765";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(backend.c_str(), command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr, folder.c_str(), &startup, &process)) return Fail(L"Cannot start the bundled desktop service. Check that the complete package was extracted.");
    process_ = process.hProcess;
    if (!AssignProcessToJobObject(job_, process_)) {
      TerminateProcess(process_, 1);
      CloseHandle(process.hThread);
      return Fail(L"Cannot attach the private service to this application.");
    }
    ResumeThread(process.hThread);
    CloseHandle(process.hThread);
    for (int attempt = 0; attempt < 90; ++attempt) {
      if (WaitForSingleObject(process_, 0) == WAIT_OBJECT_0) break;
      if (Healthy()) return true;
      Sleep(300);
    }
    return Fail(L"The desktop service could not become ready. Check the V2 data-folder configuration and database upgrade before retrying.");
  }

 private:
  HANDLE job_ = nullptr, process_ = nullptr, mutex_ = nullptr;
  static bool Fail(const wchar_t* message) {
    MessageBoxW(nullptr, message, L"Muhammad Zakaria and Sons", MB_OK | MB_ICONINFORMATION);
    return false;
  }
  static bool Healthy() {
    auto session = WinHttpOpen(L"ZakariaERP/2", WINHTTP_ACCESS_TYPE_NO_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) return false;
    WinHttpSetTimeouts(session, 300, 300, 300, 300);
    auto connection = WinHttpConnect(session, L"127.0.0.1", 8765, 0);
    auto request = connection ? WinHttpOpenRequest(connection, L"GET", L"/api/health/", nullptr, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, 0) : nullptr;
    DWORD status = 0, size = sizeof(status);
    if (request && WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0) && WinHttpReceiveResponse(request, nullptr)) {
      WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX);
    }
    if (request) WinHttpCloseHandle(request);
    if (connection) WinHttpCloseHandle(connection);
    WinHttpCloseHandle(session);
    return status == 200;
  }
};
#endif
