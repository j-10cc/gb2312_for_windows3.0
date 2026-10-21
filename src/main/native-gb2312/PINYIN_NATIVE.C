#include <windows.h>
#include <string.h>

/* Windows 3.0 native WINNLS IME for the PHON.IME slot.  WINNLS owns the
 * keyboard hook and sends key messages to this window while enabled. */
#define WM_IME_REPORT 0x010a
#define WM_IME_INPUT (WM_USER + 16)
#define WM_IME_ENABLE (WM_USER + 17)

typedef BOOL (FAR PASCAL *SET_IME_HANDLE)(LPCSTR, HWND);
typedef void (FAR PASCAL *SET_KEYBOARD_HOOK)(BOOL);
typedef void (FAR PASCAL *SET_SYSTEM_IME)(HWND);
#ifdef PINYIN_DIAGNOSTICS
typedef LRESULT (FAR PASCAL *KEYBOARD_HOOK)(int, WORD, DWORD);
static KEYBOARD_HOOK diagnostic_hook;
static void Diag(WORD stage, WORD value)
{
    HFILE file = _lopen("C:\\PYDIAG.BIN", OF_WRITE);
    WORD record[2];
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYDIAG.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    record[0] = stage;
    record[1] = value;
    _lwrite(file, (LPSTR)record, 4);
    _lclose(file);
}
#endif

#include "PINYIN_DICT.H"
static BYTE heading_bitmap[2][32];
static BOOL heading_available[2];
static HWND ime_window, target_window;
static BOOL ctrl_down, alt_down, ime_enabled;
static WORD shortcut_key;
static HWND docked_window;
static RECT docked_original, docked_bounds;
static HWND input_focus;

static HWND InputFocus(void)
{
    return input_focus && IsWindow(input_focus) ? input_focus : GetFocus();
}

static BOOL CompactBar(void)
{
    return GetSystemMetrics(SM_CYSCREEN) <= 200;
}

static int ImeHeight(void)
{
    return CompactBar() ? 24 : 40;
}

static void RestoreApplication(void)
{
    RECT current;
    if (docked_window && IsWindow(docked_window)) {
        GetWindowRect(docked_window, &current);
        /* Respect a user's own move/resize while the bar was enabled. */
        if (EqualRect(&current, &docked_bounds))
            SetWindowPos(docked_window, NULL, docked_original.left,
                         docked_original.top,
                         docked_original.right - docked_original.left,
                         docked_original.bottom - docked_original.top,
                         SWP_NOACTIVATE | SWP_NOZORDER);
    }
    docked_window = NULL;
}

static void FitApplication(void)
{
    HWND active = GetActiveWindow();
    RECT r;
    int bottom = GetSystemMetrics(SM_CYSCREEN) - ImeHeight();
    if (!ime_enabled) { RestoreApplication(); return; }
    if (!active || active == ime_window || active == docked_window) return;
    /* Excel activates an editing popup while its workbook remains the same
     * application. Keep the reserved strip through that internal transition. */
    if (docked_window && IsWindow(docked_window) &&
        GetWindowTask(active) == GetWindowTask(docked_window)) return;
    RestoreApplication();
    if (!active || !IsZoomed(active)) return;
    GetWindowRect(active, &r);
    if (r.bottom <= bottom || r.top >= bottom) return;
    docked_window = active;
    docked_original = r;
    SetWindowPos(active, NULL, r.left, r.top, r.right - r.left,
                 bottom - r.top, SWP_NOACTIVATE | SWP_NOZORDER);
    GetWindowRect(active, &docked_bounds);
}

/* Win3 task queues can contain only eight messages. Keep undelivered events
 * locally and retry after the destination has run; WM_CHAR DBCS pairs must
 * enter its real queue, since synchronous SendMessage bypasses USER assembly. */
#define OUTPUT_CAPACITY 128
typedef struct {
    HWND window;
    UINT message;
    WPARAM wparam;
    LPARAM lparam;
} OUTPUT_EVENT;
static OUTPUT_EVENT output[OUTPUT_CAPACITY];
static WORD output_head, output_count;
static BOOL output_draining;

static void DrainOutput(void)
{
    OUTPUT_EVENT *event;
    if (output_draining) return;
    output_draining = TRUE;
    while (output_count) {
        event = output + output_head;
        if (IsWindow(event->window) &&
            !PostMessage(event->window, event->message, event->wparam, event->lparam))
            break;
        output_head = (output_head + 1) % OUTPUT_CAPACITY;
        --output_count;
    }
    if (output_count) SetTimer(ime_window, 3, 25, NULL);
    else KillTimer(ime_window, 3);
    output_draining = FALSE;
}

static BOOL QueueMessage(HWND window, UINT message, WPARAM wp, LPARAM lp)
{
    OUTPUT_EVENT *event;
    DrainOutput();
    if (output_count == OUTPUT_CAPACITY) { MessageBeep(0); return FALSE; }
    event = output + (output_head + output_count) % OUTPUT_CAPACITY;
    event->window = window; event->message = message;
    event->wparam = wp; event->lparam = lp;
    ++output_count;
    DrainOutput();
    return TRUE;
}

static void Redraw(void)
{
    if (!ime_window) return;
    FitApplication();
    if (ime_enabled) {
        ShowWindow(ime_window, SW_SHOWNOACTIVATE);
        SetWindowPos(ime_window, HWND_TOP, 0,
                     GetSystemMetrics(SM_CYSCREEN) - ImeHeight(),
                     GetSystemMetrics(SM_CXSCREEN), ImeHeight(), SWP_NOACTIVATE);
    } else
        ShowWindow(ime_window, SW_HIDE);
    InvalidateRect(ime_window, NULL, TRUE);
}

static void ClearKey(void)
{
    key_length = candidate_count = candidate_total = candidate_page = 0;
    key[0] = raw_key[0] = '\0';
    Redraw();
}

/* Some editors replace their focused child window when they enter text
 * editing.  Preserve an unfinished syllable across that transition if both
 * controls belong to the same Win16 task; crossing into another application
 * still cancels it, so a pending candidate cannot be committed there. */
static void SyncTargetFocus(void)
{
    HWND focus = InputFocus();
    HTASK old_task, new_task;
    char old_class[32], new_class[32];
    if (!key_length || !target_window || !focus || focus == target_window)
        return;
    old_task = IsWindow(target_window) ? GetWindowTask(target_window) : NULL;
    new_task = GetWindowTask(focus);
    GetClassName(target_window, old_class, sizeof(old_class));
    GetClassName(focus, new_class, sizeof(new_class));
    if (!old_task || !new_task || old_task != new_task ||
        !lstrcmpi(old_class, "EDIT") || !lstrcmpi(new_class, "EDIT") ||
        !lstrcmpi(old_class, "OpusFedt") || !lstrcmpi(new_class, "OpusFedt"))
        ClearKey();
    target_window = focus;
}

/* Reuse the installed CGA font bank, with no extra resident glyph cache.
 * Derive its name from the existing installer-patched bitmap path slot. */
static HFILE OpenGlyphFont(void)
{
    char path[80], *name;
    BYTE header[24];
    HFILE file;
    if (!CompactBar()) return _lopen(bitmap_path, OF_READ);
    lstrcpy(path, bitmap_path);
    name = strrchr(path, '\\');
    if (!name) return HFILE_ERROR;
    lstrcpy(name + 1, "CHCGA10.FNT");
    file = _lopen(path, OF_READ);
    if (file == HFILE_ERROR) return file;
    if (_lread(file, header, sizeof(header)) != sizeof(header) ||
        memcmp(header, "CH10", 4) || header[4] != 1 ||
        header[6] != 10 || WordAt(header + 10) != 20) {
        _lclose(file); return HFILE_ERROR;
    }
    return file;
}

static BOOL ReadGlyph(HFILE file, BYTE lead, BYTE trail, BYTE *data)
{
    BYTE offset[4];
    DWORD at;
    WORD bytes = 32;
    if (file == HFILE_ERROR) return FALSE;
    if (CompactBar()) {
        if (_llseek(file, 16L, 0) != 16L || _lread(file, offset, 4) != 4)
            return FALSE;
        at = DwordAt(offset) +
             ((DWORD)(lead - 0x81) * 157L + 63L + trail - 0xA1) * 20L;
        bytes = 20;
    } else {
        at = 0x920L + (275L + (DWORD)(lead - 0xA1) * 94L +
                        trail - 0xA1) * 32L;
    }
    return _llseek(file, at, 0) == (LONG)at &&
           _lread(file, data, bytes) == bytes;
}

static void LoadHeading(void)
{
    static const BYTE heading[] = {0xC6, 0xB4, 0xD2, 0xF4}; /* 拼音 */
    HFILE file = OpenGlyphFont();
    WORD i;
    if (file == HFILE_ERROR) return;
    for (i = 0; i < 2; ++i) {
        if (ReadGlyph(file, heading[i * 2], heading[i * 2 + 1], heading_bitmap[i]))
            heading_available[i] = TRUE;
    }
    _lclose(file);
}

static BOOL PaintGlyph(HDC dc, HDC memory, int x, int y, const BYTE *data)
{
    HBITMAP bitmap, old_bitmap;
    int height = CompactBar() ? 10 : 16;
    BOOL drawn = FALSE;
    if (!memory) return FALSE;
    bitmap = CreateBitmap(16, height, 1, 1, data);
    if (!bitmap) return FALSE;
    old_bitmap = SelectObject(memory, bitmap);
    if (old_bitmap) {
        /* CHCGA stores ink as one; CFSUNG stores background as one. */
        drawn = BitBlt(dc, x, y, 16, height, memory, 0, 0,
                       CompactBar() ? NOTSRCCOPY : SRCCOPY);
        SelectObject(memory, old_bitmap);
    }
    DeleteObject(bitmap);
    return drawn;
}

static HWND Destination(void)
{
    HWND focus = InputFocus();
    if (focus && focus != ime_window && IsWindow(focus))
        target_window = focus;
    if (target_window && IsWindow(target_window)) return target_window;
    return NULL;
}

static void SendCharacter(WORD character)
{
    HWND destination = Destination();
    if (destination) QueueMessage(destination, WM_CHAR, character, 1L);
}

static void Commit(WORD choice)
{
    WORD offset;
    HWND destination = Destination();
    if (!destination || choice >= candidate_count) return;
    DrainOutput();
    if (OUTPUT_CAPACITY - output_count < candidate_lengths[choice] * 2) {
        MessageBeep(0); return; /* Preserve composition if a receiver is stalled. */
    }
    /* Keep one native envelope per Hanzi and retry a full destination queue. */
    for (offset = 0; offset < candidate_lengths[choice]; offset += 2) {
#ifdef PINYIN_DIAGNOSTICS
        Diag(0x90, ((WORD)candidates[choice][offset] << 8) |
                   candidates[choice][offset + 1]);
#endif
        QueueMessage(destination, WM_KEYDOWN, 0x280, 0L);
        QueueMessage(destination, WM_CHAR, candidates[choice][offset], 1L);
        QueueMessage(destination, WM_CHAR, candidates[choice][offset + 1], 1L);
        QueueMessage(destination, WM_KEYUP, 0x280, 0L);
    }
    ClearKey();
}

static void FlushRaw(WORD tail)
{
    WORD i;
    for (i = 0; i < key_length; ++i) SendCharacter((BYTE)raw_key[i]);
    ClearKey();
    if (tail) SendCharacter(tail);
}

static BOOL ForwardVirtualKey(WPARAM key_code)
{
    if (key_code >= VK_F1 && key_code <= VK_F12) return TRUE;
    switch (key_code) {
    case VK_BACK: case VK_TAB: case VK_RETURN: case VK_ESCAPE:
    case VK_SHIFT: case VK_CONTROL: case VK_MENU:
    case VK_CAPITAL: case VK_NUMLOCK: case VK_SCROLL:
    case VK_PRIOR: case VK_NEXT: case VK_END: case VK_HOME:
    case VK_LEFT: case VK_UP: case VK_RIGHT: case VK_DOWN:
    case VK_INSERT: case VK_DELETE:
        return TRUE;
    }
    return FALSE;
}

BOOL FAR PASCAL PinyinDlgProc(HWND hwnd, UINT message,
                                       WPARAM wparam, LPARAM lparam)
{
    (void)hwnd; (void)message; (void)wparam; (void)lparam;
    return FALSE;
}

static LONG DispatchImeMessage(HWND hwnd, UINT message,
                               WPARAM wparam, LPARAM lparam)
{
    HWND destination;
    WORD i;
    BYTE c;
    PAINTSTRUCT ps;
    HDC dc, memory;
    HFONT font, old_font;
    char label[2], page_label[12];
    HFILE bitmap_file;
    WORD j;
    int width, step, x, separator, candidate_y, heading_y, text_y;
    RECT header;
    switch (message) {
    case WM_CREATE:
        ime_window = hwnd;
#ifdef PINYIN_DIAGNOSTICS
        Diag(5, hwnd);
#endif
        return 0L;
    case WM_TIMER:
        if (wparam == 3) { DrainOutput(); return 0L; }
#ifdef PINYIN_DIAGNOSTICS
        if ((wparam == 1 || wparam == 2) && diagnostic_hook) {
            KillTimer(hwnd, wparam);
            Diag(0x40, wparam);
            diagnostic_hook(0, VK_CONTROL, 0L);
            diagnostic_hook(0, VK_SPACE, 0L);
            diagnostic_hook(0, VK_CONTROL, 0x80000000L);
        }
#endif
        return 0L;
    case WM_IME_ENABLE:
        ime_enabled = wparam != 0;
        ctrl_down = alt_down = FALSE;
        shortcut_key = 0;
        ClearKey();
        return 0L;
    case WM_MOUSEACTIVATE:
        return MA_NOACTIVATE;
    case WM_LBUTTONDOWN:
        if (HIWORD(lparam) >= (CompactBar() ? 11 : 19) && candidate_count) {
            step = (GetSystemMetrics(SM_CXSCREEN) - 4) / page_size;
            i = LOWORD(lparam) / step;
            if (i < candidate_count) Commit(i);
        }
        return 0L;
    case WM_KEYDOWN:
    case WM_KEYUP:
#ifdef PINYIN_DIAGNOSTICS
        Diag(message == WM_KEYDOWN ? 0x81 : 0x82, wparam);
#endif
        SyncTargetFocus();
        if (wparam == VK_CONTROL) ctrl_down = message == WM_KEYDOWN;
        if (wparam == VK_MENU) alt_down = message == WM_KEYDOWN;
        if (message == WM_KEYUP && wparam == shortcut_key) {
            shortcut_key = 0;
            destination = Destination();
            if (destination) QueueMessage(destination, message, wparam, lparam);
            return 0L;
        }
        if (message == WM_KEYDOWN && wparam == VK_CONTROL && key_length)
            ClearKey();
        if (message == WM_KEYDOWN && wparam == VK_MENU && key_length)
            ClearKey();
        if (message == WM_KEYDOWN && (ctrl_down || alt_down) &&
            wparam >= 'A' && wparam <= 'Z') {
            shortcut_key = wparam;
            destination = Destination();
            if (destination) QueueMessage(destination, message, wparam, lparam);
            return 0L;
        }
        if (message == WM_KEYDOWN && key_length &&
            (wparam == VK_LEFT || wparam == VK_RIGHT ||
             wparam == VK_UP || wparam == VK_DOWN ||
             wparam == VK_HOME || wparam == VK_END ||
             wparam == VK_PRIOR || wparam == VK_NEXT ||
             wparam == VK_DELETE || wparam == VK_INSERT ||
             (wparam >= VK_F1 && wparam <= VK_F12))) {
            if (candidate_count) Commit(0);
            else FlushRaw(0);
        }
        /* Printable keys are delivered as WM_CHAR below. Forwarding their
         * WM_KEYDOWN as well would make the application's TranslateMessage
         * generate a second copy of the character. */
        if (key_length && (wparam == VK_BACK || wparam == VK_RETURN ||
                           wparam == VK_ESCAPE || wparam == VK_TAB))
            return 0L;
        if (!ForwardVirtualKey(wparam)) return 0L;
        destination = Destination();
        if (destination) QueueMessage(destination, message, wparam, lparam);
        return 0L;
    case WM_SYSKEYDOWN:
    case WM_SYSKEYUP:
    case WM_SYSCHAR:
        if (key_length) ClearKey();
        destination = Destination();
        if (destination) QueueMessage(destination, message, wparam, lparam);
        return 0L;
    case WM_CHAR:
        c = (BYTE)wparam;
        ime_enabled = TRUE;
#ifdef PINYIN_DIAGNOSTICS
        Diag(0x80, c);
#endif
        if (shortcut_key && (ctrl_down || alt_down)) return 0L;
        /* A composition belongs to the control where it began.  Discard it
         * after a mouse focus change instead of committing into another app. */
        SyncTargetFocus();
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c == 39 && key_length && key[key_length - 1] != 39)) {
            if (key_length == MAX_KEY) FlushRaw(0);
            raw_key[key_length] = c;
            key[key_length++] = c >= 'A' && c <= 'Z' ? c + 32 : c;
            key[key_length] = '\0';
            raw_key[key_length] = '\0';
            candidate_page = 0;
            LoadPage();
            Redraw();
            return 0L;
        }
        if (key_length && c == 8) {
            key[--key_length] = '\0';
            raw_key[key_length] = '\0';
            candidate_page = 0;
            LoadPage();
            Redraw();
            return 0L;
        }
        if (key_length && c == 27) {
            ClearKey();
            return 0L;
        }
        if (key_length && c >= '1' && c <= '9') {
            if (candidate_count && c - '1' < candidate_count)
                Commit(c - '1');
            else {
                FlushRaw(0);
                SendCharacter(c);
            }
            return 0L;
        }
        if (key_length && (c == ' ' || c == 13)) {
            if (candidate_count) Commit(0);
            else FlushRaw(c);
            return 0L;
        }
        if (key_length && c == 9) {
            if (candidate_count) Commit(0);
            else FlushRaw(0);
            destination = Destination();
            if (destination) {
                QueueMessage(destination, WM_KEYDOWN, VK_TAB, 1L);
                QueueMessage(destination, WM_KEYUP, VK_TAB, 1L);
            }
            return 0L;
        }
        if (key_length && c == '=' && candidate_count) {
            ++candidate_page;
            LoadPage();
            Redraw();
            return 0L;
        }
        if (key_length && c == '-' && candidate_count) {
            if (candidate_page) --candidate_page;
            else candidate_page = (candidate_total - 1) / page_size;
            LoadPage();
            Redraw();
            return 0L;
        }
        if (key_length) {
            if (candidate_count) Commit(0);
            else FlushRaw(0);
        }
        if (c == 8 || c == 9 || c == 13 || c == 27)
            return 0L;  /* The forwarded virtual key owns this action. */
        SendCharacter(c);
        return 0L;
    case WM_PAINT:
        dc = BeginPaint(hwnd, &ps);
        width = GetSystemMetrics(SM_CXSCREEN) - 2;
        header.left = 0; header.top = 0;
        header.right = width; header.bottom = ImeHeight();
        separator = CompactBar() ? 10 : 18;
        candidate_y = CompactBar() ? 11 : 20;
        heading_y = CompactBar() ? 0 : 1;
        text_y = CompactBar() ? 0 : 2;
        FillRect(dc, &header, GetStockObject(WHITE_BRUSH));
        MoveTo(dc, 0, separator); LineTo(dc, width, separator);
        font = CreateFont(CompactBar() ? 10 : 12, 8, 0, 0, FW_NORMAL, 0, 0, 0,
                          DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                          CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                          FIXED_PITCH | FF_MODERN, NULL);
        old_font = font ? SelectObject(dc, font) : NULL;
        /* Keep the tail of long full-pinyin composition visible. */
        j = key_length > 58 ? key_length - 58 : 0;
        TextOut(dc, 42, text_y, raw_key + j, key_length - j);
        if (candidate_total) {
            wsprintf(page_label, "%u/%u", candidate_page + 1,
                     (candidate_total - 1) / page_size + 1);
            TextOut(dc, width - 64, text_y, page_label, lstrlen(page_label));
        }
        memory = CreateCompatibleDC(dc);
        if (heading_available[0] && heading_available[1]) {
            PaintGlyph(dc, memory, 3, heading_y, heading_bitmap[0]);
            PaintGlyph(dc, memory, 19, heading_y, heading_bitmap[1]);
        } else TextOut(dc, 5, text_y, "PY", 2);
        step = (width - 2) / page_size;
        bitmap_file = OpenGlyphFont();
        for (i = 0; i < candidate_count; ++i) {
            x = 3 + i * step;
            if (!i) Rectangle(dc, x - 1, separator + 1,
                             x + 20 + candidate_lengths[i] * 8, ImeHeight() - 2);
            label[0] = '1' + i; label[1] = '.';
            TextOut(dc, x + 1, CompactBar() ? 11 : 21, label, 2);
            for (j = 0; j < candidate_lengths[i]; j += 2) {
                if (!ReadGlyph(bitmap_file, candidates[i][j], candidates[i][j+1], glyph) ||
                    !PaintGlyph(dc, memory, x + 19 + j * 8, candidate_y, glyph))
                    TextOut(dc, x + 19 + j * 8, candidate_y,
                            (LPSTR)candidates[i] + j, 2);
            }
        }
        if (bitmap_file != HFILE_ERROR) _lclose(bitmap_file);
        if (!key_length) TextOut(dc, 8, CompactBar() ? 11 : 21,
                                "Ctrl+Space   1-9   Space   -/=", 30);
        if (memory) DeleteDC(memory);
        if (font) { SelectObject(dc, old_font); DeleteObject(font); }
        EndPaint(hwnd, &ps);
        return 0L;
    case WM_DESTROY:
        RestoreApplication();
        PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(hwnd, message, wparam, lparam);
}

/* WINNLS may call back while an application is inside its own editor loop.
 * Copy events and focus now; perform disk I/O and GDI on our own message loop.
 * Serial dispatch also keeps a new composition from changing a pending commit. */
#define INPUT_CAPACITY 64
typedef struct {
    UINT message;
    WPARAM wparam;
    LPARAM lparam;
    HWND focus;
} INPUT_EVENT;
static INPUT_EVENT input[INPUT_CAPACITY];
static WORD input_head, input_count;
static BOOL input_busy, paint_busy, input_wake_pending;

static void WakeInput(HWND hwnd)
{
    if (!input_count || input_busy || paint_busy || input_wake_pending) return;
    if (PostMessage(hwnd, WM_IME_INPUT, 0, 0L)) input_wake_pending = TRUE;
    else SetTimer(hwnd, 4, 25, NULL);
}

static void EnqueueInput(HWND hwnd, UINT message, WPARAM wp, LPARAM lp)
{
    INPUT_EVENT *event;
    if (input_count == INPUT_CAPACITY) { MessageBeep(0); return; }
    event = input + (input_head + input_count) % INPUT_CAPACITY;
    event->message = message; event->wparam = wp; event->lparam = lp;
    event->focus = GetFocus();
    ++input_count;
    WakeInput(hwnd);
}

LONG FAR PASCAL IMEWNDPROC(HWND hwnd, UINT message,
                          WPARAM wparam, LPARAM lparam)
{
    WORD FAR *report;
    INPUT_EVENT event;
    LONG result;
    switch (message) {
    case WM_IME_REPORT:
        /* WINNLS owns/frees this IMESTRUCT after the synchronous callback. */
        report = (WORD FAR *)GlobalLock((HGLOBAL)lparam);
        if (report) {
            if (report[0] == 0x17)
                EnqueueInput(hwnd, WM_IME_ENABLE, report[1] != 0, 0L);
            GlobalUnlock((HGLOBAL)lparam);
        }
        return 0L;
    case WM_KEYDOWN: case WM_KEYUP: case WM_CHAR:
    case WM_SYSKEYDOWN: case WM_SYSKEYUP: case WM_SYSCHAR:
    case WM_LBUTTONDOWN:
        EnqueueInput(hwnd, message, wparam, lparam);
        return 0L;
    case WM_TIMER:
        if (wparam != 4) break;
        KillTimer(hwnd, 4);
        /* Fall through to the input wakeup if our queue was previously full. */
    case WM_IME_INPUT:
        input_wake_pending = FALSE;
        if (input_busy || paint_busy) return 0L;
        input_busy = TRUE;
        while (input_count) {
            event = input[input_head];
            input_head = (input_head + 1) % INPUT_CAPACITY;
            --input_count;
            input_focus = event.focus;
            DispatchImeMessage(hwnd, event.message, event.wparam, event.lparam);
        }
        input_focus = NULL;
        input_busy = FALSE;
        return 0L;
    case WM_PAINT:
        paint_busy = TRUE;
        result = DispatchImeMessage(hwnd, message, wparam, lparam);
        paint_busy = FALSE;
        WakeInput(hwnd);
        return result;
    }
    return DispatchImeMessage(hwnd, message, wparam, lparam);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    HINSTANCE nls;
    SET_IME_HANDLE register_ime;
    SET_KEYBOARD_HOOK set_hook;
    SET_SYSTEM_IME set_system;
    WNDCLASS wc;
    HWND hwnd;
    MSG msg;
    (void)command; (void)show;
#ifdef PINYIN_DIAGNOSTICS
    Diag(1, 0);
#endif
    if (!LoadIndex()) return 1;
    LoadHeading();
#ifdef PINYIN_DIAGNOSTICS
    Diag(2, 0);
#endif
    nls = LoadLibrary("WINNLS.DLL");
#ifdef PINYIN_DIAGNOSTICS
    Diag(3, nls);
#endif
    if ((UINT)nls < 32) return 2;
    register_ime = (SET_IME_HANDLE)GetProcAddress(nls, MAKEINTRESOURCE(11));
    set_hook = (SET_KEYBOARD_HOOK)GetProcAddress(nls, MAKEINTRESOURCE(10));
    set_system = (SET_SYSTEM_IME)GetProcAddress(nls, MAKEINTRESOURCE(17));
#ifdef PINYIN_DIAGNOSTICS
    diagnostic_hook = (KEYBOARD_HOOK)GetProcAddress(nls,
                                                   MAKEINTRESOURCE(2));
#endif
    if (!register_ime || !set_hook || !set_system) return 3;
#ifdef PINYIN_DIAGNOSTICS
    Diag(4, 0);
#endif
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)IMEWNDPROC;
        wc.cbClsExtra = 0;
        wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "GBPY_NATIVE";
        if (!RegisterClass(&wc)) return 4;
    }
    hwnd = CreateWindow("GBPY_NATIVE", "Pinyin", WS_POPUP | WS_BORDER,
                        0, GetSystemMetrics(SM_CYSCREEN) - ImeHeight(),
                        GetSystemMetrics(SM_CXSCREEN), ImeHeight(), GetDesktopWindow(), NULL,
                        instance, NULL);
    if (!hwnd) return 5;
    ime_window = hwnd;
    if (!register_ime("phon.ime", hwnd)) return 6;
#ifdef PINYIN_DIAGNOSTICS
    Diag(6, hwnd);
#endif
    set_system(hwnd);
#ifdef PINYIN_DIAGNOSTICS
    Diag(7, hwnd);
#endif
    set_hook(TRUE);
#ifdef PINYIN_DIAGNOSTICS
    Diag(8, hwnd);
#endif
    ShowWindow(hwnd, SW_HIDE);
#ifdef PINYIN_DIAGNOSTICS
    if (diagnostic_hook) {
        SetTimer(hwnd, 1, 7000, NULL);
        SetTimer(hwnd, 2, 16000, NULL);
    }
#endif
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
