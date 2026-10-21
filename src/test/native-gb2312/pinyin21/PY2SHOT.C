#include <conio.h>
static void Snapshot(void) {
    outp(0x28,0x10); outp(0x28,0x40); outp(0x28,0xc5); outp(0x28,0);
    outp(0x29,1); outp(0x29,0); outp(0x29,0); outp(0x29,0);
}
#include <windows.h>

/* Test-only Office driver: it focuses a blank editor and toggles WINNLS.
 * DOSBox AUTOTYPE supplies all composition keys. Save dialogs use ASCII fixture
 * filenames. No Chinese text is injected by this helper. */
typedef LRESULT (FAR PASCAL *HOOK)(int, WORD, DWORD);
static HOOK hook;
static int word, ticks, phase, registered, reopening;
static HWND host;
static char filename[64];
static DWORD started;
static DWORD save_after;

static void Log(const char *p)
{
    HFILE f = _lopen("C:\\PY2OFF.LOG", OF_WRITE);
    if (f == HFILE_ERROR) f = _lcreat("C:\\PY2OFF.LOG", 0);
    if (f == HFILE_ERROR) return;
    _llseek(f, 0L, 2); _lwrite(f, p, lstrlen(p)); _lclose(f);
}

static HWND Find(HWND owner, const char *expected, int depth)
{
    HWND c, found;
    char name[40];
    if (depth > 7) return NULL;
    c = GetWindow(owner, GW_CHILD);
    while (c) {
        GetClassName(c, name, sizeof(name));
        if (!lstrcmpi(name, expected) && IsWindowVisible(c)) return c;
        found = Find(c, expected, depth + 1);
        if (found) return found;
        c = GetWindow(c, GW_HWNDNEXT);
    }
    return NULL;
}

static HWND WordDialog(void)
{
    return Find(GetDesktopWindow(), "osa_sdm_Microsoft Word", 0);
}

static void Enter(HWND w)
{
    /* Word's own message loop translates WM_KEYDOWN. Supplying WM_CHAR too
     * can leave a second Return after the dialog has already closed. */
    PostMessage(w, WM_KEYDOWN, VK_RETURN, 1L);
    PostMessage(w, WM_KEYUP, VK_RETURN, 1L);
}

static void Toggle(void)
{
    hook(0, VK_CONTROL, 0L); hook(0, VK_SPACE, 0L);
    hook(0, VK_CONTROL, 0x80000000L);
}

LONG __export FAR PASCAL Probe(HWND w, UINT m, WPARAM wp, LPARAM lp)
{
    HWND app, dialog, edit, document;
    HFILE f;
    char line[100];
    RECT r;
    (void)wp;
    if (m == WM_TIMER) {
        ++ticks; if (!(ticks % 2)) Snapshot();
        if (ticks > 220) { Log("TIMEOUT\r\n"); KillTimer(w, 1); return 0L; }
        if (word && !registered) {
            dialog = WordDialog();
            edit = dialog ? Find(dialog, "OpusFedt", 0) : NULL;
            if (edit) {
                if (!GetWindowTextLength(edit)) SendMessage(edit, WM_SETTEXT, 0, (LPARAM)(LPSTR)"Test");
                SetFocus(edit); Enter(edit); registered = 1;
                Log("FIRST_RUN_ACCEPTED\r\n"); return 0L;
            }
        }
        app = Find(GetDesktopWindow(), word ? "OpusApp" : "XLMAIN", 0);
        if (phase == 4 && !app) {
            f = _lopen(filename, OF_READ);
            if (f != HFILE_ERROR) {
                _lclose(f); Log("FILE_EXISTS\r\nDONE\r\n"); KillTimer(w, 1);
            }
            return 0L;
        }
        if (phase == 4 && word && app) {
            dialog = Find(GetDesktopWindow(), "#32770", 0);
            if (dialog) {
                PostMessage(dialog, WM_COMMAND, IDYES, 0L);
                Log("CLOSE_SAVE_CONFIRMED\r\n"); return 0L;
            }
        }
        if (!app) return 0L;
        /* A visible Word document can precede its startup font/layout work.
         * Let that settle before invoking the synchronous NLS test callback. */
        if (!phase && ticks >= 24) {
            document = word ? Find(app, "OpusWwd", 0) : app;
            if (!document) return 0L;
            SetActiveWindow(app); BringWindowToTop(app); SetFocus(document);
            Log("EDITOR_READY\r\n");
            if (reopening) {
                PostMessage(app, WM_COMMAND, word ? 1391 : 1, 0L);
                phase = 10; return 0L;
            }
            if (!reopening) { Toggle(); Log("NATIVE_IME_ENABLED\r\n"); }
            phase = 1; return 0L;
        }
        if (phase == 10) {
            dialog = word ? WordDialog() : Find(GetDesktopWindow(), "#32770", 0);
            edit = dialog ? Find(dialog, word ? "OpusFedt" : "XLFEDT", 0) : NULL;
            if (edit) {
                SendMessage(edit, WM_SETTEXT, 0, (LPARAM)(LPSTR)
                            (word ? "C:\\WINDOWS\\SOURCE.DOC" : "C:\\WINDOWS\\SOURCE.XLS"));
                if (word) { SetFocus(edit); Enter(edit); }
                else PostMessage(dialog, WM_COMMAND, IDOK, 0L);
                phase = 11; ticks = 0; Log("NATIVE_OPEN\r\n");
            }
            return 0L;
        }
        if (phase == 11 && ticks >= 10) { phase = 1; ticks = 22; return 0L; }
        if (phase == 1 && (reopening ? ticks >= 22 : GetTickCount() - started >= save_after)) {
            if (!reopening) {
                Toggle(); Log("NATIVE_IME_DISABLED\r\n");
                dialog = FindWindow("GBPY_NATIVE", "Pinyin");
                if (dialog) {
                    GetWindowRect(dialog, &r);
                    wsprintf(line, "BAR %d %d %d %d\r\n", r.left, r.top,
                             r.right-r.left, r.bottom-r.top); Log(line);
                }
            }
            PostMessage(app, WM_COMMAND, word ? 1429 : 5, 0L);
            Log("SAVE_AS\r\n"); phase = 2; return 0L;
        }
        if (phase == 2) {
            dialog = word ? WordDialog() : Find(GetDesktopWindow(), "#32770", 0);
            edit = dialog ? Find(dialog, word ? "OpusFedt" : "XLFEDT", 0) : NULL;
            if (edit) {
                SendMessage(edit, WM_SETTEXT, 0, (LPARAM)(LPSTR)filename);
                if (word) { SetFocus(edit); Enter(edit); }
                else PostMessage(dialog, WM_COMMAND, IDOK, 0L);
                phase = 3; ticks = 0; Log("SAVE_ACCEPTED\r\n");
            }
            return 0L;
        }
        if (phase == 3 && ticks == 5 && word) {
            /* Some Word installations do not show Summary on Save. Sending
             * Enter to the document after a completed save edits it again. */
            dialog = WordDialog();
            wsprintf(line, "SUMMARY_CHECK OWNER_ENABLED=%d DIALOG=%u\r\n",
                     IsWindowEnabled(app), (WORD)dialog); Log(line);
            if (dialog && !IsWindowEnabled(app)) {
                edit = Find(dialog, "OpusFedt", 0);
                SetActiveWindow(dialog); SetFocus(edit ? edit : dialog);
                Enter(edit ? edit : dialog); Log("SUMMARY_ACCEPTED\r\n");
            }
            else Log("NO_SUMMARY_DIALOG\r\n");
        }
        if (phase == 3 && ticks >= 10) {
            PostMessage(app, WM_COMMAND, word ? 1575 : 10, 0L);
            Log("NATIVE_CLOSE\r\n"); phase = 4;
        }
        return 0L;
    }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0L; }
    return DefWindowProc(w, m, wp, lp);
}

int PASCAL WinMain(HINSTANCE h, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASS wc;
    MSG msg;
    HINSTANCE nls = LoadLibrary("WINNLS.DLL");
    (void)cmd; (void)show;
    word = GetProfileInt("Pinyin2Test", "Word", 0);
    reopening = GetProfileInt("Pinyin2Test", "Reopen", 0);
    save_after = 70000L;
    lstrcpy(filename, reopening ? "C:\\WINDOWS\\REOPEN." : "C:\\WINDOWS\\PY2OUT.");
    lstrcat(filename, word ? "DOC" : "XLS");
    hook = (HOOK)GetProcAddress(nls, MAKEINTRESOURCE(2));
    if (!hook) return 1;
    if (!prev) {
        wc.style = 0; wc.lpfnWndProc = Probe; wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = h; wc.hIcon = wc.hCursor = NULL; wc.hbrBackground = NULL;
        wc.lpszMenuName = NULL; wc.lpszClassName = "PY2OFF";
        if (!RegisterClass(&wc)) return 2;
    }
    host = CreateWindow("PY2OFF", "", WS_POPUP, 0, 0, 1, 1, NULL, NULL, h, NULL);
    Log("START\r\n"); SetTimer(host, 1, 500, NULL);
    started = GetTickCount();
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg); DispatchMessage(&msg);
    }
    return 0;
}
