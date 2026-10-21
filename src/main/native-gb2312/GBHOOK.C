#include <windows.h>

/* Win16 global hooks must live in a DLL with one shared data segment.
   The hook only handles keys for the selected task and never calls the IME
   window from another task. */
#define QUEUE_CAPACITY 32
static BYTE keys[QUEUE_CAPACITY];
static WORD read_at;
static WORD write_at;
static HTASK selected_task;
static BOOL selected_active;
static BOOL selected_composing;
static HOOKPROC previous_hook;
static BOOL installed;

BOOL FAR PASCAL LibMain(HINSTANCE instance, WORD data_segment,
                        WORD heap_size, LPSTR command)
{
    (void)instance; (void)data_segment; (void)heap_size; (void)command;
    return TRUE;
}

int FAR PASCAL WEP(int reason)
{
    (void)reason;
    return 1;
}

LONG __export FAR PASCAL GBKeyboardHook(int code, WPARAM key,
                                        LPARAM state)
{
    WORD character, next;
    if (code != HC_ACTION || !selected_active ||
        GetCurrentTask() != selected_task ||
        ((DWORD)state & (0x80000000UL | 0x20000000UL)) ||
        (GetKeyState(VK_CONTROL) & 0x8000))
        return DefHookProc(code, key, state, &previous_hook);
    character = key;
    if (character >= 'A' && character <= 'Z')
        character += 'a' - 'A';
    if (!((character >= 'a' && character <= 'z') ||
          (selected_composing &&
           (character == VK_SPACE || character == VK_RETURN ||
            character == VK_BACK || character == VK_ESCAPE ||
            (character >= '1' && character <= '9')))))
        return DefHookProc(code, key, state, &previous_hook);
    if (character == VK_SPACE) character = ' ';
    else if (character == VK_RETURN) character = 13;
    else if (character == VK_BACK) character = 8;
    else if (character == VK_ESCAPE) character = 27;
    next = (write_at + 1) % QUEUE_CAPACITY;
    if (next == read_at)
        return DefHookProc(code, key, state, &previous_hook);
    keys[write_at] = (BYTE)character;
    write_at = next;
    return 1L;
}

WORD __export FAR PASCAL GBHookStart(void)
{
    if (installed) return 1;
    previous_hook = SetWindowsHook(WH_KEYBOARD, (HOOKPROC)GBKeyboardHook);
    installed = TRUE;
    return 1;
}

void __export FAR PASCAL GBHookStop(void)
{
    if (installed) {
        UnhookWindowsHook(WH_KEYBOARD, (HOOKPROC)GBKeyboardHook);
        installed = FALSE;
    }
    selected_active = FALSE;
    selected_task = 0;
    read_at = write_at = 0;
}

void __export FAR PASCAL GBHookTarget(HTASK task, WORD active,
                                      WORD composing)
{
    selected_task = task;
    selected_active = active != 0;
    selected_composing = composing != 0;
    if (!selected_active) read_at = write_at = 0;
}

WORD __export FAR PASCAL GBHookNext(void)
{
    WORD value;
    if (read_at == write_at) return 0;
    value = keys[read_at];
    read_at = (read_at + 1) % QUEUE_CAPACITY;
    return value;
}
