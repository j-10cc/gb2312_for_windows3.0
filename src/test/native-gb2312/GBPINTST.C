#include <windows.h>

static HWND edit;
static unsigned attempts;
static UINT launch_result;
static HFILE optional_ime;
static unsigned phase;

static void Mark(char *message)
{
    HFILE file = _lcreat("PSTART.LOG", 0);
    if (file != HFILE_ERROR) {
        _lwrite(file, message, lstrlen(message));
        _lclose(file);
    }
}

static void LogResult(char *status)
{
    HFILE file = phase ? _lopen("PINTEST.LOG", OF_WRITE)
                       : _lcreat("PINTEST.LOG", 0);
    char raw[48], line[160];
    static char hex[] = "0123456789ABCDEF";
    int i, at = 0;
    if (file == HFILE_ERROR) return;
    if (phase) _llseek(file, 0L, 2);
    for (i = 0; status[i]; ++i) line[at++] = status[i];
    line[at++] = ':';
    GetWindowText(edit, raw, sizeof(raw));
    for (i = 0; raw[i] && at < 140; ++i) {
        unsigned char c = (unsigned char)raw[i];
        line[at++] = ' ';
        line[at++] = hex[c >> 4];
        line[at++] = hex[c & 15];
    }
    line[at++] = '\r';
    line[at++] = '\n';
    _lwrite(file, line, at);
    _lclose(file);
}

long __export FAR PASCAL ProbeProc(HWND hwnd, UINT message,
                                    WPARAM wparam, LPARAM lparam)
{
    HWND ime;
#ifdef IME_PEEK_TEST
    MSG peek;
#endif
    char *key = "zhong";
    int i;
    switch (message) {
    case WM_CREATE:
        Mark("CREATE");
        edit = CreateWindow("EDIT", "", WS_CHILD | WS_VISIBLE | WS_BORDER |
                            ES_AUTOHSCROLL, 10, 20, 440, 25,
                            hwnd, (HMENU)101,
                            ((LPCREATESTRUCT)lparam)->hInstance, NULL);
        Mark(edit ? "EDIT" : "NOEDIT");
        SetFocus(edit);
        optional_ime = _lopen("C:\\WINDOWS\\PINYIN.EXE", OF_READ);
        if (optional_ime != HFILE_ERROR) {
            _lclose(optional_ime);
            launch_result = WinExec("C:\\WINDOWS\\PINYIN.EXE", SW_SHOWNOACTIVATE);
            Mark(launch_result > 31 ? "LAUNCHED" : "NOLOAD");
        } else {
            Mark("SYSTEM");
        }
        SetTimer(hwnd, 1, 1000, NULL);
        Mark("TIMER");
        return 0L;
    case WM_TIMER:
        if (phase == 6) {
            KillTimer(hwnd, 1);
            LogResult("REPEAT");
            return 0L;
        }
        if (phase == 5) {
            LogResult("LONG");
            SetWindowText(edit, "");
            PostMessage(edit, WM_CHAR, 'z', 1L);
#ifdef IME_PEEK_TEST
            PeekMessage(&peek, edit, WM_CHAR, WM_CHAR, PM_NOREMOVE);
            PeekMessage(&peek, edit, WM_CHAR, WM_CHAR, PM_NOREMOVE);
#endif
            PostMessage(edit, WM_CHAR, 'z', 1L);
            PostMessage(edit, WM_CHAR, ' ', 1L);
            phase = 6;
            return 0L;
        }
        if (phase == 4) {
            LogResult("PUNCT");
            SetWindowText(edit, "");
            for (i = 0; i < 8; ++i)
                PostMessage(edit, WM_CHAR, "abcdefgh"[i], 1L);
            phase = 5;
            return 0L;
        }
        if (phase == 3) {
            LogResult("RAW_DIGIT");
            SetWindowText(edit, "");
            for (i = 0; key[i]; ++i)
                PostMessage(edit, WM_CHAR, key[i], 1L);
            PostMessage(edit, WM_CHAR, ',', 1L);
            phase = 4;
            return 0L;
        }
        if (phase == 1) {
#ifdef IME_PEEK_TEST
            PostMessage(edit, WM_CHAR, key[0], 1L);
            PeekMessage(&peek, edit, WM_CHAR, WM_CHAR, PM_NOREMOVE);
            PeekMessage(&peek, edit, WM_CHAR, WM_CHAR, PM_NOREMOVE);
            LogResult("PEEK");
            for (i = 1; key[i]; ++i) PostMessage(edit, WM_CHAR, key[i], 1L);
#else
            for (i = 0; key[i]; ++i) PostMessage(edit, WM_CHAR, key[i], 1L);
#endif
            PostMessage(edit, WM_CHAR, ' ', 1L);
            phase = 2;
            SetTimer(hwnd, 1, 1000, NULL);
            return 0L;
        }
        if (phase == 2) {
            LogResult("KEYBOARD");
            ime = FindWindow("phon", "Pinyin GB2312");
            if (ime) {
                SetWindowText(edit, "");
                for (i = 0; key[i]; ++i) SendMessage(ime, WM_CHAR, key[i], 1L);
                SendMessage(ime, WM_CHAR, '2', 1L);
                LogResult("SECOND");
                SetWindowText(edit, "");
                SendMessage(ime, WM_CHAR, 'x', 1L);
                SendMessage(ime, WM_CHAR, 'y', 1L);
                SendMessage(ime, WM_CHAR, 'z', 1L);
                SendMessage(ime, WM_CHAR, ' ', 1L);
                LogResult("RAW");
                SetWindowText(edit, "");
                PostMessage(edit, WM_CHAR, 'x', 1L);
                PostMessage(edit, WM_CHAR, 'y', 1L);
                PostMessage(edit, WM_CHAR, 'z', 1L);
                PostMessage(edit, WM_CHAR, '1', 1L);
                phase = 3;
            }
            return 0L;
        }
        ime = FindWindow("phon", "Pinyin GB2312");
        if (!ime && ++attempts < 8) return 0L;
        KillTimer(hwnd, 1);
        if (!ime) {
            LogResult("NOIME");
            return 0L;
        }
        SetFocus(edit);
        for (i = 0; key[i]; ++i) SendMessage(ime, WM_CHAR, key[i], 1L);
        SendMessage(ime, WM_CHAR, ' ', 1L);
        LogResult("COMMIT");
        SetWindowText(edit, "");
        PostMessage(edit, WM_KEYDOWN, VK_CONTROL, 1L);
        PostMessage(edit, WM_KEYDOWN, VK_SPACE, 1L);
        PostMessage(edit, WM_KEYUP, VK_CONTROL, 1L);
        phase = 1;
        SetTimer(hwnd, 1, 500, NULL);
        InvalidateRect(hwnd, NULL, TRUE);
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
        wc.lpfnWndProc = (WNDPROC)ProbeProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNativePinyinProbe";
        if (!RegisterClass(&wc)) return 1;
    }
    Mark("CLASS");
    hwnd = CreateWindow("GBNativePinyinProbe", "Pinyin system IME test",
                        WS_OVERLAPPEDWINDOW, 10, 10, 500, 110,
                        NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    Mark("WINDOW");
    ShowWindow(hwnd, show);
    Mark("SHOW");
    UpdateWindow(hwnd);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
