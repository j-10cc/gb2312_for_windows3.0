#include <windows.h>

/* Test-only Win16 client for the native WINNLS -> PHON.IME -> EDIT path. */
static HWND editor;
static WORD attempts;

static void WriteStage(WORD stage, WORD value)
{
    HFILE file = _lopen("NATSTAGE.BIN", OF_WRITE);
    WORD record[2];
    if (file == HFILE_ERROR) file = _lcreat("NATSTAGE.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    record[0] = stage;
    record[1] = value;
    _lwrite(file, (LPSTR)record, 4);
    _lclose(file);
}

static void WriteResult(void)
{
    static char hex[] = "0123456789ABCDEF";
    char raw[16], line[80];
    HFILE file;
    WORD i, at = 0;
    GetWindowText(editor, raw, sizeof(raw));
    line[at++] = 'C'; line[at++] = 'O'; line[at++] = 'M';
    line[at++] = 'M'; line[at++] = 'I'; line[at++] = 'T';
    line[at++] = ':';
    for (i = 0; raw[i]; ++i) {
        BYTE c = (BYTE)raw[i];
        line[at++] = ' ';
        line[at++] = hex[c >> 4];
        line[at++] = hex[c & 15];
    }
    line[at++] = '\r'; line[at++] = '\n';
    file = _lcreat("PINTEST.LOG", 0);
    if (file != HFILE_ERROR) {
        _lwrite(file, line, at);
        _lclose(file);
    }
    WriteStage(10, raw[0] ? (BYTE)raw[0] : 0);
}

LONG __export FAR PASCAL NativeTestProc(HWND hwnd, UINT message,
                                         WPARAM wparam, LPARAM lparam)
{
    HWND ime;
    WORD i;
    static char pinyin[] = "zhong";
    switch (message) {
    case WM_CREATE:
        WriteStage(4, hwnd);
        editor = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE |
                              WS_BORDER | ES_AUTOHSCROLL,
                              8, 12, 260, 24, hwnd, (HMENU)101,
                              ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        if (!editor) return -1L;
        WriteStage(5, editor);
        SetFocus(editor);
        WriteStage(6, SetTimer(hwnd, 1, 1000, NULL));
        return 0L;
    case WM_TIMER:
        WriteStage(7, wparam);
        if (wparam == 1) {
            ime = FindWindow("GBPY_NATIVE", "Pinyin");
            WriteStage(8, ime);
            if (!ime && ++attempts < 15) return 0L;
            KillTimer(hwnd, 1);
            if (ime) {
                SetFocus(editor);
                for (i = 0; pinyin[i]; ++i)
                    SendMessage(ime, WM_CHAR, pinyin[i], 1L);
                SendMessage(ime, WM_CHAR, ' ', 1L);
                WriteStage(9, ime);
                SetTimer(hwnd, 2, 1000, NULL);
            } else WriteResult();
        } else if (wparam == 2) {
            KillTimer(hwnd, 2);
            WriteResult();
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
    WriteStage(1, instance);
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)NativeTestProc;
        wc.cbClsExtra = 0;
        wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNATST";
        if (!RegisterClass(&wc)) return 1;
        WriteStage(2, instance);
    }
    hwnd = CreateWindow("GBNATST", "Native Pinyin Test",
                        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                        10, 10, 300, 85, NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    WriteStage(3, hwnd);
    ShowWindow(hwnd, show);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
