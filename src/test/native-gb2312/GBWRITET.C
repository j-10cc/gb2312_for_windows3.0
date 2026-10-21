#include <windows.h>
#include <string.h>

/* Drives the actual Windows 3.0 Write application in a disposable image.
   The test sends GB2312 bytes directly to Write's document window. */

static HWND write_window;
static HWND document_window;
static HWND dialog_window;
static HWND runner_window;
static int phase, retries;
static HINSTANCE app_instance;

static void Record(char *stage, int value)
{
    HFILE file = _lopen("C:\\GBWRITE.LOG", OF_WRITE);
    char line[64], number[16];
    if (file == HFILE_ERROR) file = _lcreat("C:\\GBWRITE.LOG", 0);
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

static void RecordLong(char *stage, long value)
{
    HFILE file = _lopen("C:\\GBWRITE.LOG", OF_WRITE);
    char line[64], number[20];
    if (file == HFILE_ERROR) file = _lcreat("C:\\GBWRITE.LOG", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    lstrcpy(line, stage);
    lstrcat(line, "=");
    wsprintf(number, "%ld", value);
    lstrcat(line, number);
    lstrcat(line, "\r\n");
    _lwrite(file, line, lstrlen(line));
    _lclose(file);
}

static void RecordText(char *stage, char *value)
{
    HFILE file = _lopen("C:\\GBWRITE.LOG", OF_WRITE);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    _lwrite(file, stage, lstrlen(stage));
    _lwrite(file, "=", 1);
    _lwrite(file, value, lstrlen(value));
    _lwrite(file, "\r\n", 2);
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
    char name[32], title[80];
    (void)ignored;
    GetClassName(hwnd, name, sizeof(name));
    if (lstrcmpi(name, "#32770") == 0) {
        GetWindowText(hwnd, title, sizeof(title));
        RecordText("DIALOG", title);
        dialog_window = hwnd;
    }
    return TRUE;
}

static HWND FindDialogEdit(HWND dialog)
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

static int PasteText(char *text)
{
    HGLOBAL handle;
    LPSTR data;
    Record("CLIP_LEN", lstrlen(text));
    handle = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, lstrlen(text) + 1);
    if (!handle) { Record("CLIP_ALLOC", 0); return 0; }
    data = GlobalLock(handle);
    if (!data) { GlobalFree(handle); Record("CLIP_LOCK", 0); return 0; }
    lstrcpy(data, text);
    GlobalUnlock(handle);
    if (!OpenClipboard(runner_window)) {
        GlobalFree(handle);
        Record("CLIP_OPEN", 0);
        return 0;
    }
    EmptyClipboard();
    if (!SetClipboardData(CF_TEXT, handle)) {
        CloseClipboard();
        GlobalFree(handle);
        Record("CLIP_SET", 0);
        return 0;
    }
    CloseClipboard();
    Record("CLIP_AVAILABLE", IsClipboardFormatAvailable(CF_TEXT));
    Record("PASTE_STATE", GetMenuState(GetMenu(write_window), 4115,
                                        MF_BYCOMMAND));
    Record("PASTE_RET", (int)SendMessage(write_window, WM_COMMAND, 4115, 0L));
    return 1;
}

static void WriteComplexText(void)
{
    static char title[] = "GB2312 \xD6\xD0\xCE\xC4 \xBC\xF2\xCC\xE5\r\n";
    static char line[] = "\xD6\xD0\xCE\xC4 \xBC\xF2\xCC\xE5\tABC 123\r\n";
    static char body[2500];
    int row;
    BringWindowToTop(write_window);
    SetActiveWindow(write_window);
    SetFocus(document_window);
    Record("FOCUS", GetFocus() == document_window);
    SendMessage(write_window, WM_COMMAND, 4226, 0L);
    SendMessage(write_window, WM_COMMAND, 4161, 0L);
    PasteText(title);
    SendMessage(write_window, WM_COMMAND, 4161, 0L);
    SendMessage(write_window, WM_COMMAND, 4225, 0L);
    body[0] = '\0';
    for (row = 0; row < 68; ++row)
        lstrcat(body, line);
    PasteText(body);
    Record("TYPED_ROWS", row);
}

LONG __export FAR PASCAL RunnerProc(HWND hwnd, UINT message,
                                    WPARAM wparam, LPARAM lparam)
{
    FARPROC callback;
    HWND edit;
    HFILE file;
    (void)wparam; (void)lparam;
    if (message == WM_CREATE) {
        runner_window = hwnd;
        Record("LAUNCH", (WORD)WinExec("C:\\WINDOWS\\WRITE.EXE", SW_SHOWNORMAL));
        SetTimer(hwnd, 1, 900, NULL);
        return 0L;
    }
    if (message == WM_TIMER) {
        KillTimer(hwnd, 1);
        if (phase == 0) {
            write_window = FindWindow("MSWRITE_MENU", NULL);
            document_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDocument, app_instance);
            if (write_window && callback)
                EnumChildWindows(write_window, (WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            if (!document_window && retries++ < 15) {
                SetTimer(hwnd, 1, 600, NULL);
                return 0L;
            }
            Record("DOCUMENT", document_window ? 1 : 0);
            if (!document_window) return 0L;
            phase = 1;
            WriteComplexText();
            PostMessage(write_window, WM_COMMAND, 4100, 0L);
            SetTimer(hwnd, 1, 900, NULL);
            return 0L;
        }
        if (phase == 1) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            edit = dialog_window ? FindDialogEdit(dialog_window) : NULL;
            if (!edit && retries++ < 30) {
                SetTimer(hwnd, 1, 500, NULL);
                return 0L;
            }
            Record("SAVE_DIALOG", edit ? 1 : 0);
            if (!edit) return 0L;
            Record("EDIT_ID", GetDlgCtrlID(edit));
            SetWindowText(edit, "");
            SetFocus(edit);
            {
                char *letter = "GBCOMPLE.WRI";
                while (*letter)
                    SendMessage(edit, WM_CHAR, (BYTE)*letter++, 1L);
            }
            {
                char name[40];
                GetWindowText(edit, name, sizeof(name));
                RecordText("EDIT_TEXT", name);
            }
            {
                HWND ok = GetDlgItem(dialog_window, IDOK);
                Record("SAVE_BUTTON", ok ? 1 : 0);
                if (ok) {
                    PostMessage(ok, WM_LBUTTONDOWN, MK_LBUTTON,
                                MAKELONG(8, 8));
                    PostMessage(ok, WM_LBUTTONUP, 0, MAKELONG(8, 8));
                }
            }
            phase = 2;
            SetTimer(hwnd, 1, 1500, NULL);
            return 0L;
        }
        if (phase == 2) {
            char title[100];
            GetWindowText(write_window, title, sizeof(title));
            if (!strstr(title, "GBCOMPLE.WRI") && retries++ < 35) {
                SetTimer(hwnd, 1, 500, NULL);
                return 0L;
            }
            RecordText("WRITE_TITLE", title);
            Record("SAVED", strstr(title, "GBCOMPLE.WRI") != NULL);
            file = _lopen("C:\\WINDOWS\\GBCOMPLE.WRI", OF_READ);
            if (file != HFILE_ERROR) {
                Record("WRI_SIZE", (int)_llseek(file, 0L, 2));
                _lclose(file);
            } else Record("WRI_LOCKED", 1);
            PostMessage(write_window, WM_COMMAND, 4101, 0L);
            phase = 3;
            SetTimer(hwnd, 1, 1000, NULL);
            return 0L;
        }
        if (phase == 3) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            Record("PRINT_DIALOG", dialog_window ? 1 : 0);
            if (dialog_window) {
                HWND ok = GetDlgItem(dialog_window, IDOK);
                if (ok) {
                    PostMessage(ok, WM_LBUTTONDOWN, MK_LBUTTON,
                                MAKELONG(8, 8));
                    PostMessage(ok, WM_LBUTTONUP, 0, MAKELONG(8, 8));
                }
            }
            phase = 4;
            SetTimer(hwnd, 1, 3500, NULL);
            return 0L;
        }
        if (phase == 4) {
            file = _lopen("C:\\WINDOWS\\GBPRINT.PRN", OF_READ);
            Record("PRINT_FILE", file != HFILE_ERROR);
            if (file != HFILE_ERROR) {
                RecordLong("PRINT_SIZE", _llseek(file, 0L, 2));
                _lclose(file);
            }
            phase = 5;
            PostMessage(write_window, WM_COMMAND, 4097, 0L);
            SetTimer(hwnd, 1, 1200, NULL);
            return 0L;
        }
        if (phase == 5) {
            char title[100];
            HWND no;
            GetWindowText(write_window, title, sizeof(title));
            RecordText("NEW_TITLE", title);
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            no = dialog_window ? GetDlgItem(dialog_window, IDNO) : NULL;
            Record("DISCARD_PROMPT", no ? 1 : 0);
            if (no) {
                PostMessage(no, WM_LBUTTONDOWN, MK_LBUTTON,
                            MAKELONG(8, 8));
                PostMessage(no, WM_LBUTTONUP, 0, MAKELONG(8, 8));
            }
            phase = 6;
            SetTimer(hwnd, 1, 1000, NULL);
            return 0L;
        }
        if (phase == 6) {
            char title[100];
            GetWindowText(write_window, title, sizeof(title));
            if (strstr(title, "GBCOMPLE.WRI") && retries++ < 18) {
                SetTimer(hwnd, 1, 500, NULL);
                return 0L;
            }
            RecordText("EMPTY_TITLE", title);
            PostMessage(write_window, WM_COMMAND, 4098, 0L);
            phase = 7;
            SetTimer(hwnd, 1, 900, NULL);
            return 0L;
        }
        if (phase == 7) {
            dialog_window = NULL;
            callback = MakeProcInstance((FARPROC)FindDialog, app_instance);
            if (callback) EnumWindows((WNDENUMPROC)callback, 0L);
            if (callback) FreeProcInstance(callback);
            edit = dialog_window ? FindDialogEdit(dialog_window) : NULL;
            if (!edit && retries++ < 25) {
                SetTimer(hwnd, 1, 500, NULL);
                return 0L;
            }
            Record("OPEN_DIALOG", edit ? 1 : 0);
            if (!edit) return 0L;
            SetWindowText(edit, "");
            SetFocus(edit);
            {
                char *letter = "GBCOMPLE.WRI";
                while (*letter)
                    SendMessage(edit, WM_CHAR, (BYTE)*letter++, 1L);
            }
            {
                HWND ok = GetDlgItem(dialog_window, IDOK);
                if (ok) {
                    PostMessage(ok, WM_LBUTTONDOWN, MK_LBUTTON,
                                MAKELONG(8, 8));
                    PostMessage(ok, WM_LBUTTONUP, 0, MAKELONG(8, 8));
                }
            }
            phase = 8;
            SetTimer(hwnd, 1, 1800, NULL);
            return 0L;
        }
        if (phase == 8) {
            char title[100];
            GetWindowText(write_window, title, sizeof(title));
            if (!strstr(title, "GBCOMPLE.WRI") && retries++ < 25) {
                SetTimer(hwnd, 1, 600, NULL);
                return 0L;
            }
            RecordText("REOPEN_TITLE", title);
            Record("REOPENED", strstr(title, "GBCOMPLE.WRI") != NULL);
            phase = 9;
            return 0L;
        }
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
    app_instance = instance;
    if (!previous) {
        wc.style = 0;
        wc.lpfnWndProc = (WNDPROC)RunnerProc;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = NULL;
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBWriteTest";
        if (!RegisterClass(&wc)) return 1;
    }
    hwnd = CreateWindow("GBWriteTest", "Write print test", WS_POPUP,
                        0, 0, 1, 1, NULL, NULL, instance, NULL);
    if (!hwnd) return 2;
    ShowWindow(hwnd, SW_HIDE);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return (int)msg.wParam;
}
