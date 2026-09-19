#ifndef ZAKARIA_DESKTOP_SERVICE_H_
#define ZAKARIA_DESKTOP_SERVICE_H_
#include <windows.h>
#include <iphlpapi.h>
#include <shlobj.h>
#include <winhttp.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include "startup_splash.h"

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
    StartupSplash::Instance();  // Starts the one-second "slow launch" clock.
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
    // Global: one shared database per computer, so a second Windows account
    // must not start its own service against the same data.
    mutex_ = CreateMutexW(nullptr, TRUE, L"Global\\ZakariaERP-V2-Native");
    if (!mutex_ || GetLastError() == ERROR_ALREADY_EXISTS || GetLastError() == ERROR_ACCESS_DENIED) {
      return Fail(L"Zakaria ERP is already open on this computer, possibly in another Windows account. Close it there before opening it here.");
    }
    if (!std::filesystem::exists(backend)) return Fail(L"The desktop package is incomplete. Reinstall Zakaria ERP or keep its backend, data and DLL folders together.");
    std::wstring data;
    if (std::filesystem::exists(config)) {
      // Acceptance packages name an explicit data folder.
      std::ifstream input(config, std::ios::binary);
      std::string encoded;
      std::getline(input, encoded);
      if (!encoded.empty() && encoded.back() == '\r') encoded.pop_back();
      const int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, encoded.data(), static_cast<int>(encoded.size()), nullptr, 0);
      if (!count) return Fail(L"The V2 data-folder configuration is invalid.");
      data.assign(count, L'\0');
      MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, encoded.data(), static_cast<int>(encoded.size()), data.data(), count);
    } else {
      // Installed application: shared data prepared by the installer.
      PWSTR common = nullptr;
      if (FAILED(SHGetKnownFolderPath(FOLDERID_ProgramData, 0, nullptr, &common))) {
        if (common) CoTaskMemFree(common);
        return Fail(L"Cannot locate the shared ProgramData folder.");
      }
      data = (std::filesystem::path(common) / L"ZakariaERP").wstring();
      CoTaskMemFree(common);
    }
    if (data.find(L'"') != std::wstring::npos || !std::filesystem::path(data).is_absolute()) return Fail(L"The V2 data-folder configuration is invalid.");
    log_ = (std::filesystem::path(data) / L"logs" / L"service.log").wstring();
    // Refuse a occupied port rather than attaching to an unrelated local server.
    if (Listening(0) && Healthy()) return Fail(L"A desktop service is already using port 8765. Close the earlier desktop service before opening this package.");
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
    // First run and upgrades create or back up the database before listening.
    // Quick starts finish before the splash appears; slower ones show progress.
    // Timing uses the clock: a refused loopback connection can block ~2 s, so
    // the HTTP check runs only once our own process listens on the port.
    auto& splash = StartupSplash::Instance();
    const DWORD service_pid = GetProcessId(process_);
    const ULONGLONG begun = GetTickCount64();
    while (GetTickCount64() - begun < 180000) {
      splash.ShowIfSlow();
      splash.Pump();
      if (Listening(service_pid) && Healthy()) return true;
      if (MsgWaitForMultipleObjects(1, &process_, FALSE, 200, QS_ALLINPUT) == WAIT_OBJECT_0) break;
    }
    splash.Close();
    const std::wstring message = L"The desktop service could not start. Details are in:\n" + log_;
    return Fail(message.c_str());
  }

 private:
  HANDLE job_ = nullptr, process_ = nullptr, mutex_ = nullptr;
  std::wstring log_;
  static bool Fail(const wchar_t* message) {
    MessageBoxW(nullptr, message, L"Muhammad Zakaria and Sons", MB_OK | MB_ICONINFORMATION);
    return false;
  }
  // True when process `pid` (any process if 0) has a TCP listener on port 8765 (IPv4).
  static bool Listening(DWORD pid) {
    const ULONG kIpv4 = 2;  // AF_INET
    DWORD size = 0;
    GetExtendedTcpTable(nullptr, &size, FALSE, kIpv4, TCP_TABLE_OWNER_PID_LISTENER, 0);
    std::vector<BYTE> buffer(size);
    if (size == 0 || GetExtendedTcpTable(buffer.data(), &size, FALSE, kIpv4, TCP_TABLE_OWNER_PID_LISTENER, 0) != NO_ERROR) {
      return true;  // Table unavailable: fall back to the HTTP check.
    }
    const auto table = reinterpret_cast<PMIB_TCPTABLE_OWNER_PID>(buffer.data());
    for (DWORD i = 0; i < table->dwNumEntries; ++i) {
      const DWORD network = table->table[i].dwLocalPort;
      const DWORD port = ((network & 0xFF) << 8) | ((network >> 8) & 0xFF);
      if (port == 8765 && (pid == 0 || table->table[i].dwOwningPid == pid)) return true;
    }
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
