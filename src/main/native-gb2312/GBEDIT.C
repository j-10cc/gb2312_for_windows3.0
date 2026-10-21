#include <windows.h>

/* A resident-free probe of the original traditional USER.EXE edit control. */
static char gb[] = {0xBC,0xF2,0xCC,0xE5,0xD6,0xD0,0xCE,0xC4,0};
static HWND edit;
static HFILE log_file;

static void LogBytes(char *label)
{
    static char digits[] = "0123456789ABCDEF";
    char raw[64], line[160];
    int at = 0, i = 0;
    GetWindowText(edit, raw, sizeof(raw));
    while (label[i]) line[at++] = label[i++];
    line[at++] = ':';
    for (i = 0; raw[i] && at < 150; ++i) {
        unsigned char value = (unsigned char)raw[i];
        line[at++] = ' ';
        line[at++] = digits[value >> 4];
        line[at++] = digits[value & 15];
    }
    line[at++] = '\r';
    line[at++] = '\n';
    _lwrite(log_file, line, at);
}

static void LogCursor(char *label)
{
    static char digits[] = "0123456789ABCDEF";
    char line[40];
    LONG selection = SendMessage(edit, EM_GETSEL, 0, 0L);
    unsigned int at = 0, value = LOWORD(selection), i;
    for (i = 0; label[i]; ++i) line[at++] = label[i];
    line[at++] = ':';
    line[at++] = ' ';
    for (i = 0; i < 4; ++i)
        line[at++] = digits[(value >> (12 - 4 * i)) & 15];
    line[at++] = '\r';
    line[at++] = '\n';
    _lwrite(log_file, line, at);
}

long __export FAR PASCAL ProbeProc(HWND hwnd, unsigned message,
                                    WORD wparam, LONG lparam)
{
    switch (message) {
    case WM_CREATE:
        CreateWindow("STATIC", "GB2312 native EDIT probe", WS_CHILD | WS_VISIBLE,
                     8, 8, 330, 16, hwnd, NULL,
                     ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER |
                            ES_AUTOHSCROLL, 8, 30, 500, 24, hwnd,
                            (HMENU)101, ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        if (!edit) return -1L;
        log_file = _lcreat("C:\\GBEDIT.LOG", 0);
        if (log_file == HFILE_ERROR) return -1L;
        SendMessage(edit, EM_REPLACESEL, 0, (LONG)(LPSTR)gb);
        LogBytes("BEFORE");
        SendMessage(edit, EM_SETSEL, 0, MAKELONG(8,8));
        SendMessage(edit, WM_CHAR, 8, 1L);
        LogBytes("BACK");
        SetWindowText(edit, gb);
        SendMessage(edit, EM_SETSEL, 0, MAKELONG(8,8));
        SendMessage(edit, WM_KEYDOWN, VK_LEFT, 1L);
        LogCursor("LEFT");
        SendMessage(edit, EM_SETSEL, 0, MAKELONG(0,0));
        SendMessage(edit, WM_KEYDOWN, VK_RIGHT, 1L);
        LogCursor("RIGHT");
        SetWindowText(edit, gb);
        SendMessage(edit, EM_SETSEL, 0, MAKELONG(0,0));
        SendMessage(edit, WM_KEYDOWN, VK_DELETE, 1L);
        LogBytes("DELETE");
        SetWindowText(edit, gb);
        _lclose(log_file);
        SetFocus(edit);
        return 0L;
    case WM_DESTROY:
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
        wc.lpfnWndProc = (WNDPROC)ProbeProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNativeEditProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBNativeEditProbe", gb, WS_OVERLAPPEDWINDOW,
                        10, 10, 600, 120, NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    ShowWindow(hwnd, show);
    UpdateWindow(hwnd);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
