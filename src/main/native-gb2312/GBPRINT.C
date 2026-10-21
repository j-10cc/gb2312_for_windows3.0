#include <windows.h>
#include <string.h>

/* Exercise the installed Windows 3.0 printer driver without a physical port.
   The disposable test image selects a real driver and a file port in WIN.INI. */

static void Record(char *stage, int value)
{
    HFILE file = _lopen("C:\\GBPRINT.LOG", OF_WRITE);
    char line[80], number[16];
    if (file == HFILE_ERROR) file = _lcreat("C:\\GBPRINT.LOG", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    lstrcpy(line, stage);
    lstrcat(line, "=");
    wsprintf(number, "%d", value);
    lstrcat(line, number);
    lstrcat(line, "\r\n");
    _lwrite(file, line, lstrlen(line));
    _lclose(file);
}

static void PrintDocument(void)
{
    char setting[128], *driver, *port, *comma;
    HDC dc;
    HFONT font, old_font;
    int result, width, height;
    static char title[] = "GB2312 print probe";
    static char chinese[] = "\xD6\xD0\xCE\xC4 \xBC\xF2\xCC\xE5 ABC 123";

    GetProfileString("windows", "device", "", setting, sizeof(setting));
    Record("PROFILE", lstrlen(setting));
    comma = strchr(setting, ',');
    if (!comma) return;
    *comma++ = '\0';
    driver = comma;
    comma = strchr(driver, ',');
    if (!comma) return;
    *comma++ = '\0';
    port = comma;
    dc = CreateDC(driver, setting, port, NULL);
    Record("DC", dc ? 1 : 0);
    if (!dc) return;
    width = GetDeviceCaps(dc, HORZRES);
    height = GetDeviceCaps(dc, VERTRES);
    Record("WIDTH", width);
    Record("HEIGHT", height);
    font = CreateFont(50, 0, 0, 0, FW_NORMAL, 0, 0, 0,
                      DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                      DEFAULT_QUALITY, FF_DONTCARE, "MingLiU");
    old_font = font ? SelectObject(dc, font) : NULL;
    result = Escape(dc, STARTDOC, sizeof(title), title, NULL);
    Record("START", result);
    if (result > 0) {
        TextOut(dc, 80, 80, "GB2312 page 1", 13);
        TextOut(dc, 80, 170, chinese, lstrlen(chinese));
        Rectangle(dc, 60, 140, width - 60, 250);
        result = Escape(dc, NEWFRAME, 0, NULL, NULL);
        Record("PAGE1", result);
        if (result > 0) {
            TextOut(dc, 80, 80, "GB2312 page 2", 13);
            TextOut(dc, 80, 170, chinese, lstrlen(chinese));
            Rectangle(dc, 60, 140, width - 60, 250);
            result = Escape(dc, NEWFRAME, 0, NULL, NULL);
            Record("PAGE2", result);
        }
        if (result > 0) {
            result = Escape(dc, ENDDOC, 0, NULL, NULL);
            Record("END", result);
        } else Escape(dc, ABORTDOC, 0, NULL, NULL);
    }
    if (old_font) SelectObject(dc, old_font);
    if (font) DeleteObject(font);
    DeleteDC(dc);
    Record("DONE", 1);
}

LONG __export FAR PASCAL PrintProc(HWND hwnd, UINT message,
                                   WPARAM wparam, LPARAM lparam)
{
    if (message == WM_CREATE) {
        SetTimer(hwnd, 1, 600, NULL);
        return 0L;
    }
    if (message == WM_TIMER) {
        KillTimer(hwnd, 1);
        PrintDocument();
        return 0L;
    }
    if (message == WM_DESTROY) {
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
        wc.lpfnWndProc = (WNDPROC)PrintProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBPrintProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBPrintProbe", "GB2312 print probe",
                        WS_OVERLAPPEDWINDOW, 10, 10, 350, 140,
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
