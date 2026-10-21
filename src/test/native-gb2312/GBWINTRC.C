#include <windows.h>

static HFILE trace_file;
static char class_name[64];
static char title[192];
static char line[256];
static WORD ticks;
static WNDENUMPROC enumeration;

static void Flush(void)
{
    _lclose(trace_file);
    trace_file = _lopen("C:\\GBWIN.LOG", OF_WRITE);
    if (trace_file != HFILE_ERROR)
        _llseek(trace_file, 0L, 2);
}

static void Dump(HWND hwnd, WORD depth)
{
    HWND child;
    WORD i, count;
    if (!IsWindow(hwnd) || depth > 3) return;
    GetClassName(hwnd, class_name, sizeof(class_name));
    count = GetWindowText(hwnd, title, sizeof(title));
    wsprintf(line, "D=%u H=%u C=%s V=%u N=%u ",
             depth, (UINT)hwnd, (LPSTR)class_name,
             (UINT)IsWindowVisible(hwnd), count);
    _lwrite(trace_file, line, lstrlen(line));
    if (count > 80) count = 80;
    for (i = 0; i < count; ++i) {
        wsprintf(line, "%02X", (BYTE)title[i]);
        _lwrite(trace_file, line, 2);
    }
    _lwrite(trace_file, "\r\n", 2);
    Flush();
    child = GetWindow(hwnd, GW_CHILD);
    for (i = 0; child && i < 128; ++i) {
        Dump(child, depth + 1);
        child = GetWindow(child, GW_HWNDNEXT);
    }
}

BOOL __export FAR PASCAL EnumTop(HWND hwnd, LPARAM lparam)
{
    (void)lparam;
    Dump(hwnd, 1);
    return TRUE;
}

LONG __export FAR PASCAL TraceProc(HWND hwnd, UINT message,
                                    WPARAM wparam, LPARAM lparam)
{
    if (message == WM_TIMER && wparam == 1) {
        wsprintf(line, "TICK %u\r\n", ticks++);
        _lwrite(trace_file, line, lstrlen(line));
        Flush();
        EnumWindows(enumeration, 0L);
        Flush();
        if (ticks >= 40) {
            KillTimer(hwnd, 1);
            DestroyWindow(hwnd);
        }
        return 0L;
    }
    if (message == WM_DESTROY) {
        _lclose(trace_file);
        PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    WNDCLASS wc;
    HWND hwnd;
    MSG msg;
    (void)instance; (void)previous; (void)command; (void)show;
    trace_file = _lcreat("C:\\GBWIN.LOG", 0);
    if (trace_file == HFILE_ERROR) return 1;
    _lwrite(trace_file, "START\r\n", 7);
    wc.style = 0;
    wc.lpfnWndProc = (WNDPROC)TraceProc;
    wc.cbClsExtra = wc.cbWndExtra = 0;
    wc.hInstance = instance;
    wc.hIcon = NULL;
    wc.hCursor = NULL;
    wc.hbrBackground = NULL;
    wc.lpszMenuName = NULL;
    wc.lpszClassName = "GBWinTrace";
    if (!RegisterClass(&wc)) {
        _lwrite(trace_file, "NOCLASS\r\n", 9);
        _lclose(trace_file);
        return 2;
    }
    hwnd = CreateWindow("GBWinTrace", "GBWinTrace", WS_POPUP,
                        0, 0, 1, 1, NULL, NULL, instance, NULL);
    if (!hwnd) {
        _lwrite(trace_file, "NOWINDOW\r\n", 10);
        _lclose(trace_file);
        return 3;
    }
    _lwrite(trace_file, "WINDOW\r\n", 8);
    Flush();
    enumeration = (WNDENUMPROC)MakeProcInstance((FARPROC)EnumTop, instance);
    if (!enumeration) {
        _lwrite(trace_file, "NOENUM\r\n", 8);
        DestroyWindow(hwnd);
        return 4;
    }
    if (!SetTimer(hwnd, 1, 500, NULL))
        _lwrite(trace_file, "NOTIMER\r\n", 9);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    FreeProcInstance((FARPROC)enumeration);
    return 0;
}
