#include <windows.h>
#include <string.h>

/* Native Win16 system IME replacement for the original phon.ime slot.
   The on-disk PYI1 index is generated from the local Unihan archive. */

#define INDEX_COUNT 409
#define INDEX_BYTES 14
#define MAX_KEY 7
#define PAGE_SIZE 9
#define MAX_CANDIDATES 512
#define WM_FINISH_COMPOSITION (WM_USER + 1)
#define WM_TOGGLE_IME (WM_USER + 2)
#define RESTORE_TIMER 2
#define HOTKEY_TIMER 3

/* INSTALL.BAT rewrites both 80-byte slots in its copied PHON.IME. */
static char dictionary_path[80] = "C:\\WINDOWS\\GBPY.DAT";
static char bitmap_path[80] = "C:\\WINDOWS\\SYSTEM\\CFSUNG16.B5Q";
static BYTE index_table[INDEX_COUNT * INDEX_BYTES];
static char key[MAX_KEY + 1];
static WORD key_length;
static WORD candidate_count;
static WORD candidate_page;
static BYTE candidates[PAGE_SIZE * 2];
static BYTE candidate_bitmap[PAGE_SIZE][32];
static BOOL bitmap_available[PAGE_SIZE];
static HWND target_window;
static HTASK target_task;
static BOOL target_is_write;
static HWND ime_window;
static HOOKPROC previous_message_hook;
static HOOKPROC message_hook_instance;
static HOOKPROC previous_keyboard_hook;
static HOOKPROC keyboard_hook_instance;
static BOOL ime_active;
static BOOL control_down;
static BOOL space_down;
static BOOL forwarding_literal;
static BOOL suppress_space;
static BOOL hotkey_held;
#define TARGET_SLOTS 32
#define CLIP_SLOTS 16
static HWND hooked_windows[TARGET_SLOTS];
static WNDPROC original_procs[TARGET_SLOTS];
static WNDPROC target_proc_instance;
static UINT clip_formats[CLIP_SLOTS];
static HGLOBAL clip_copies[CLIP_SLOTS];
static WORD clip_count;
static BOOL clip_restore_pending;
static BOOL clip_restore_cleared;
typedef WORD (FAR PASCAL *GBHOOK_START)(void);
typedef void (FAR PASCAL *GBHOOK_STOP)(void);
typedef void (FAR PASCAL *GBHOOK_TARGET)(HTASK, WORD, WORD);
typedef WORD (FAR PASCAL *GBHOOK_NEXT)(void);
static HINSTANCE hook_library;
static GBHOOK_STOP gb_hook_stop;
static GBHOOK_TARGET gb_hook_target;
static GBHOOK_NEXT gb_hook_next;
#define PENDING_KEY_COUNT 32
static BYTE pending_keys[PENDING_KEY_COUNT];
static WORD pending_read;
static WORD pending_write;

#ifdef PINYIN_DIAGNOSTICS
static HOOKPROC previous_call_hook;
static HOOKPROC call_hook_instance;
typedef struct {
    LPARAM parameter;
    WPARAM source;
    UINT message;
    HWND window;
} CALL_RECORD;

LONG __export FAR PASCAL PinyinCallHook(int code, WPARAM source,
                                        LPARAM parameter)
{
    CALL_RECORD FAR *record = (CALL_RECORD FAR *)parameter;
    LPCSTR value = NULL;
    HFILE file;
    BYTE buffer[8];
    WORD i;
    (void)source;
    if (code == HC_ACTION && record &&
        (record->message == WM_SETTEXT || record->message == WM_CREATE)) {
        if (record->message == WM_SETTEXT)
            value = (LPCSTR)record->parameter;
        else if (record->parameter)
            value = ((CREATESTRUCT FAR *)record->parameter)->lpszName;
        if (value) {
            file = _lopen("C:\\PYCALL.BIN", OF_WRITE);
            if (file == HFILE_ERROR) file = _lcreat("C:\\PYCALL.BIN", 0);
            if (file != HFILE_ERROR) {
                _llseek(file, 0L, 2);
                buffer[0] = (BYTE)record->window;
                buffer[1] = (BYTE)(record->window >> 8);
                buffer[2] = (BYTE)record->message;
                buffer[3] = (BYTE)(record->message >> 8);
                for (i = 0; i < 120 && value[i]; ++i)
                    _lwrite(file, value + i, 1);
                buffer[4] = 0;
                _lwrite(file, buffer + 4, 1);
                _lclose(file);
            }
        }
    }
    return DefHookProc(code, source, parameter, &previous_call_hook);
}

static void Trace(char *message)
{
    HFILE file = _lcreat("C:\\PYLOAD.LOG", 0);
    if (file != HFILE_ERROR) {
        _lwrite(file, message, lstrlen(message));
        _lclose(file);
    }
}

static void TraceKey(WORD value)
{
    HFILE file = _lopen("C:\\PYKEY.LOG", OF_WRITE);
    BYTE c = (BYTE)value;
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYKEY.LOG", 0);
    if (file != HFILE_ERROR) {
        _llseek(file, 0L, 2);
        _lwrite(file, &c, 1);
        _lclose(file);
    }
}
static void TraceHook(int code, WPARAM source, MSG FAR *message)
{
    static WORD recorded;
    HFILE file;
    static WORD data[4];
    if (!message || recorded >= 48 ||
        (message->message != WM_CHAR && message->message != WM_KEYDOWN)) return;
    file = _lopen("C:\\PYHOOK.BIN", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYHOOK.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    data[0] = (WORD)code;
    data[1] = source;
    data[2] = message->message;
    data[3] = message->wParam;
    _lwrite(file, (LPSTR)data, sizeof(data));
    _lclose(file);
    ++recorded;
}
static void TraceKeyboard(int code, WPARAM source, LPARAM state)
{
    static WORD recorded;
    static WORD data[8];
    HFILE file;
    if (recorded >= 80) return;
    file = _lopen("C:\\PYBOARD.BIN", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYBOARD.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    data[0] = (WORD)code;
    data[1] = source;
    data[2] = LOWORD(state);
    data[3] = HIWORD(state);
    data[4] = GetCurrentTask();
    data[5] = target_window ? GetWindowTask(target_window) : 0;
    data[6] = target_window;
    data[7] = ime_active;
    _lwrite(file, (LPSTR)data, sizeof(data));
    _lclose(file);
    ++recorded;
}
static void TraceRoute(HWND focus)
{
    static WORD data[5];
    HFILE file = _lopen("C:\\PYROUTE.BIN", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYROUTE.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    data[0] = focus;
    data[1] = target_window;
    data[2] = GetCurrentTask();
    data[3] = target_window ? GetWindowTask(target_window) : 0;
    data[4] = ime_active;
    _lwrite(file, (LPSTR)data, sizeof(data));
    _lclose(file);
}
static void TraceState(WORD stage, HWND hwnd, UINT message)
{
    static WORD recorded;
    static WORD data[8];
    HFILE file;
    LONG current;
    if (recorded >= 80 || message != WM_CHAR) return;
    file = _lopen("C:\\PYSTATE.BIN", OF_WRITE);
    if (file == HFILE_ERROR) file = _lcreat("C:\\PYSTATE.BIN", 0);
    if (file == HFILE_ERROR) return;
    _llseek(file, 0L, 2);
    current = GetWindowLong(hwnd, GWL_WNDPROC);
    data[0] = stage;
    data[1] = hwnd;
    data[2] = LOWORD(current);
    data[3] = HIWORD(current);
    data[4] = LOWORD((LONG)target_proc_instance);
    data[5] = HIWORD((LONG)target_proc_instance);
    data[6] = ime_active;
    data[7] = key_length;
    _lwrite(file, (LPSTR)data, sizeof(data));
    _lclose(file);
    ++recorded;
}
#else
#define Trace(message) ((void)0)
#define TraceKey(value) ((void)0)
#define TraceHook(code, source, message) ((void)0)
#define TraceKeyboard(code, source, state) ((void)0)
#define TraceRoute(focus) ((void)0)
#define TraceState(stage, hwnd, message) ((void)0)
#endif

static WORD WordAt(BYTE *p)
{
    return (WORD)p[0] | ((WORD)p[1] << 8);
}

static DWORD DwordAt(BYTE *p)
{
    return (DWORD)WordAt(p) | ((DWORD)WordAt(p + 2) << 16);
}

static BOOL LoadIndex(void)
{
    HFILE dictionary;
    BYTE header[6];
    LONG file_length;
    DWORD next_offset;
    WORD i, j, count;
    BYTE *entry;
    BOOL ended;
    dictionary = _lopen(dictionary_path, OF_READ);
    if (dictionary == HFILE_ERROR) return FALSE;
    if (_lread(dictionary, header, sizeof(header)) != sizeof(header) ||
        header[0] != 'P' || header[1] != 'Y' || header[2] != 'I' ||
        header[3] != '1' || WordAt(header + 4) != INDEX_COUNT ||
        _lread(dictionary, index_table, sizeof(index_table)) !=
        sizeof(index_table)) {
        goto invalid_index;
    }
    file_length = _llseek(dictionary, 0L, 2);
    if (file_length < 6L + sizeof(index_table) || file_length > 65535L)
        goto invalid_index;
    next_offset = 6L + sizeof(index_table);
    for (i = 0; i < INDEX_COUNT; ++i) {
        entry = index_table + i * INDEX_BYTES;
        ended = FALSE;
        for (j = 0; j < 8; ++j) {
            if (entry[j] == 0) ended = TRUE;
            else if (ended || entry[j] < 'a' || entry[j] > 'z')
                goto invalid_index;
        }
        if (!ended || entry[0] == 0 ||
            DwordAt(entry + 8) != next_offset)
            goto invalid_index;
        count = WordAt(entry + 12);
        if (!count || count > MAX_CANDIDATES) goto invalid_index;
        next_offset += (DWORD)count * 2L;
        if (next_offset > (DWORD)file_length) goto invalid_index;
    }
    if (next_offset != (DWORD)file_length) goto invalid_index;
    _lclose(dictionary);
    return TRUE;
invalid_index:
    _lclose(dictionary);
    return FALSE;
}

static void ClearKey(void)
{
    key_length = candidate_count = candidate_page = 0;
    key[0] = '\0';
    InvalidateRect(ime_window, NULL, TRUE);
}

static void LoadPage(void)
{
    HFILE dictionary, bitmap_file;
    WORD i, offset, available, ordinal, image;
    BYTE lead, trail;
    BYTE *entry = NULL;
    candidate_count = 0;
    for (i = 0; i < PAGE_SIZE; ++i) bitmap_available[i] = FALSE;
    if (!key_length) return;
    for (i = 0; i < INDEX_COUNT; ++i) {
        BYTE *candidate = index_table + i * INDEX_BYTES;
        if (lstrcmp(key, (LPCSTR)candidate) == 0) {
            entry = candidate;
            break;
        }
    }
    if (!entry) return;
    available = WordAt(entry + 12);
    offset = candidate_page * PAGE_SIZE;
    if (offset >= available) {
        candidate_page = 0;
        offset = 0;
    }
    candidate_count = available - offset;
    if (candidate_count > PAGE_SIZE) candidate_count = PAGE_SIZE;
    /* Win16 HFILE values are task-relative. The IME can remain loaded while
       focus moves to another task, so a saved handle can identify an EXE or
       temporary file by the time the next composition starts. */
    dictionary = _lopen(dictionary_path, OF_READ);
    if (dictionary == HFILE_ERROR) {
        candidate_count = 0;
        return;
    }
    if (_llseek(dictionary, DwordAt(entry + 8) + (DWORD)offset * 2L, 0) < 0L ||
        _lread(dictionary, candidates, candidate_count * 2) !=
        candidate_count * 2) candidate_count = 0;
    _lclose(dictionary);
    for (i = 0; i < candidate_count; ++i)
        if (candidates[i * 2] < 0xA1 || candidates[i * 2] > 0xF7 ||
            candidates[i * 2 + 1] < 0xA1 ||
            candidates[i * 2 + 1] > 0xFE) {
            candidate_count = 0;
            return;
        }
    bitmap_file = _lopen(bitmap_path, OF_READ);
    if (bitmap_file == HFILE_ERROR) return;
    for (i = 0; i < candidate_count; ++i) {
        lead = candidates[i * 2];
        trail = candidates[i * 2 + 1];
        if (lead < 0xA1 || lead > 0xF7 || trail < 0xA1 || trail > 0xFE)
            continue;
        ordinal = (WORD)(lead - 0xA1) * 94 + (WORD)(trail - 0xA1);
        image = 275 + ordinal;
        if (_llseek(bitmap_file, 0x920L + (LONG)image * 32L, 0) >= 0L &&
            _lread(bitmap_file, candidate_bitmap[i], 32) == 32) {
            bitmap_available[i] = TRUE;
        }
    }
    _lclose(bitmap_file);
}

static BOOL IsEdit(HWND hwnd)
{
    char class_name[24];
    if (!hwnd || !IsWindow(hwnd)) return FALSE;
    GetClassName(hwnd, class_name, sizeof(class_name));
    return lstrcmpi(class_name, "Edit") == 0;
}

static BOOL IsWriteDocument(HWND hwnd)
{
    char class_name[24];
    if (!hwnd || !IsWindow(hwnd)) return FALSE;
    GetClassName(hwnd, class_name, sizeof(class_name));
    return lstrcmpi(class_name, "MSWRITE_DOC") == 0;
}

static void FreeClipboardCopies(void)
{
    WORD i;
    for (i = 0; i < clip_count; ++i) {
        if (clip_copies[i]) GlobalFree(clip_copies[i]);
        clip_copies[i] = NULL;
    }
    clip_count = 0;
}

static BOOL RestoreClipboard(void)
{
    WORD i;
    BOOL complete = TRUE;
    if (!OpenClipboard(ime_window)) return FALSE;
    if (!clip_restore_cleared) {
        if (!EmptyClipboard()) { CloseClipboard(); return FALSE; }
        clip_restore_cleared = TRUE;
    }
    for (i = 0; i < clip_count; ++i) {
        if (clip_copies[i]) {
            if (SetClipboardData(clip_formats[i], clip_copies[i]))
                clip_copies[i] = NULL;
            else complete = FALSE;
        }
    }
    CloseClipboard();
    if (complete) {
        FreeClipboardCopies();
        clip_restore_pending = FALSE;
        clip_restore_cleared = FALSE;
        KillTimer(ime_window, RESTORE_TIMER);
    }
    return complete;
}

/* Write's document loop does not dispatch synthetic WM_CHAR to its window
   procedure. Its Paste command accepts GB2312 CF_TEXT. Preserve small text
   clipboard formats; leave other clipboard contents untouched on failure. */
static BOOL PasteWriteDBCS(HWND destination, char *text)
{
    HWND top = destination;
    UINT format = 0;
    HGLOBAL source, copy, candidate;
    LPSTR from, to;
    DWORD size;
    WORD i, byte_index;
    BOOL success = FALSE;
    char class_name[24];
    while (GetParent(top)) top = GetParent(top);
    GetClassName(top, class_name, sizeof(class_name));
    if (lstrcmpi(class_name, "MSWRITE_MENU") != 0) return FALSE;
    if (clip_restore_pending && !RestoreClipboard()) return FALSE;
    clip_count = 0;
    clip_restore_cleared = FALSE;
    if (!OpenClipboard(ime_window)) return FALSE;
    while ((format = EnumClipboardFormats(format)) != 0) {
        if (clip_count == CLIP_SLOTS ||
            (format != CF_TEXT && format != CF_OEMTEXT &&
             format != CF_DSPTEXT)) goto snapshot_fail;
        source = GetClipboardData(format);
        if (!source) goto snapshot_fail;
        size = GlobalSize(source);
        if (!size || size > 4096UL) goto snapshot_fail;
        copy = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, size);
        if (!copy) goto snapshot_fail;
        from = GlobalLock(source);
        to = GlobalLock(copy);
        if (!from || !to) {
            if (to) GlobalUnlock(copy);
            if (from) GlobalUnlock(source);
            GlobalFree(copy);
            goto snapshot_fail;
        }
        for (byte_index = 0; byte_index < (WORD)size; ++byte_index)
            to[byte_index] = from[byte_index];
        GlobalUnlock(copy);
        GlobalUnlock(source);
        clip_formats[clip_count] = format;
        clip_copies[clip_count++] = copy;
    }
    CloseClipboard();
    candidate = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, 3);
    if (!candidate) goto finish;
    to = GlobalLock(candidate);
    if (!to) { GlobalFree(candidate); goto finish; }
    to[0] = text[0]; to[1] = text[1]; to[2] = '\0';
    GlobalUnlock(candidate);
    if (!OpenClipboard(ime_window)) { GlobalFree(candidate); goto finish; }
    if (!EmptyClipboard()) {
        CloseClipboard();
        GlobalFree(candidate);
        goto finish;
    }
    clip_restore_cleared = TRUE;
    if (!SetClipboardData(CF_TEXT, candidate)) {
        BOOL restored = TRUE;
        GlobalFree(candidate);
        for (i = 0; i < clip_count; ++i)
            if (SetClipboardData(clip_formats[i], clip_copies[i]))
                clip_copies[i] = NULL;
            else restored = FALSE;
        CloseClipboard();
        if (!restored) {
            clip_restore_pending = TRUE;
            SetTimer(ime_window, RESTORE_TIMER, 250, NULL);
        }
        goto finish;
    }
    CloseClipboard();
    SendMessage(top, WM_COMMAND, 4115, 0L);
    success = TRUE;
    clip_restore_pending = TRUE;
    clip_restore_cleared = FALSE;
    if (!RestoreClipboard()) SetTimer(ime_window, RESTORE_TIMER, 250, NULL);
    goto finish;
snapshot_fail:
    CloseClipboard();
finish:
    if (!clip_restore_pending) FreeClipboardCopies();
    return success;
}

static void Commit(WORD choice)
{
    char text[3];
    HWND destination = target_window;
    if (choice >= candidate_count) return;
    TraceKey(0xFE);
    text[0] = (char)candidates[choice * 2];
    text[1] = (char)candidates[choice * 2 + 1];
    text[2] = '\0';
    if (!destination || !IsWindow(destination)) destination = GetFocus();
    if (IsEdit(destination))
        SendMessage(destination, EM_REPLACESEL, 0, (LONG)(LPSTR)text);
    else if (IsWriteDocument(destination)) {
        if (!PasteWriteDBCS(destination, text)) {
            MessageBeep(0);
            return;
        }
    } else if (destination && destination != ime_window) {
        PostMessage(destination, WM_CHAR, (BYTE)text[0], 1L);
        PostMessage(destination, WM_CHAR, (BYTE)text[1], 1L);
    }
    ClearKey();
}

static void FlushRaw(WORD tail)
{
    char raw[MAX_KEY + 2];
    WORD i, length = key_length;
    HWND destination = target_window;
    if (!destination || !IsWindow(destination)) destination = GetFocus();
    for (i = 0; i < length; ++i) raw[i] = key[i];
    if (tail == ' ') raw[length++] = ' ';
    raw[length] = '\0';
    if (IsEdit(destination))
        SendMessage(destination, EM_REPLACESEL, 0, (LONG)(LPSTR)raw);
    else if (destination && destination != ime_window) {
        forwarding_literal = TRUE;
        for (i = 0; i < length; ++i)
            SendMessage(destination, WM_CHAR, (BYTE)raw[i], 1L);
        forwarding_literal = FALSE;
    }
    if (tail == 13 && destination && destination != ime_window) {
        forwarding_literal = TRUE;
        SendMessage(destination, WM_CHAR, 13, 1L);
        forwarding_literal = FALSE;
    }
    ClearKey();
}

static void SendLiteral(WORD value)
{
    HWND destination = target_window;
    if (!destination || !IsWindow(destination)) destination = GetFocus();
    if (destination && destination != ime_window) {
        forwarding_literal = TRUE;
        SendMessage(destination, WM_CHAR, value, 1L);
        forwarding_literal = FALSE;
    }
}

LONG __export FAR PASCAL PinyinTargetProc(HWND hwnd, UINT message,
                                         WPARAM wparam, LPARAM lparam)
{
    WORD slot;
    WNDPROC original = NULL;
    WORD character;
    TraceState(2, hwnd, message);
    for (slot = 0; slot < TARGET_SLOTS; ++slot)
        if (hooked_windows[slot] == hwnd) {
            original = original_procs[slot];
            break;
        }
    if (!original) return DefWindowProc(hwnd, message, wparam, lparam);
    if (message == WM_NCDESTROY) {
        LONG result = CallWindowProc((FARPROC)original, hwnd, message, wparam, lparam);
        hooked_windows[slot] = NULL;
        original_procs[slot] = NULL;
        if (target_window == hwnd) { target_window = NULL; ClearKey(); }
        return result;
    }
    if (message == WM_KEYDOWN || message == WM_KEYUP) {
        if (wparam == VK_CONTROL) {
            control_down = message == WM_KEYDOWN;
        }
        if (message == WM_KEYUP && wparam == VK_SPACE)
            space_down = FALSE;
        if (message == WM_KEYDOWN && wparam == VK_SPACE &&
                (control_down || (GetKeyState(VK_CONTROL) & 0x8000))) {
            if (!space_down) {
                space_down = TRUE;
                suppress_space = TRUE;
                PostMessage(ime_window, WM_TOGGLE_IME, 0, (LPARAM)hwnd);
            }
            return 0L;
        }
    } else if (message == WM_CHAR) {
        if (suppress_space) {
            suppress_space = FALSE;
            if (wparam == ' ') return 0L;
        }
        if (ime_active && !forwarding_literal) {
            character = wparam;
            if (key_length && target_window != hwnd) ClearKey();
            target_window = hwnd;
            if (key_length &&
                ((character >= 'a' && character <= 'z') ||
                 (character >= 'A' && character <= 'Z')) &&
                key_length == MAX_KEY) {
                SendMessage(ime_window, WM_FINISH_COMPOSITION, 0, 0L);
                return CallWindowProc((FARPROC)original, hwnd, message, wparam, lparam);
            }
            if (key_length && character >= '1' && character <= '9' &&
                !candidate_count) {
                SendMessage(ime_window, WM_FINISH_COMPOSITION, 0, 0L);
                return CallWindowProc((FARPROC)original, hwnd, message, wparam, lparam);
            }
            if (key_length && character != 8 && character != 27 &&
                character != 13 && character != ' ' &&
                character != '-' && character != '=' &&
                !(character >= '1' && character <= '9') &&
                !(character >= 'a' && character <= 'z') &&
                !(character >= 'A' && character <= 'Z')) {
                SendMessage(ime_window, WM_FINISH_COMPOSITION, 1, 0L);
                return CallWindowProc((FARPROC)original, hwnd, message, wparam, lparam);
            }
            if (((character >= 'a' && character <= 'z') ||
                 (character >= 'A' && character <= 'Z')) ||
                (key_length && (character == 8 || character == 27 ||
                 character == 13 || character == ' ' ||
                 character == '-' || character == '=' ||
                 (character >= '1' && character <= '9')))) {
                target_window = hwnd;
                SendMessage(ime_window, WM_CHAR, character, lparam);
                return 0L;
            }
        }
    }
    return CallWindowProc((FARPROC)original, hwnd, message, wparam, lparam);
}

static void HookTarget(HWND hwnd)
{
    WORD slot;
    LONG old_proc;
    if (!target_proc_instance || !hwnd || hwnd == ime_window ||
        !IsWindow(hwnd)) return;
    for (slot = 0; slot < TARGET_SLOTS; ++slot)
        if (hooked_windows[slot] == hwnd) return;
    for (slot = 0; slot < TARGET_SLOTS; ++slot)
        if (!hooked_windows[slot]) break;
    if (slot == TARGET_SLOTS) return;
    old_proc = SetWindowLong(hwnd, GWL_WNDPROC, (LONG)target_proc_instance);
    if (!old_proc) return;
    original_procs[slot] = (WNDPROC)old_proc;
    hooked_windows[slot] = hwnd;
}

LONG __export FAR PASCAL PinyinMessageHook(int code, WPARAM wparam,
                                           LPARAM lparam)
{
    MSG FAR *message = (MSG FAR *)lparam;
    HWND focus;
    TraceHook(code, wparam, message);
    if (message) TraceState(1, message->hwnd, message->message);
    /* Some physical-key paths enter a Win16 task queue with a null HWND.
       A synthetic PostMessage-to-EDIT probe does not exercise this case.
       DispatchMessage cannot route those characters to the EDIT control,
       so deliver them to our composition window while Chinese is active. */
    if (code == HC_ACTION && message &&
        message->message == WM_CHAR && !message->hwnd) {
        focus = GetFocus();
        TraceRoute(focus);
        if (target_window && IsWindow(target_window) &&
            GetWindowTask(target_window) == GetCurrentTask()) {
            if (ime_active && !target_is_write) {
                PostMessage(ime_window, WM_CHAR, message->wParam,
                            message->lParam);
                message->message = WM_NULL;
            } else if (!ime_active) message->hwnd = focus;
        }
    }
    if (code == HC_ACTION && message &&
        message->message == WM_KEYUP &&
        (message->wParam == VK_SPACE || message->wParam == VK_CONTROL))
        space_down = FALSE;
    /* Installing the subclass is idempotent. Composition happens only when
       DispatchMessage reaches the target, never during PM_NOREMOVE peeks. */
    if (code == HC_ACTION && message &&
        message->hwnd != ime_window && IsWindow(message->hwnd) &&
        !IsWriteDocument(message->hwnd) &&
        ((message->message == WM_KEYDOWN &&
          (message->wParam == VK_CONTROL || message->wParam == VK_SPACE)) ||
         (message->message == WM_KEYUP && message->wParam == VK_CONTROL) ||
         (ime_active && message->message == WM_CHAR)))
        HookTarget(message->hwnd);
    return DefHookProc(code, wparam, lparam, &previous_message_hook);
}

/* Write consumes physical keys through its own document loop, so its posted
   WM_CHAR events bypass the window subclass used by standard EDIT controls.
   Intercept the hardware key before that loop converts it to a character. */
LONG __export FAR PASCAL PinyinKeyboardHook(int code, WPARAM wparam,
                                             LPARAM lparam)
{
    WORD character;
    TraceKeyboard(code, wparam, lparam);
    if (code != HC_ACTION)
        return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
    if ((DWORD)lparam & 0x80000000UL) {
        if (wparam == VK_CONTROL) control_down = FALSE;
        if (wparam == VK_SPACE) space_down = FALSE;
        return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
    }
    /* The timer owns Ctrl+Space.  Passing its physical key events through
       keeps Write's keyboard state balanced while the IME changes mode. */
    if (wparam == VK_CONTROL || (wparam == VK_SPACE && !key_length))
        return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
    /* Hotkeys such as Alt+F4 can destroy the foreground task.  Avoid USER
       focus/class queries in this global hook for keys we never compose. */
    if (wparam != VK_CONTROL && wparam != VK_SPACE &&
        wparam != VK_RETURN && wparam != VK_BACK &&
        wparam != VK_ESCAPE &&
        (wparam < 'A' || wparam > 'Z') &&
        (wparam < '1' || wparam > '9'))
        return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
    if (!ime_active || !target_is_write ||
        target_task != GetCurrentTask())
        return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
    character = wparam;
    if (character >= 'A' && character <= 'Z')
        character += 'a' - 'A';
    if ((character >= 'a' && character <= 'z') ||
        (key_length && (character == VK_SPACE || character == VK_RETURN ||
                        character == VK_BACK || character == VK_ESCAPE ||
                        (character >= '1' && character <= '9')))) {
        WORD next;
        if (character == VK_SPACE) character = ' ';
        else if (character == VK_RETURN) character = 13;
        else if (character == VK_BACK) character = 8;
        else if (character == VK_ESCAPE) character = 27;
        /* Cross-task PostMessage from WH_KEYBOARD can re-enter USER while
           Write is dispatching a key.  Drain this bounded queue in our own
           timer callback after the hook has returned. */
        next = (pending_write + 1) % PENDING_KEY_COUNT;
        if (next == pending_read)
            return DefHookProc(code, wparam, lparam,
                               &previous_keyboard_hook);
        pending_keys[pending_write] = (BYTE)character;
        pending_write = next;
        return DefHookProc(code, wparam, lparam,
                           &previous_keyboard_hook);
    }
    return DefHookProc(code, wparam, lparam, &previous_keyboard_hook);
}

BOOL __export FAR PASCAL PinyinDlgProc(HWND hwnd, UINT message,
                                       WPARAM wparam, LPARAM lparam)
{
    (void)hwnd; (void)message; (void)wparam; (void)lparam;
    return FALSE;
}

LONG __export FAR PASCAL IMEWNDPROC(HWND hwnd, UINT message,
                                     WPARAM wparam, LPARAM lparam)
{
    PAINTSTRUCT ps;
    HDC dc, memory;
    HFONT font, old_font;
    HBITMAP bitmap, old_bitmap;
    char display[96];
    char label[3], symbol[2];
    WORD i;
    BOOL drawn;
    HWND focused;
    (void)lparam;
    switch (message) {
    case WM_CREATE:
        ime_window = hwnd;
        return 0L;
    case WM_TIMER:
        if (wparam == RESTORE_TIMER && clip_restore_pending)
            RestoreClipboard();
        if (wparam == HOTKEY_TIMER) {
            WORD drained = 0;
            BOOL down;
            WORD hooked_key;
            if (target_window && !IsWindow(target_window)) {
                target_window = NULL;
                target_task = 0;
                target_is_write = FALSE;
                ClearKey();
            }
            down = (GetAsyncKeyState(VK_CONTROL) & 0x8000) &&
                   (GetAsyncKeyState(VK_SPACE) & 0x8000);
            if (down && !hotkey_held) {
                focused = GetFocus();
                if (focused && focused != hwnd) {
                    Trace("HOTKEY");
                    PostMessage(hwnd, WM_TOGGLE_IME, 0, (LPARAM)focused);
                } else Trace("NOFOCUS");
            }
            hotkey_held = down;
            if (gb_hook_target)
                gb_hook_target(target_task,
                               ime_active && target_is_write,
                               key_length != 0);
            if (gb_hook_next)
                while ((hooked_key = gb_hook_next()) != 0)
                    PostMessage(hwnd, WM_CHAR, hooked_key, 1L);
            while (pending_read != pending_write && drained++ < 8) {
                BYTE character = pending_keys[pending_read];
                pending_read = (pending_read + 1) % PENDING_KEY_COUNT;
                PostMessage(hwnd, WM_CHAR, character, 1L);
            }
        }
        return 0L;
    case WM_FINISH_COMPOSITION:
        if (key_length) {
            if (wparam && candidate_count) Commit(0);
            else FlushRaw(0);
        }
        return 0L;
    case WM_TOGGLE_IME:
        Trace("TOGGLE");
        focused = (HWND)lparam;
        if (!focused || !IsWindow(focused)) return 0L;
        ime_active = !ime_active;
        target_window = focused;
        target_task = GetWindowTask(focused);
        target_is_write = IsWriteDocument(focused);
        if (!ime_active) ClearKey();
        ShowWindow(hwnd, ime_active ? SW_SHOWNOACTIVATE : SW_HIDE);
        if (ime_active)
            SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0,
                         SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        return 0L;
    case WM_CHAR:
        TraceKey(wparam);
        focused = GetFocus();
        if (!target_is_write && focused && focused != hwnd) {
            target_window = focused;
            target_task = GetWindowTask(focused);
            target_is_write = IsWriteDocument(focused);
        }
        if ((wparam >= 'a' && wparam <= 'z') ||
            (wparam >= 'A' && wparam <= 'Z')) {
            if (key_length < MAX_KEY) {
                key[key_length++] = (char)(wparam >= 'A' && wparam <= 'Z'
                                           ? wparam + 32 : wparam);
                key[key_length] = '\0';
                candidate_page = 0;
                LoadPage();
                InvalidateRect(hwnd, NULL, TRUE);
            } else {
                FlushRaw(0);
                SendLiteral(wparam);
            }
            return 0L;
        }
        if (wparam == 8 && key_length) {
            key[--key_length] = '\0';
            candidate_page = 0;
            LoadPage();
            InvalidateRect(hwnd, NULL, TRUE);
            return 0L;
        }
        if (wparam == 27) {
            ClearKey();
            return 0L;
        }
        if (key_length && wparam >= '1' && wparam <= '9') {
            if (candidate_count) Commit((WORD)(wparam - '1'));
            else {
                FlushRaw(0);
                SendLiteral(wparam);
            }
            return 0L;
        }
        if (key_length && (wparam == ' ' || wparam == 13)) {
            if (candidate_count) Commit(0);
            else FlushRaw(wparam);
            return 0L;
        }
        if (key_length && wparam == '=') {
            if (candidate_count) {
                ++candidate_page;
                LoadPage();
                InvalidateRect(hwnd, NULL, TRUE);
            } else {
                FlushRaw(0);
                SendLiteral(wparam);
            }
            return 0L;
        }
        if (key_length && wparam == '-' && candidate_page) {
            --candidate_page;
            LoadPage();
            InvalidateRect(hwnd, NULL, TRUE);
            return 0L;
        }
        if (key_length && wparam >= 32) {
            if (candidate_count) Commit(0);
            else FlushRaw(0);
            SendLiteral(wparam);
            return 0L;
        }
        break;
    case WM_PAINT:
        dc = BeginPaint(hwnd, &ps);
        font = CreateFont(GetSystemMetrics(SM_CYSCREEN) <= 200 ? 10 : 16,
                          0, 0, 0, FW_NORMAL, 0, 0, 0,
                          DEFAULT_CHARSET, OUT_DEFAULT_PRECIS,
                          CLIP_DEFAULT_PRECIS, DEFAULT_QUALITY,
                          DEFAULT_PITCH | FF_DONTCARE, NULL);
        old_font = font ? SelectObject(dc, font) : NULL;
        lstrcpy(display, "Pinyin: ");
        lstrcat(display, key);
        TextOut(dc, 5, 3, display, lstrlen(display));
        memory = CreateCompatibleDC(dc);
        for (i = 0; i < candidate_count; ++i) {
            label[0] = (char)('1' + i);
            label[1] = '.';
            label[2] = '\0';
            symbol[0] = (char)candidates[i * 2];
            symbol[1] = (char)candidates[i * 2 + 1];
            TextOut(dc, 5 + i * 57, 22, label, 2);
            drawn = FALSE;
            if (memory && bitmap_available[i]) {
                bitmap = CreateBitmap(16, 16, 1, 1, candidate_bitmap[i]);
                if (bitmap) {
                    old_bitmap = SelectObject(memory, bitmap);
                    if (old_bitmap) {
                        drawn = BitBlt(dc, 25 + i * 57, 22, 16, 16,
                                       memory, 0, 0, SRCCOPY);
                        SelectObject(memory, old_bitmap);
                    }
                    DeleteObject(bitmap);
                }
            }
            if (!drawn)
                TextOut(dc, 25 + i * 57, 22, symbol, 2);
        }
        if (memory) DeleteDC(memory);
        if (font) {
            SelectObject(dc, old_font);
            DeleteObject(font);
        }
        EndPaint(hwnd, &ps);
        return 0L;
    case WM_DESTROY:
        if (clip_restore_pending) RestoreClipboard();
        FreeClipboardCopies();
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
    HINSTANCE nls;
    (void)command; (void)show;
    Trace("MAIN");
    if (!LoadIndex()) { Trace("NOINDEX"); return 1; }
    Trace("INDEX");
    if (!previous) {
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = (WNDPROC)IMEWNDPROC;
        wc.cbClsExtra = wc.cbWndExtra = 0;
        wc.hInstance = instance;
        wc.hIcon = NULL;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.hbrBackground = GetStockObject(WHITE_BRUSH);
        wc.lpszMenuName = NULL;
        wc.lpszClassName = "phon";
        if (!RegisterClass(&wc)) { Trace("NOCLASS"); return 2; }
    }
    Trace("CLASS");
    hwnd = CreateWindow("phon", "Pinyin GB2312", WS_POPUP | WS_BORDER,
                        10, GetSystemMetrics(SM_CYSCREEN) - 50,
                        GetSystemMetrics(SM_CXSCREEN) - 20, 44,
                        NULL, NULL, instance, NULL);
    if (!hwnd) { Trace("NOWINDOW"); return 3; }
    Trace("WINDOW");
    Trace("LOADLIB");
    nls = LoadLibrary("WINNLS.DLL");
    Trace("LOADED");
    (void)nls;
    hook_library = LoadLibrary("GBHOOK.DLL");
    if ((UINT)hook_library >= 32) {
        GBHOOK_START start_hook = (GBHOOK_START)GetProcAddress(
            hook_library, "GBHOOKSTART");
        gb_hook_stop = (GBHOOK_STOP)GetProcAddress(hook_library,
                                                 "GBHOOKSTOP");
        gb_hook_target = (GBHOOK_TARGET)GetProcAddress(hook_library,
                                                     "GBHOOKTARGET");
        gb_hook_next = (GBHOOK_NEXT)GetProcAddress(hook_library,
                                                 "GBHOOKNEXT");
        if (!start_hook || !gb_hook_stop || !gb_hook_target ||
            !gb_hook_next || !start_hook()) {
            FreeLibrary(hook_library);
            hook_library = 0;
            gb_hook_stop = NULL;
            gb_hook_target = NULL;
            gb_hook_next = NULL;
        }
    }
    ShowWindow(hwnd, SW_HIDE);
    SetTimer(hwnd, HOTKEY_TIMER, 40, NULL);
    target_proc_instance = (WNDPROC)MakeProcInstance(
        (FARPROC)PinyinTargetProc, instance);
    message_hook_instance = (HOOKPROC)MakeProcInstance(
        (FARPROC)PinyinMessageHook, instance);
    if (message_hook_instance
#ifdef PINYIN_NO_MESSAGE_HOOK
        && FALSE
#endif
        )
        previous_message_hook = SetWindowsHook(WH_GETMESSAGE,
                                               message_hook_instance);
    keyboard_hook_instance = (HOOKPROC)MakeProcInstance(
        (FARPROC)PinyinKeyboardHook, instance);
    if (keyboard_hook_instance
#ifdef PINYIN_NO_KEYBOARD_HOOK
        && FALSE
#endif
        )
        previous_keyboard_hook = SetWindowsHook(WH_KEYBOARD,
                                                keyboard_hook_instance);
#ifdef PINYIN_DIAGNOSTICS
    call_hook_instance = (HOOKPROC)MakeProcInstance(
        (FARPROC)PinyinCallHook, instance);
    if (call_hook_instance)
        previous_call_hook = SetWindowsHook(WH_CALLWNDPROC,
                                            call_hook_instance);
#endif
    Trace("READY");
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    if (message_hook_instance
#ifdef PINYIN_NO_MESSAGE_HOOK
        && FALSE
#endif
        )
        UnhookWindowsHook(WH_GETMESSAGE, message_hook_instance);
    if (keyboard_hook_instance
#ifdef PINYIN_NO_KEYBOARD_HOOK
        && FALSE
#endif
        )
        UnhookWindowsHook(WH_KEYBOARD, keyboard_hook_instance);
#ifdef PINYIN_DIAGNOSTICS
    if (call_hook_instance)
        UnhookWindowsHook(WH_CALLWNDPROC, call_hook_instance);
#endif
    {
        WORD slot;
        for (slot = 0; slot < TARGET_SLOTS; ++slot)
            if (hooked_windows[slot] && IsWindow(hooked_windows[slot]) &&
                (WNDPROC)GetWindowLong(hooked_windows[slot], GWL_WNDPROC)
                    == target_proc_instance)
                SetWindowLong(hooked_windows[slot], GWL_WNDPROC,
                              (LONG)original_procs[slot]);
    }
    if (target_proc_instance) FreeProcInstance((FARPROC)target_proc_instance);
    if (message_hook_instance) FreeProcInstance((FARPROC)message_hook_instance);
    if (keyboard_hook_instance) FreeProcInstance((FARPROC)keyboard_hook_instance);
    if (gb_hook_stop) gb_hook_stop();
    if ((UINT)hook_library >= 32) FreeLibrary(hook_library);
#ifdef PINYIN_DIAGNOSTICS
    if (call_hook_instance) FreeProcInstance((FARPROC)call_hook_instance);
#endif
    return (int)msg.wParam;
}
