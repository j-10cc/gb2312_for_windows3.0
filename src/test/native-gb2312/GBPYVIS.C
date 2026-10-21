#include <windows.h>

static HWND edit;
static unsigned attempts;

static void Mark(char *message)
{
    HFILE file = _lcreat("PYVIS.LOG", 0);
    if (file != HFILE_ERROR) {
        _lwrite(file, message, lstrlen(message));
        _lclose(file);
    }
}

long __export FAR PASCAL VisualProc(HWND hwnd, UINT message,
                                     WPARAM wparam, LPARAM lparam)
{
    HWND ime;
    const char *key = "zhong";
    int i;
    (void)wparam;
    switch (message) {
    case WM_CREATE:
        Mark("CREATE");
        edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER |
                            ES_AUTOHSCROLL, 10, 20, 440, 25, hwnd,
                            (HMENU)101,
                            ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        SetFocus(edit);
        Mark(edit ? "EDIT" : "NOEDIT");
        SetTimer(hwnd, 1, 1000, NULL);
        return 0L;
    case WM_TIMER:
        if (wparam == 2) {
            KillTimer(hwnd, 2);
            Mark("TYPING");
            for (i = 0; key[i]; ++i)
                PostMessage(edit, WM_CHAR, key[i], 1L);
            return 0L;
        }
        ime = FindWindow("phon", "Pinyin GB2312");
        if (!ime && ++attempts < 8) return 0L;
        KillTimer(hwnd, 1);
        if (ime) {
            Mark("IME");
            SetFocus(edit);
            PostMessage(edit, WM_KEYDOWN, VK_CONTROL, 1L);
            PostMessage(edit, WM_KEYDOWN, VK_SPACE, 1L);
            PostMessage(edit, WM_KEYUP, VK_CONTROL, 1L);
            SetTimer(hwnd, 2, 800, NULL);
        } else {
            Mark("NOIME");
        }
        return 0L;
    case WM_DESTROY:
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
    (void)command;
    Mark("MAIN");
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)VisualProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNativePinyinVisual";
        if (!RegisterClass(&wc)) return 1;
    }
    Mark("CLASS");
    hwnd = CreateWindow("GBNativePinyinVisual", "Pinyin candidate display",
                        WS_OVERLAPPEDWINDOW, 10, 10, 500, 110,
                        NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    Mark("WINDOW");
    ShowWindow(hwnd, show);
    UpdateWindow(hwnd);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
