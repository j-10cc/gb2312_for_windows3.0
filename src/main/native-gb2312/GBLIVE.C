#include <windows.h>

/* A normal EDIT box for testing the original PHON.IME keyboard path. */
static HWND edit;
static HFILE log_file;

static void LogText(void)
{
    static char digits[] = "0123456789ABCDEF";
    char raw[80], line[240];
    int i, at = 0;
    GetWindowText(edit, raw, sizeof(raw));
    for (i = 0; raw[i] && at < 230; ++i) {
        unsigned char b = (unsigned char)raw[i];
        line[at++] = digits[b >> 4];
        line[at++] = digits[b & 15];
        line[at++] = ' ';
    }
    line[at++] = '\r';
    line[at++] = '\n';
    _lwrite(log_file, line, at);
}

long __export FAR PASCAL LiveProc(HWND hwnd, unsigned message,
                                   WORD wparam, LONG lparam)
{
    switch (message) {
    case WM_CREATE:
        CreateWindow("STATIC", "Type with the system IME below:",
                     WS_CHILD | WS_VISIBLE, 8, 8, 420, 16, hwnd, NULL,
                     ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER |
                            ES_AUTOHSCROLL, 8, 28, 500, 24, hwnd,
                            (HMENU)101, ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        if (!edit) return -1L;
        log_file = _lcreat("C:\\GBLIVE.LOG", 0);
        if (log_file == HFILE_ERROR) return -1L;
        SetFocus(edit);
        return 0L;
    case WM_COMMAND:
        if (wparam == 101 && HIWORD(lparam) == EN_CHANGE)
            LogText();
        return 0L;
    case WM_DESTROY:
        _lclose(log_file);
        PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HANDLE instance, HANDLE previous, LPSTR command, int show)
{
    WNDCLASS wc;
    HWND hwnd;
    MSG msg;
    (void)command;
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)LiveProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNativeLiveProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBNativeLiveProbe", "GB2312 PHON IME input test",
                        WS_OVERLAPPEDWINDOW, 10, 10, 600, 120,
                        NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    ShowWindow(hwnd, show);
    UpdateWindow(hwnd);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
