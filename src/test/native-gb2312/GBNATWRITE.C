#include <windows.h>

#ifdef NATIVE_E
#define WRITE_PATH "E:\\WIN30GB\\WRITE.EXE"
#define LOG_PATH "E:\\NATWRITE.LOG"
#else
#define WRITE_PATH "C:\\WINDOWS\\WRITE.EXE"
#define LOG_PATH "NATWRITE.LOG"
#endif

/* Test-only native PHON.IME -> MS Write document -> saved WRI probe. */
static HWND host, writer, document, dialog_window;
static HINSTANCE app_instance;
static WORD phase, attempts;

static void Record(char *name, WORD value)
{
    HFILE file = _lopen(LOG_PATH, OF_WRITE);
    char line[60], number[16];
    if (file == HFILE_ERROR) file = _lcreat(LOG_PATH, 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    wsprintf(number, "%d", value);
    lstrcpy(line, name);
    lstrcat(line, "=");
    lstrcat(line, number);
    lstrcat(line, "\r\n");
    _lwrite(file, line, lstrlen(line));
    _lclose(file);
}

BOOL __export FAR PASCAL FindDocument(HWND hwnd, LPARAM unused)
{
    char name[32];
    (void)unused;
    GetClassName(hwnd, name, sizeof(name));
    if (!lstrcmpi(name, "MSWRITE_DOC")) document = hwnd;
    return TRUE;
}

BOOL __export FAR PASCAL FindDialog(HWND hwnd, LPARAM result)
{
    char name[32];
    (void)result;
    GetClassName(hwnd, name, sizeof(name));
    if (!lstrcmpi(name, "#32770")) dialog_window = hwnd;
    return TRUE;
}

static HWND FindEdit(HWND dialog)
{
    HWND child = GetWindow(dialog, GW_CHILD);
    char name[32];
    while (child) {
        GetClassName(child, name, sizeof(name));
        if (!lstrcmpi(name, "EDIT")) return child;
        child = GetWindow(child, GW_HWNDNEXT);
    }
    return NULL;
}

LONG __export FAR PASCAL NativeWriteProc(HWND hwnd, UINT message,
                                          WPARAM wparam, LPARAM lparam)
{
    FARPROC callback;
    HWND ime, edit, ok;
    const char *letter;
    (void)lparam;
    switch (message) {
    case WM_CREATE:
        host = hwnd;
        Record("CREATE", 1);
        Record("TIMER", SetTimer(hwnd, 1, 900, NULL));
        return 0L;
    case WM_TIMER:
        Record("TICK", phase);
        KillTimer(hwnd, 1);
        if (phase == 0) {
            Record("LAUNCH", (WORD)WinExec(WRITE_PATH, SW_SHOWNORMAL));
            ++phase;
        } else if (phase == 1) {
            writer = FindWindow("MSWRITE_MENU", NULL);
            document = NULL;
            callback = MakeProcInstance((FARPROC)FindDocument, app_instance);
            if (writer && callback)
                EnumChildWindows(writer, (WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            if (!document && ++attempts < 25) {
                SetTimer(host, 1, 600, NULL);
                return 0L;
            }
            Record("DOCUMENT", document != NULL);
            if (!document) return 0L;
            BringWindowToTop(writer);
            SetActiveWindow(writer);
            SetFocus(document);
            ime = FindWindow("GBPY_NATIVE", "Pinyin");
            Record("IME", ime != NULL);
            if (!ime) return 0L;
            for (letter = "zhong "; *letter; ++letter)
                PostMessage(ime, WM_CHAR, (BYTE)*letter, 1L);
            ++phase;
        } else if (phase == 2) {
            PostMessage(writer, WM_COMMAND, 4100, 0L);
            ++phase;
        } else if (phase == 3) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            edit = dialog_window ? FindEdit(dialog_window) : NULL;
            if (!edit && ++attempts < 70) {
                SetTimer(host, 1, 500, NULL);
                return 0L;
            }
            Record("SAVE_DIALOG", edit != NULL);
            if (!edit) return 0L;
            SetWindowText(edit, "");
            SetFocus(edit);
            for (letter = "NATWRITE.WRI"; *letter; ++letter)
                SendMessage(edit, WM_CHAR, (BYTE)*letter, 1L);
            ok = GetDlgItem(dialog_window, IDOK);
            Record("OK", ok != NULL);
            if (ok) {
                PostMessage(ok, WM_LBUTTONDOWN, MK_LBUTTON, MAKELONG(8, 8));
                PostMessage(ok, WM_LBUTTONUP, 0, MAKELONG(8, 8));
            }
            ++phase;
            SetTimer(host, 1, 1600, NULL);
            return 0L;
        } else if (phase == 4) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            Record("DIALOG_STILL", dialog_window != NULL);
            Record("SAVE_ISSUED", 1);
            ++phase;
            return 0L;
        }
        SetTimer(host, 1, 900, NULL);
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
    (void)command; (void)show;
    app_instance = instance;
    Record("MAIN", 1);
    if (!previous) {
        wc.style = 0;
        wc.lpfnWndProc = (WNDPROC)NativeWriteProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = wc.hCursor = NULL;
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBNATWRITE";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBNATWRITE", "Write IME review",
                        WS_OVERLAPPEDWINDOW, 0, 0, 180, 70,
                        NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    ShowWindow(hwnd, SW_SHOWNORMAL);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
