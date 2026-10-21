#include <windows.h>

/* Native GB2312 bytes for "简体中文", without a resident display hook. */
static char text[] = {0xBC,0xF2,0xCC,0xE5,0xD6,0xD0,0xCE,0xC4,0};
static char mixed[] = {0xBC,0xF2,0xCC,0xE5,0xD6,0xD0,0xCE,0xC4,
                       0x20,0x41,0x42,0x43,0x20,0x31,0x32,0x33,0};
static int spaced[] = {10,10,10,10,10,10,10,10,10,10};

static void SaveFile(char *path, char FAR *data, unsigned length)
{
    HFILE f = _lcreat(path, 0);
    if (f != HFILE_ERROR) {
        _lwrite(f, data, length);
        _lclose(f);
    }
}

static void Capture(void)
{
    HDC screen = GetDC(NULL), memory;
    HBITMAP bitmap, old;
    BITMAP b;
    HGLOBAL allocation;
    char FAR *bits;
    LONG length;
    char info[80];
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    memory = CreateCompatibleDC(screen);
    bitmap = CreateBitmap(width, height, 1, 1, NULL);
    if (!screen || !memory || !bitmap) return;
    old = SelectObject(memory, bitmap);
    BitBlt(memory, 0, 0, width, height, screen, 0, 0, SRCCOPY);
    SelectObject(memory, old);
    GetObject(bitmap, sizeof(b), &b);
    length = (LONG)b.bmWidthBytes * b.bmHeight;
    if (length <= 0 || length > 60000L) return;
    allocation = GlobalAlloc(GMEM_MOVEABLE, length);
    if (!allocation) return;
    bits = GlobalLock(allocation);
    if (GetBitmapBits(bitmap, length, bits) == length) {
        SaveFile("C:\\VGA.RAW", bits, (unsigned)length);
        wsprintf(info, "%d %d %d %d %d", width, height,
                 b.bmWidthBytes, b.bmPlanes, b.bmBitsPixel);
        SaveFile("C:\\VGA.INF", info, lstrlen(info));
        SaveFile("C:\\VGA.LOG", "MONO CAPTURED", 13);
    }
    GlobalUnlock(allocation);
    GlobalFree(allocation);
    DeleteObject(bitmap);
    DeleteDC(memory);
    ReleaseDC(NULL, screen);
}

static void DrawLine(HDC dc, int y, int size)
{
    HFONT font, old;
    char line[60];
    DWORD extent;
    font = CreateFont(size, 0, 0, 0, FW_NORMAL, 0, 0, 0,
                      DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                      CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                      DEFAULT_PITCH | FF_DONTCARE, NULL);
    old = SelectObject(dc, font);
    wsprintf(line, "Size %d: ", size);
    TextOut(dc, 10, y, line, lstrlen(line));
    TextOut(dc, 95, y, text, lstrlen(text));
    extent = GetTextExtent(dc, text, lstrlen(text));
    wsprintf(line, "w=%d h=%d", LOWORD(extent), HIWORD(extent));
    TextOut(dc, 340, y, line, lstrlen(line));
    SelectObject(dc, old);
    DeleteObject(font);
}

long __export FAR PASCAL ProbeProc(HWND hwnd, unsigned message,
                                    WORD wparam, LONG lparam)
{
    PAINTSTRUCT ps;
    HDC dc, memory;
    HBITMAP bitmap, old;
    RECT rect;
    int compact;
    if (message == WM_CREATE) {
        SaveFile("C:\\VGA.LOG", "CREATED", 7);
        return 0L;
    }
    if (message == WM_PAINT) {
        SaveFile("C:\\VGA.LOG", "PAINT", 5);
        dc = BeginPaint(hwnd, &ps);
        compact = GetSystemMetrics(SM_CYSCREEN) <= 200;
        if (compact) {
            DrawLine(dc, 5, 8);
            DrawLine(dc, 30, 10);
            TextOut(dc, 95, 50, mixed, lstrlen(mixed));
            ExtTextOut(dc, 430, 30, 0, NULL, text, lstrlen(text), spaced);
        } else {
            DrawLine(dc, 10, 8);
            DrawLine(dc, 45, 12);
            DrawLine(dc, 80, 16);
            DrawLine(dc, 120, 20);
            DrawLine(dc, 165, 24);
            TextOut(dc, 95, 185, mixed, lstrlen(mixed));
            DrawLine(dc, 215, 32);
            ExtTextOut(dc, 430, 80, 0, NULL, text, lstrlen(text), spaced);
        }

        /* Ink should preserve the black stripe under transparent text. */
        rect.left = 0; rect.top = compact ? 65 : 265;
        rect.right = 550; rect.bottom = rect.top + 30;
        FillRect(dc, &rect, GetStockObject(BLACK_BRUSH));
        SetTextColor(dc, RGB(255,255,255));
        SetBkColor(dc, RGB(255,255,255));
        SetBkMode(dc, TRANSPARENT);
        TextOut(dc, 95, rect.top + 2, text, lstrlen(text));
        SetBkMode(dc, OPAQUE);
        SetTextColor(dc, RGB(0,0,0));
        SetBkColor(dc, RGB(255,255,255));

        /* This text is rendered into a memory bitmap, then copied onscreen. */
        memory = CreateCompatibleDC(dc);
        bitmap = CreateCompatibleBitmap(dc, 260, 32);
        if (memory && bitmap) {
            old = SelectObject(memory, bitmap);
            PatBlt(memory, 0, 0, 260, 32, WHITENESS);
            TextOut(memory, 0, 0, text, lstrlen(text));
            BitBlt(dc, 95, compact ? 110 : 315, 260, 32,
                   memory, 0, 0, SRCCOPY);
            SelectObject(memory, old);
            DeleteObject(bitmap);
            DeleteDC(memory);
        }
        rect.left = 95;
        rect.top = compact ? 143 : 350;
        rect.right = 155;
        rect.bottom = rect.top + (compact ? 12 : 20);
        SetTextColor(dc, RGB(255,255,255));
        SetBkColor(dc, RGB(0,0,0));
        ExtTextOut(dc, 95, rect.top, ETO_OPAQUE | ETO_CLIPPED,
                   &rect, text, lstrlen(text), NULL);
        EndPaint(hwnd, &ps);
        SaveFile("C:\\VGA.LOG", "PAINTED", 7);
        return 0L;
    }
    if (message == WM_TIMER) {
        KillTimer(hwnd, 1);
        Capture();
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
    SaveFile("C:\\VGA.LOG", "MAIN", 4);
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)ProbeProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GB2312DrawProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    SaveFile("C:\\VGA.LOG", "CLASS", 5);
    hwnd = CreateWindow("GB2312DrawProbe", text,
                        WS_OVERLAPPEDWINDOW, 10, 10, 600,
                        GetSystemMetrics(SM_CYSCREEN) <= 200 ? 180 : 400,
                        NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    SaveFile("C:\\VGA.LOG", "WINDOW", 6);
    ShowWindow(hwnd, show);
    UpdateWindow(hwnd);
    SetTimer(hwnd, 1, 2500, NULL);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
