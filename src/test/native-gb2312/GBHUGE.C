#include <windows.h>

/* 1024 * 528 / 8 = 67584 bytes: the two strings straddle 64 KiB. */
static char chinese[] = {0xD6, 0xD0, 0};

static void Log(char *status, int first, int second, int reference)
{
    char line[80];
    HFILE file = _lcreat("C:\\HUGE.LOG", 0);
    if (file == HFILE_ERROR) return;
    _lwrite(file, status, lstrlen(status));
    wsprintf(line, " %d %d %d", first, second, reference);
    _lwrite(file, line, lstrlen(line));
    _lclose(file);
}

static int Ink(HDC dc, int left, int top)
{
    int x, y, count = 0;
    for (y = 0; y < 10; ++y)
        for (x = 0; x < 16; ++x)
            if (GetPixel(dc, left + x, top + y) == RGB(0, 0, 0))
                ++count;
    return count;
}

static void Pattern(char *path, HDC dc, int left, int top)
{
    static char line[18];
    HFILE file = _lcreat(path, 0);
    int x, y;
    if (file == HFILE_ERROR) return;
    for (y = 0; y < 10; ++y) {
        for (x = 0; x < 16; ++x)
            line[x] = GetPixel(dc, left + x, top + y) == RGB(0, 0, 0)
                        ? '#' : '.';
        line[16] = '\r'; line[17] = '\n';
        _lwrite(file, line, 18);
    }
    _lclose(file);
}

long __export FAR PASCAL ProbeProc(HWND hwnd, UINT message,
                                    WPARAM wparam, LPARAM lparam)
{
    PAINTSTRUCT ps;
    HDC dc, memory, small;
    HBITMAP bitmap, old, small_bitmap, small_old;
    BITMAP info;
    int first, second, reference = -1;
    (void)wparam; (void)lparam;
    if (message == WM_PAINT) {
        dc = BeginPaint(hwnd, &ps);
        memory = CreateCompatibleDC(dc);
        bitmap = CreateBitmap(1024, 528, 1, 1, NULL);
        if (!memory || !bitmap) {
            Log("ALLOCFAIL", memory != 0, bitmap != 0, 0);
        } else {
            GetObject(bitmap, sizeof(info), &info);
            old = SelectObject(memory, bitmap);
            if (!old) Log("SELECTFAIL", info.bmWidthBytes, info.bmHeight, 0);
            else {
                SetTextColor(memory, RGB(0, 0, 0));
                SetBkColor(memory, RGB(255, 255, 255));
                PatBlt(memory, 0, 486, 80, 42, WHITENESS);
                TextOut(memory, 8, 490, chinese, 2);
                TextOut(memory, 8, 514, chinese, 2);
                first = Ink(memory, 8, 490);
                second = Ink(memory, 8, 514);
                Pattern("C:\\HUGE0.TXT", memory, 8, 490);
                Pattern("C:\\HUGE1.TXT", memory, 8, 514);
                BitBlt(dc, 30, 30, 80, 42, memory, 0, 486, SRCCOPY);
                small = CreateCompatibleDC(dc);
                small_bitmap = CreateBitmap(80, 20, 1, 1, NULL);
                if (small && small_bitmap) {
                    small_old = SelectObject(small, small_bitmap);
                    if (small_old) {
                        SetTextColor(small, RGB(0, 0, 0));
                        SetBkColor(small, RGB(255, 255, 255));
                        PatBlt(small, 0, 0, 80, 20, WHITENESS);
                        TextOut(small, 8, 4, chinese, 2);
                        reference = Ink(small, 8, 4);
                        Pattern("C:\\SMALL.TXT", small, 8, 4);
                        BitBlt(dc, 120, 30, 50, 20, small, 0, 0, SRCCOPY);
                        SelectObject(small, small_old);
                    }
                    DeleteObject(small_bitmap);
                }
                if (small) DeleteDC(small);
                Log("HUGE", first, second, reference);
                SelectObject(memory, old);
            }
            DeleteObject(bitmap);
        }
        if (memory) DeleteDC(memory);
        EndPaint(hwnd, &ps);
        return 0L;
    }
    if (message == WM_DESTROY) { PostQuitMessage(0); return 0L; }
    return DefWindowProc(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
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
        wc.lpszClassName = "GBHugeProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBHugeProbe", "GB2312 Huge Bitmap",
                        WS_OVERLAPPEDWINDOW, 10, 10, 180, 110,
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
