#include <windows.h>
#include <string.h>

/* Application-local Excel 2.1d GB2312 editor companion.  The installed
 * EXCEL.EXE starts the unchanged localized core as XLCORE.EXE, then remains
 * hidden only while that Excel instance is running.  It does not install a
 * system hook or change Windows files. */
#define WM_XLGB_KEY (WM_USER + 60)
#define MAX_FORMULA_TEXT 260
#define INPUT_SENTINEL 0x7FFE0001L

static HWND host_window;
static HWND formula_window;
static WNDPROC original_formula_proc;
static FARPROC formula_callback;
static FARPROC root_callback;
static FARPROC child_callback;
static BOOL sending_key;
/* Serialize deferred input: WM_GETTEXT can yield to the source task, which
 * can enqueue the trail byte while the lead-byte edit is still in progress. */
static WORD input_keys[64], input_chars[64];
static unsigned input_head, input_count;
static BOOL input_busy;
static WORD input_lead;
static void QueueInput(WORD key, WORD character) {
    unsigned tail;
    if (input_count >= 64) { MessageBeep(0); return; }
    tail=(input_head+input_count)%64;
    input_keys[tail]=key; input_chars[tail]=character; ++input_count;
    if (!input_busy && !PostMessage(host_window,WM_XLGB_KEY,0,0L)) {
        --input_count; MessageBeep(0);
    }
}
static BOOL excel_seen;
static BOOL excel_found;
static unsigned int missing_ticks;
static unsigned int startup_ticks;

static BOOL IsGbPair(const unsigned char *text, unsigned int length,
                     unsigned int caret)
{
    unsigned int index = 0;
    while (index < caret && index < length) {
        if (index + 1 < length && text[index] >= 0xA1 &&
            text[index] <= 0xF7 && text[index + 1] >= 0xA1 &&
            text[index + 1] <= 0xFE)
            index += 2;
        else ++index;
    }
    return index == caret && caret + 1 < length &&
           text[caret] >= 0xA1 && text[caret] <= 0xF7 &&
           text[caret + 1] >= 0xA1 && text[caret + 1] <= 0xFE;
}

static unsigned int AlignedCaret(const unsigned char *text,
                                 unsigned int length, unsigned int caret,
                                 BOOL toward_end)
{
    unsigned int index = 0;
    while (index < length) {
        unsigned int width = IsGbPair(text, length, index) ? 2 : 1;
        if (caret == index + 1 && width == 2)
            return toward_end ? index + 2 : index;
        if (caret <= index) break;
        index += width;
    }
    return caret;
}

LONG __export FAR PASCAL FormulaProc(HWND window, UINT message,
                                    WPARAM key, LPARAM flags)
{
    LONG result;
    WNDPROC previous = original_formula_proc;
    /* TranslateMessage also queues WM_CHAR(Backspace).  The deferred handler
     * sends the complete one- or two-byte edit; discard that queued char. */
    if (window == formula_window && message == WM_CHAR &&
        key == VK_BACK && flags != INPUT_SENTINEL) return 0L;
    if (window == formula_window && message == WM_KEYDOWN &&
        (key == VK_DELETE || key == VK_BACK ||
         key == VK_LEFT || key == VK_RIGHT) && flags != INPUT_SENTINEL) {
        /* Excel's interpreter cannot answer WM_GETTEXT reentrantly here.
         * Return to its message loop before querying the formula editor. */
        QueueInput(key,0);
        /* A full queue must not fall through to Excel's byte-wise editor. */
        return 0L;
    }
    /* Direct typing over a byte selection must expand to whole GB pairs too.
     * Query Excel only at the existing deferred, message-loop safe point. */
    if (window == formula_window && message == WM_CHAR && key >= 32 && flags != INPUT_SENTINEL) {
        if (input_lead) {
            if (key >= 0xA1 && key <= 0xFE) QueueInput(input_lead | (key << 8),2);
            else MessageBeep(0);
            input_lead=0;
        } else if (key >= 0xA1 && key <= 0xF7) input_lead=key;
        else QueueInput(key,1);
        return 0L;
    }
    result = CallWindowProc((FARPROC)previous, window, message, key, flags);
    if (window == formula_window && message == WM_NCDESTROY) {
        formula_window = NULL;
        original_formula_proc = NULL;
    }
    return result;
}

BOOL __export FAR PASCAL FindExcelChild(HWND window, LPARAM unused)
{
    char class_name[24];
    WNDPROC previous;
    (void)unused;
    if (formula_window) return TRUE;
    GetClassName(window, class_name, sizeof(class_name));
    if (lstrcmpi(class_name, "XLFEDT")) return TRUE;
    previous = (WNDPROC)SetWindowLong(window, GWL_WNDPROC,
                                      (LONG)formula_callback);
    if (previous) {
        original_formula_proc = previous;
        formula_window = window;
    }
    return TRUE;
}

BOOL __export FAR PASCAL FindExcelRoot(HWND window, LPARAM unused)
{
    char class_name[24];
    (void)unused;
    GetClassName(window, class_name, sizeof(class_name));
    /* Excel's Font expansion restores its historic 146-unit height.
     * The 5.2 CGA template has compact controls; keep its outer window in view.
     * Match the native owner and four font-only IDs, never other applications. */
    if (GetSystemMetrics(SM_CYSCREEN) <= 200 &&
        !lstrcmpi(class_name, "#32770") && IsWindowVisible(window) &&
        GetDlgItem(window,514) && GetDlgItem(window,515) &&
        GetDlgItem(window,516) && GetDlgItem(window,520)) {
        HWND owner = GetParent(window);
        RECT bounds;
        char owner_class[24];
        GetClassName(owner,owner_class,sizeof(owner_class));
        GetWindowRect(window,&bounds);
        if (!lstrcmpi(owner_class,"XLMAIN") && bounds.bottom-bounds.top > 200)
            SetWindowPos(window,NULL,bounds.left,6,bounds.right-bounds.left,188,
                         SWP_NOZORDER|SWP_NOACTIVATE);
    }
    if (lstrcmpi(class_name, "XLMAIN")) return TRUE;
    excel_found = TRUE;
    excel_seen = TRUE;
    if (!formula_window)
        EnumChildWindows(window, (WNDENUMPROC)child_callback, 0L);
    return TRUE;
}

static void ProcessInput(WPARAM key, LPARAM flags) {
        if (formula_window &&
            IsWindow(formula_window) && original_formula_proc) {
            char text[MAX_FORMULA_TEXT];
            unsigned int length, caret, finish, count, index;
            LONG selection;
            length = (unsigned int)SendMessage(formula_window, WM_GETTEXT,
                                               sizeof(text),
                                               (LPARAM)(LPSTR)text);
            if (length >= sizeof(text) - 1) {
                MessageBeep(0);
                return;
            }
            selection = SendMessage(formula_window, EM_GETSEL, 0, 0L);
            caret = LOWORD(selection);
            finish = HIWORD(selection);
            if (caret > length || finish > length) {
                MessageBeep(0);
                return;
            }
            if (caret == finish) {
                BOOL toward_end = !flags && (key == VK_BACK || key == VK_LEFT);
                caret = AlignedCaret((const unsigned char *)text, length,
                                     caret, toward_end);
                finish = caret;
            } else {
                caret = AlignedCaret((const unsigned char *)text, length,
                                     caret, FALSE);
                finish = AlignedCaret((const unsigned char *)text, length,
                                      finish, TRUE);
            }
            if (caret != LOWORD(selection) || finish != HIWORD(selection)) {
                LONG aligned;
                SendMessage(formula_window, EM_SETSEL, 0,
                            MAKELONG(caret, finish));
                aligned = SendMessage(formula_window, EM_GETSEL, 0, 0L);
                if (LOWORD(aligned) != caret || HIWORD(aligned) != finish) {
                    MessageBeep(0);
                    return;
                }
            }
            count = flags == 2 ? 2 : 1;
            if (!flags && caret == finish) {
                if ((key == VK_DELETE || key == VK_RIGHT) &&
                    IsGbPair((const unsigned char *)text, length, caret))
                    count = 2;
                if ((key == VK_BACK || key == VK_LEFT) && caret >= 2 &&
                    IsGbPair((const unsigned char *)text, length, caret - 2))
                    count = 2;
            }
            sending_key = TRUE;
            for (index = 0; index < count; ++index)
                SendMessage(formula_window,
                            flags || key == VK_BACK ? WM_CHAR : WM_KEYDOWN,
                            flags == 2 ? (index ? HIBYTE(key) : LOBYTE(key)) : key, INPUT_SENTINEL);
            sending_key = FALSE;
        }
}

LONG __export FAR PASCAL HelperProc(HWND window, UINT message,
                                   WPARAM key, LPARAM flags)
{
    switch (message) {
    case WM_TIMER:
        excel_found = FALSE;
        EnumWindows((WNDENUMPROC)root_callback, 0L);
        if (excel_seen && !excel_found) {
            if (++missing_ticks >= 10) DestroyWindow(window);
        } else missing_ticks = 0;
        if (!excel_seen && ++startup_ticks >= 150) DestroyWindow(window);
        return 0L;
    case WM_XLGB_KEY:
        if (!input_busy && input_count) {
            WORD input_key=input_keys[input_head], character=input_chars[input_head];
            input_head=(input_head+1)%64; --input_count; input_busy=TRUE;
            ProcessInput(input_key,character); input_busy=FALSE;
            if(input_count) PostMessage(host_window,WM_XLGB_KEY,0,0L);
        }
        return 0L;
    case WM_DESTROY:
        KillTimer(window, 1);
        PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(window, message, key, flags);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    WNDCLASS wc;
    HWND window;
    MSG event;
    char path[160], launch[256];
    char *name;
    UINT started, path_length;
    (void)show;
    if (previous) return 2;
    path_length = GetModuleFileName(instance, path, sizeof(path));
    if (!path_length || path_length >= sizeof(path)) return 3;
    path[path_length] = 0;
    name = strrchr(path, '\\');
    if (!name || name - path > 120) return 4;
    lstrcpy(name + 1, "XLCORE.EXE");
    lstrcpy(launch, path);
    if (command && *command) {
        if (lstrlen(launch) + lstrlen(command) + 2 >= sizeof(launch))
            return 5;
        lstrcat(launch, " ");
        lstrcat(launch, command);
    }
    wc.style = 0;
    wc.lpfnWndProc = (WNDPROC)HelperProc;
    wc.cbClsExtra = wc.cbWndExtra = 0;
    wc.hInstance = instance;
    wc.hIcon = wc.hCursor = NULL;
    wc.hbrBackground = NULL;
    wc.lpszMenuName = NULL;
    wc.lpszClassName = "XLGB_HELPER";
    if (!RegisterClass(&wc)) return 6;
    window = CreateWindow("XLGB_HELPER", "", WS_POPUP,
                          0, 0, 1, 1, NULL, NULL, instance, NULL);
    if (!window) return 7;
    host_window = window;
    formula_callback = MakeProcInstance((FARPROC)FormulaProc, instance);
    root_callback = MakeProcInstance((FARPROC)FindExcelRoot, instance);
    child_callback = MakeProcInstance((FARPROC)FindExcelChild, instance);
    if (!formula_callback || !root_callback || !child_callback) return 8;
    SetTimer(window, 1, 400, NULL);
    started = WinExec(launch, SW_SHOW);
    if (started < 32) return 9;
    while (GetMessage(&event, NULL, 0, 0)) {
        TranslateMessage(&event);
        DispatchMessage(&event);
    }
    FreeProcInstance(formula_callback);
    FreeProcInstance(root_callback);
    FreeProcInstance(child_callback);
    return 0;
}
