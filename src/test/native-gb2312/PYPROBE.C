#include <windows.h>

/* A disposable Win16 PHON.IME slot probe.  It observes the Windows 3.0
 * WINNLS delivery path without installing any application or keyboard hook. */
typedef BOOL (FAR PASCAL *SET_IME_HANDLE)(LPCSTR, HWND);
typedef void (FAR PASCAL *SET_KEYBOARD_HOOK)(BOOL);
typedef void (FAR PASCAL *SET_SYSTEM_IME)(HWND);
typedef HWND (FAR PASCAL *GET_SYSTEM_IME)(void);
typedef LRESULT (FAR PASCAL *KEYBOARD_HOOK)(int, WORD, DWORD);
static HINSTANCE self_instance;
static KEYBOARD_HOOK keyboard_hook;

static void LogMessage(WORD type, HWND hwnd, UINT message,
                       WPARAM wparam, LPARAM lparam)
{
    WORD record[8];
    HFILE file = _lopen("C:\\PYPROBE.BIN", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYPROBE.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    record[0] = type;
    record[1] = hwnd;
    record[2] = message;
    record[3] = wparam;
    record[4] = LOWORD(lparam);
    record[5] = HIWORD(lparam);
    record[6] = GetCurrentTask();
    record[7] = GetFocus();
    _lwrite(file, (LPSTR)record, sizeof(record));
    _lclose(file);
}

BOOL __export FAR PASCAL PinyinDlgProc(HWND hwnd, UINT message,
                                       WPARAM wparam, LPARAM lparam)
{
    LogMessage(2, hwnd, message, wparam, lparam);
    return FALSE;
}

LONG __export FAR PASCAL IMEWNDPROC(HWND hwnd, UINT message,
                                     WPARAM wparam, LPARAM lparam)
{
    if (message == WM_CREATE || message == WM_DESTROY ||
        message == WM_KEYDOWN || message == WM_KEYUP ||
        message == WM_CHAR || message == WM_COMMAND ||
        message == WM_SETFOCUS || message == WM_KILLFOCUS ||
        message >= WM_USER)
        LogMessage(1, hwnd, message, wparam, lparam);
    if (message == WM_TIMER && wparam == 1 && keyboard_hook) {
        KillTimer(hwnd, 1);
        keyboard_hook(0, VK_CONTROL, 0L);
        keyboard_hook(0, VK_SPACE, 0L);
        keyboard_hook(0, VK_CONTROL, 0x80000000L);
        LogMessage(5, hwnd, 0, 0, 0L);
    }
    if (message == WM_DESTROY) PostQuitMessage(0);
    return DefWindowProc(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    HINSTANCE nls;
    SET_IME_HANDLE register_ime;
    SET_KEYBOARD_HOOK set_keyboard_hook;
    SET_SYSTEM_IME set_system_ime;
    GET_SYSTEM_IME get_system_ime;
    HWND system_ime = NULL;
    WNDCLASS wc;
    HWND hwnd;
    MSG msg;
    BOOL registered = FALSE;
    (void)command; (void)show;
    self_instance = instance;
    nls = LoadLibrary("WINNLS.DLL");
    if ((UINT)nls >= 32) {
        register_ime = (SET_IME_HANDLE)GetProcAddress(nls,
                                                      MAKEINTRESOURCE(11));
        set_keyboard_hook = (SET_KEYBOARD_HOOK)GetProcAddress(
            nls, MAKEINTRESOURCE(10));
        set_system_ime = (SET_SYSTEM_IME)GetProcAddress(
            nls, MAKEINTRESOURCE(17));
        get_system_ime = (GET_SYSTEM_IME)GetProcAddress(
            nls, MAKEINTRESOURCE(18));
        keyboard_hook = (KEYBOARD_HOOK)GetProcAddress(nls,
                                                     MAKEINTRESOURCE(2));
    }
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)IMEWNDPROC;
        wc.cbClsExtra = 0;
        wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "PYPROBE";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("PYPROBE", "PYPROBE", WS_POPUP,
                        0, 0, 250, 35, GetDesktopWindow(), NULL,
                        self_instance, NULL);
    LogMessage(4, hwnd, 0, 0, 0L);
    if (!hwnd) return 2;
    if (register_ime) registered = register_ime("phon.ime", hwnd);
    if (set_system_ime) set_system_ime(hwnd);
    if (set_keyboard_hook) set_keyboard_hook(TRUE);
    if (get_system_ime) system_ime = get_system_ime();
    LogMessage(3, hwnd, registered ? 1 : 0, nls, (LPARAM)system_ime);
    ShowWindow(hwnd, SW_HIDE);
    SetTimer(hwnd, 1, 8000, NULL);
    while (GetMessage(&msg, NULL, 0, 0)) {
        if (!msg.hwnd) {
            LogMessage(6, NULL, msg.message, msg.wParam, msg.lParam);
            IMEWNDPROC(hwnd, msg.message, msg.wParam, msg.lParam);
            continue;
        }
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
