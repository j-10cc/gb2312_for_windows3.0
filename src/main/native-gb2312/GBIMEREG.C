#include <windows.h>

/* Test-only Win16 client.  It exercises the real PHON.IME window and logs
 * the bytes accepted by two ordinary Windows EDIT controls. */
static HWND first_edit, second_edit;
static WORD stage = 0xffff;

static void Save(const char *name, const char FAR *data, WORD size)
{
    HFILE file = _lcreat(name, 0);
    if (file == HFILE_ERROR) return;
    _lwrite(file, data, size);
    _lclose(file);
}

static void Capture(void)
{
    HDC screen = GetDC(NULL), memory = NULL;
    HBITMAP bitmap = NULL, old_bitmap;
    HGLOBAL allocation = NULL;
    char FAR *bits;
    BITMAP info;
    LONG size;
    char dimensions[80];
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    if (!screen) return;
    memory = CreateCompatibleDC(screen);
    bitmap = CreateBitmap(width, height, 1, 1, NULL);
    if (!memory || !bitmap) goto done;
    old_bitmap = SelectObject(memory, bitmap);
    if (!old_bitmap) goto done;
    BitBlt(memory, 0, 0, width, height, screen, 0, 0, SRCCOPY);
    SelectObject(memory, old_bitmap);
    GetObject(bitmap, sizeof(info), &info);
    size = (LONG)info.bmWidthBytes * info.bmHeight;
    if (size <= 0 || size > 60000L) goto done;
    allocation = GlobalAlloc(GMEM_MOVEABLE, size);
    if (!allocation) goto done;
    bits = GlobalLock(allocation);
    if (!bits) goto done;
    if (GetBitmapBits(bitmap, size, bits) == size) {
        Save("IMEREG.RAW", bits, (WORD)size);
        wsprintf(dimensions, "%d %d %d %d %d", width, height,
                 info.bmWidthBytes, info.bmPlanes, info.bmBitsPixel);
        Save("IMEREG.INF", dimensions, lstrlen(dimensions));
    }
    GlobalUnlock(allocation);
done:
    if (allocation) GlobalFree(allocation);
    if (bitmap) DeleteObject(bitmap);
    if (memory) DeleteDC(memory);
    ReleaseDC(NULL, screen);
}

static void LogEdit(WORD number, HWND edit)
{
    static const char digits[] = "0123456789ABCDEF";
    char raw[32], line[112];
    WORD i, at = 0;
    HFILE file;
    GetWindowText(edit, raw, sizeof(raw));
    line[at++] = 'C'; line[at++] = 'A'; line[at++] = 'S';
    line[at++] = 'E'; line[at++] = '0' + number;
    line[at++] = ':';
    for (i = 0; raw[i]; ++i) {
        BYTE value = (BYTE)raw[i];
        line[at++] = ' ';
        line[at++] = digits[value >> 4];
        line[at++] = digits[value & 15];
    }
    line[at++] = '\r'; line[at++] = '\n';
    file = _lopen("IMEREG.LOG", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("IMEREG.LOG", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    _lwrite(file, line, at);
    _lclose(file);
}

static void Type(HWND ime, const char *text)
{
    while (*text) SendMessage(ime, WM_CHAR, (BYTE)*text++, 1L);
}

LONG __export FAR PASCAL ReviewProc(HWND hwnd, UINT message,
                                     WPARAM wparam, LPARAM lparam)
{
    HWND ime;
    switch (message) {
    case WM_CREATE:
        first_edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE |
                                  WS_BORDER | ES_AUTOHSCROLL,
                                  8, 8, 260, 25, hwnd, (HMENU)101,
                                  ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        second_edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE |
                                   WS_BORDER | ES_AUTOHSCROLL,
                                   8, 40, 260, 25, hwnd, (HMENU)102,
                                   ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        if (!first_edit || !second_edit) return -1L;
        SetFocus(first_edit);
        SetTimer(hwnd, 1, 900, NULL);
        return 0L;
    case WM_TIMER:
        if (wparam != 1) return 0L;
        ime = FindWindow("GBPY_NATIVE", "Pinyin");
        if (!ime) return 0L;
        if (stage != 0xffff) {
            LogEdit(stage, stage == 8 ? second_edit : first_edit);
            if (stage == 9) {
                SetWindowText(first_edit, "");
                SetFocus(first_edit);
                Type(ime, "zhong");
                UpdateWindow(ime);
                Capture();
                KillTimer(hwnd, 1);
                return 0L;
            }
            SetWindowText(first_edit, "");
            SetWindowText(second_edit, "");
            SetFocus(first_edit);
            ++stage;
        } else stage = 0;
        switch (stage) {
        case 0: Type(ime, "zhong "); break;
        case 1: Type(ime, "zhong2"); break;
        case 2: Type(ime, "xyz "); break;
        case 3: Type(ime, "Zyx "); break;
        case 4: Type(ime, "zhong=1"); break;
        case 5: Type(ime, "zhong-1"); break;
        case 6:
            Type(ime, "zhong");
            SendMessage(ime, WM_CHAR, 8, 1L);
            Type(ime, "g ");
            break;
        case 7:
            Type(ime, "zhong");
            SendMessage(ime, WM_CHAR, 27, 1L);
            Type(ime, "xyz ");
            break;
        case 8:
            Type(ime, "zhong");
            SetFocus(second_edit);
            Type(ime, "xyz ");
            break;
        case 9: Type(ime, ".1.2"); break;
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
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)ReviewProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBIMEREG";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBIMEREG", "IME review", WS_OVERLAPPEDWINDOW |
                        WS_VISIBLE, 10, 10, 300, 110, NULL, NULL, instance,
                        NULL);
    if (!hwnd) return 2;
    ShowWindow(hwnd, show);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
