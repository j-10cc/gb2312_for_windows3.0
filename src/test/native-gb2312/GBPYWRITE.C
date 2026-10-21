#include <windows.h>
#include <string.h>

/* Exercise Pinyin through Write's real document window, then save the WRI. */
static HWND runner, write_window, document_window, dialog_window;
static HINSTANCE app_instance;
static WORD phase, attempts;
static LONG document_proc_after_toggle;
static BYTE buffer[1024];

static void Record(char *name, int value)
{
    HFILE file = _lopen("E:\\PYWRITE.LOG", OF_WRITE);
    char line[64], number[16];
    if (file == HFILE_ERROR) file = _lcreat("E:\\PYWRITE.LOG", 0);
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

BOOL __export FAR PASCAL FindDocument(HWND hwnd, LPARAM ignored)
{
    char name[32];
    (void)ignored;
    GetClassName(hwnd, name, sizeof(name));
    if (lstrcmpi(name, "MSWRITE_DOC") == 0) document_window = hwnd;
    return TRUE;
}

BOOL __export FAR PASCAL FindDialog(HWND hwnd, LPARAM ignored)
{
    char name[32];
    (void)ignored;
    GetClassName(hwnd, name, sizeof(name));
    if (lstrcmpi(name, "#32770") == 0) dialog_window = hwnd;
    return TRUE;
}

static HWND FindEdit(HWND dialog)
{
    HWND child = GetWindow(dialog, GW_CHILD);
    char name[32];
    while (child) {
        GetClassName(child, name, sizeof(name));
        if (lstrcmpi(name, "EDIT") == 0) return child;
        child = GetWindow(child, GW_HWNDNEXT);
    }
    return NULL;
}

static void Next(WORD milliseconds)
{
    SetTimer(runner, 1, milliseconds, NULL);
}

static void TogglePinyin(void)
{
    SendMessage(document_window, WM_KEYDOWN, VK_CONTROL, 1L);
    SendMessage(document_window, WM_KEYDOWN, VK_SPACE, 1L);
    SendMessage(document_window, WM_KEYUP, VK_SPACE, 1L);
    SendMessage(document_window, WM_KEYUP, VK_CONTROL, 1L);
}

static void SeedClipboard(void)
{
    HGLOBAL handle;
    LPSTR data;
    handle = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, 5);
    if (!handle) { Record("PASTE_ALLOC", 0); return; }
    data = GlobalLock(handle);
    if (!data) { GlobalFree(handle); Record("PASTE_LOCK", 0); return; }
    lstrcpy(data, "KEEP");
    GlobalUnlock(handle);
    if (!OpenClipboard(runner)) {
        GlobalFree(handle);
        Record("PASTE_OPEN", 0);
        return;
    }
    EmptyClipboard();
    if (!SetClipboardData(CF_TEXT, handle)) {
        CloseClipboard();
        GlobalFree(handle);
        Record("PASTE_SET", 0);
        return;
    }
    CloseClipboard();
    Record("CLIP_SEEDED", 1);
}

LONG __export FAR PASCAL RunnerProc(HWND hwnd, UINT message,
                                    WPARAM wparam, LPARAM lparam)
{
    FARPROC callback;
    HWND edit, ok;
    HWND ime;
    char *letter;
    HFILE file;
    WORD found = 0, i, length;
    (void)wparam; (void)lparam;
    if (message == WM_CREATE) {
        runner = hwnd;
        Record("CREATE", 1);
        Record("TIMER", SetTimer(hwnd, 1, 900, NULL));
        return 0L;
    }
    if (message == WM_TIMER) {
        Record("TICK", phase);
        KillTimer(hwnd, 1);
        if (phase == 0) {
            Record("LAUNCH", (WORD)WinExec("E:\\WIN30GB\\WRITE.EXE", SW_SHOWNORMAL));
            phase = 1;
            Next(900);
            return 0L;
        }
        if (phase == 1) {
            write_window = FindWindow("MSWRITE_MENU", NULL);
            document_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDocument, app_instance);
            if (write_window && callback)
                EnumChildWindows(write_window, (WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            if (!document_window && attempts++ < 20) { Next(500); return 0L; }
            Record("DOCUMENT", document_window != NULL);
            Record("IME", FindWindow("phon", "Pinyin GB2312") != NULL);
            if (!document_window) return 0L;
            BringWindowToTop(write_window);
            SetActiveWindow(write_window);
            SetFocus(document_window);
            Record("FOCUS", GetFocus() == document_window);
            SeedClipboard();
            PostMessage(document_window, WM_KEYDOWN, VK_CONTROL, 1L);
            PostMessage(document_window, WM_KEYDOWN, VK_SPACE, 1L);
            PostMessage(document_window, WM_KEYUP, VK_SPACE, 1L);
            PostMessage(document_window, WM_KEYUP, VK_CONTROL, 1L);
            phase = 2;
            Next(700);
            return 0L;
        }
        if (phase == 2) {
            ime = FindWindow("phon", "Pinyin GB2312");
            Record("IME_VISIBLE", IsWindowVisible(ime));
            document_proc_after_toggle = GetWindowLong(document_window, GWL_WNDPROC);
            if (ime) for (letter = "zhong"; *letter; ++letter)
                PostMessage(ime, WM_CHAR, (BYTE)*letter, 1L);
            phase = 3;
            Next(1600);
            return 0L;
        }
        if (phase == 3) {
            ime = FindWindow("phon", "Pinyin GB2312");
            if (ime) PostMessage(ime, WM_CHAR, ' ', 1L);
            phase = 4;
            Next(1400);
            return 0L;
        }
        if (phase == 4) {
            HWND previous_document = document_window;
            document_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDocument, app_instance);
            if (write_window && callback)
                EnumChildWindows(write_window, (WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            Record("DOCUMENT_AFTER", document_window != NULL);
            Record("DOCUMENT_SAME", document_window == previous_document);
            if (document_window)
                Record("DOCUMENT_PROC_SAME",
                       GetWindowLong(document_window, GWL_WNDPROC) ==
                       document_proc_after_toggle);
            if (document_window) SetFocus(document_window);
            Record("FOCUS_AFTER", GetFocus() == document_window);
            Record("ACTIVE_TOP", GetActiveWindow() == write_window);
            ime = FindWindow("phon", "Pinyin GB2312");
            if (OpenClipboard(runner)) {
                HGLOBAL current = GetClipboardData(CF_TEXT);
                LPSTR data = current ? GlobalLock(current) : NULL;
                Record("CLIP_RESTORED", data && lstrcmp(data, "KEEP") == 0);
                if (data) GlobalUnlock(current);
                CloseClipboard();
            } else Record("CLIP_RESTORED", 0);
            TogglePinyin();
            phase = 5;
            Next(600);
            return 0L;
        }
        if (phase == 5) {
            ime = FindWindow("phon", "Pinyin GB2312");
            Record("IME_CLOSED", ime && !IsWindowVisible(ime));
            TogglePinyin();
            phase = 6;
            Next(600);
            return 0L;
        }
        if (phase == 6) {
            ime = FindWindow("phon", "Pinyin GB2312");
            Record("IME_REOPEN", ime && IsWindowVisible(ime));
            TogglePinyin();
            phase = 7;
            Next(600);
            return 0L;
        }
        if (phase == 7) {
            ime = FindWindow("phon", "Pinyin GB2312");
            Record("IME_RECLOSED", ime && !IsWindowVisible(ime));
            PostMessage(write_window, WM_COMMAND, 4100, 0L);
            phase = 8;
            Next(1000);
            return 0L;
        }
        if (phase == 8) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            edit = dialog_window ? FindEdit(dialog_window) : NULL;
            if (!edit && attempts++ < 45) { Next(500); return 0L; }
            Record("SAVE_DIALOG", edit != NULL);
            if (!edit) return 0L;
            SetWindowText(edit, "");
            SetFocus(edit);
            for (letter = "PYWRITE.WRI"; *letter; ++letter)
                SendMessage(edit, WM_CHAR, (BYTE)*letter, 1L);
            ok = GetDlgItem(dialog_window, IDOK);
            if (ok) {
                PostMessage(ok, WM_LBUTTONDOWN, MK_LBUTTON, MAKELONG(8,8));
                PostMessage(ok, WM_LBUTTONUP, 0, MAKELONG(8,8));
            }
            phase = 9;
            Next(1500);
            return 0L;
        }
        if (phase == 9) {
            char title[100];
            GetWindowText(write_window, title, sizeof(title));
            Record("SAVED_TITLE", strstr(title, "PYWRITE.WRI") != NULL);
            file = _lopen("E:\\WIN30GB\\PYWRITE.WRI", OF_READ);
            Record("WRI_OPEN", file != HFILE_ERROR);
            if (file != HFILE_ERROR) {
                length = _lread(file, buffer, sizeof(buffer));
                for (i = 0; i + 1 < length; ++i)
                    if (buffer[i] == 0xD6 && buffer[i+1] == 0xD0) ++found;
                Record("GB_ZHONG", found);
                Record("WRI_BYTES", length);
                _lclose(file);
            }
            phase = 10;
            return 0L;
        }
    }
    if (message == WM_DESTROY) PostQuitMessage(0);
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
        wc.lpfnWndProc = (WNDPROC)RunnerProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = NULL;
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBPinyinWriteProbe";
        if (!RegisterClass(&wc)) { Record("CLASSFAIL", 1); return 1; }
    }
    Record("CLASS", 1);
    hwnd = CreateWindow("GBPinyinWriteProbe", "Pinyin Write probe",
                        WS_OVERLAPPEDWINDOW, 0, 0, 180, 70,
                        NULL, NULL, instance, NULL);
    if (!hwnd) { Record("WINDOWFAIL", 1); return 2; }
    Record("WINDOW", 1);
    ShowWindow(hwnd, SW_SHOWNORMAL);
    Record("SHOWN", 1);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
