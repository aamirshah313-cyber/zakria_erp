#ifndef ZAKARIA_STARTUP_SPLASH_H_
#define ZAKARIA_STARTUP_SPLASH_H_
#include <windows.h>
#include <string>

#include "resource.h"

// Small "Starting…" window shown while the bundled service prepares or
// upgrades the database, so a slow first run does not look like a failed open.
class StartupSplash {
 public:
  ~StartupSplash() { Close(); }

  void Show() {
    if (window_) return;
    const HINSTANCE instance = GetModuleHandleW(nullptr);
    WNDCLASSW window_class{};
    window_class.lpfnWndProc = Procedure;
    window_class.hInstance = instance;
    window_class.hCursor = LoadCursorW(nullptr, IDC_WAIT);
    window_class.hbrBackground = static_cast<HBRUSH>(GetStockObject(WHITE_BRUSH));
    window_class.lpszClassName = kClassName;
    RegisterClassW(&window_class);
    const int width = 460, height = 170;
    RECT work{};
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &work, 0);
    window_ = CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW, kClassName, L"Zakaria ERP",
                              WS_POPUP | WS_BORDER,
                              work.left + (work.right - work.left - width) / 2,
                              work.top + (work.bottom - work.top - height) / 2,
                              width, height, nullptr, nullptr, instance, this);
    if (!window_) return;
    started_ = GetTickCount64();
    ShowWindow(window_, SW_SHOWNORMAL);
    UpdateWindow(window_);
  }

  // Keeps the window painted and responsive while the caller waits.
  void Pump() {
    MSG message;
    while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
      TranslateMessage(&message);
      DispatchMessageW(&message);
    }
    if (!window_) return;
    const ULONGLONG seconds = (GetTickCount64() - started_) / 1000;
    if (seconds != shown_seconds_) {
      shown_seconds_ = seconds;
      InvalidateRect(window_, nullptr, TRUE);
    }
  }

  void Close() {
    if (window_) DestroyWindow(window_);
    window_ = nullptr;
  }

 private:
  static constexpr const wchar_t* kClassName = L"ZakariaERPStartupSplash";
  HWND window_ = nullptr;
  ULONGLONG started_ = 0, shown_seconds_ = 0;

  void Paint(HWND window) {
    PAINTSTRUCT paint;
    const HDC dc = BeginPaint(window, &paint);
    SetBkMode(dc, TRANSPARENT);
    const HICON icon = static_cast<HICON>(LoadImageW(GetModuleHandleW(nullptr), MAKEINTRESOURCEW(IDI_APP_ICON), IMAGE_ICON, 64, 64, 0));
    if (icon) {
      DrawIconEx(dc, 28, 36, icon, 64, 64, 0, nullptr, DI_NORMAL);
      DestroyIcon(icon);
    }
    const HFONT title = CreateFontW(-22, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
    const HFONT body = CreateFontW(-15, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
    const HGDIOBJ previous = SelectObject(dc, title);
    SetTextColor(dc, RGB(0x19, 0x22, 0x30));
    RECT line{116, 34, 440, 64};
    DrawTextW(dc, L"Starting Zakaria ERP…", -1, &line, DT_SINGLELINE | DT_LEFT | DT_VCENTER);
    SelectObject(dc, body);
    SetTextColor(dc, RGB(0x69, 0x75, 0x86));
    RECT detail{116, 68, 440, 112};
    DrawTextW(dc, L"Preparing the database. After installing or upgrading this can take a minute.", -1, &detail, DT_LEFT | DT_WORDBREAK);
    const std::wstring elapsed = L"Please wait · " + std::to_wstring(shown_seconds_) + L" s";
    RECT timer{116, 118, 440, 140};
    DrawTextW(dc, elapsed.c_str(), -1, &timer, DT_SINGLELINE | DT_LEFT | DT_VCENTER);
    // Brand accent bar along the top edge.
    RECT bar{0, 0, 460, 4};
    const HBRUSH accent = CreateSolidBrush(RGB(0xED, 0x7B, 0x25));
    FillRect(dc, &bar, accent);
    DeleteObject(accent);
    SelectObject(dc, previous);
    DeleteObject(title);
    DeleteObject(body);
    EndPaint(window, &paint);
  }

  static LRESULT CALLBACK Procedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_NCCREATE) {
      const auto create = reinterpret_cast<CREATESTRUCTW*>(lparam);
      SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(create->lpCreateParams));
    }
    const auto self = reinterpret_cast<StartupSplash*>(GetWindowLongPtrW(window, GWLP_USERDATA));
    if (message == WM_PAINT && self) {
      self->Paint(window);
      return 0;
    }
    if (message == WM_CLOSE) return 0;  // Closes itself once the service is ready.
    return DefWindowProcW(window, message, wparam, lparam);
  }
};
#endif
