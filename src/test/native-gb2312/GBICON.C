#include <windows.h>

/* GB2312 titles: short, long, and mixed ASCII/Chinese. */
static char title_short[] = {0xD6,0xD0,0xCE,0xC4,0xCD,0xBC,0xB1,0xEA,0};
static char title_long[] = {0xBC,0xF2,0xCC,0xE5,0xD6,0xD0,0xCE,0xC4,
                            0xD0,0xA1,0xCD,0xBC,0xB1,0xEA,0};
static char title_mixed[] = {0x43,0x47,0x41,0x20,0xD6,0xD0,0xCE,0xC4,
                             0xB2,0xE2,0xCA,0xD4,0};
static int open_windows = 0;

long __export FAR PASCAL IconProc(HWND hwnd, unsigned message, WORD wparam, LONG lparam)
{
    PAINTSTRUCT ps;
    HDC dc;
    switch (message) {
    case WM_PAINT:
        dc = BeginPaint(hwnd, &ps);
        TextOut(dc, 8, 8, "Restore this window to inspect the full title.",
                lstrlen("Restore this window to inspect the full title."));
        EndPaint(hwnd, &ps);
        return 0L;
    case WM_DESTROY:
        if (--open_windows == 0) PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HANDLE instance, HANDLE previous, LPSTR command, int show)
{
    WNDCLASS wc;
    HWND hwnd[3];
    MSG msg;
    char *titles[3];
    int index;
    (void)command;
    (void)show;
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)IconProc;
        wc.cbClsExtra = 0;
        wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNativeIconProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    titles[0] = title_short;
    titles[1] = title_long;
    titles[2] = title_mixed;
    for (index = 0; index < 3; ++index) {
        hwnd[index] = CreateWindow("GBNativeIconProbe", titles[index],
                                   WS_OVERLAPPEDWINDOW,
                                   20 + index * 35, 20 + index * 20,
                                   280, 90, NULL, NULL, instance, NULL);
        if (!hwnd[index]) continue;
        ++open_windows;
        ShowWindow(hwnd[index], SW_SHOWMINIMIZED);
        UpdateWindow(hwnd[index]);
    }
    if (!open_windows) return 2;
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
