#include <windows.h>

/* GB2312: fullwidth @, 驱, 取, 权, followed by known working glyphs. */
static char missing[] = {0xA3,0xC0,0xC7,0xFD,0xC8,0xA1,0xC8,0xA8,
                         0xBC,0xF2,0xCC,0xE5,0};
/* The first donor is a valid Big5 slot outside the GB2312 repertoire. */
static char donor[] = {0xC6,0xA1,0xA3,0xE1,0};

static void DrawRow(HDC dc, int y, int size)
{
    HFONT font, old;
    char label[32];
    font = CreateFont(size, 0, 0, 0, FW_NORMAL, 0, 0, 0,
                      DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                      CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                      DEFAULT_PITCH | FF_DONTCARE, NULL);
    old = SelectObject(dc, font);
    wsprintf(label, "Size %d:", size);
    TextOut(dc, 20, y, label, lstrlen(label));
    TextOut(dc, 190, y, missing, lstrlen(missing));
    SelectObject(dc, old);
    DeleteObject(font);
}

long __export FAR PASCAL ProbeProc(HWND hwnd, unsigned message,
                                    WORD wparam, LONG lparam)
{
    PAINTSTRUCT ps;
    HDC dc;
    if (message == WM_PAINT) {
        dc = BeginPaint(hwnd, &ps);
        DrawRow(dc, 25, 16);
        DrawRow(dc, 85, 20);
        DrawRow(dc, 150, 32);
        TextOut(dc, 20, 230, "C6A1 A3E1:", 11);
        TextOut(dc, 190, 230, donor, 4);
        EndPaint(hwnd, &ps);
        return 0L;
    }
    if (message == WM_DESTROY) {
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
        wc.lpszClassName = "GB2312MissingProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GB2312MissingProbe", "GB2312 VGA glyph coverage",
                        WS_OVERLAPPEDWINDOW, 10, 10, 600, 280,
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
