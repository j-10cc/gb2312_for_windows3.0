#include <windows.h>

/* Test-only helper: inject the Ctrl+Space sequence into the stock WINNLS
 * keyboard callback after the shell has gained focus. Not installed. */
typedef LRESULT (FAR PASCAL *KEYBOARD_HOOK)(int, WORD, DWORD);

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    HINSTANCE nls;
    KEYBOARD_HOOK hook;
    MSG msg;
    (void)instance; (void)previous; (void)command; (void)show;
    nls = LoadLibrary("WINNLS.DLL");
    if ((UINT)nls < 32) return 1;
    hook = (KEYBOARD_HOOK)GetProcAddress(nls, MAKEINTRESOURCE(2));
    if (!hook) return 2;
    if (!SetTimer(NULL, 1, 7000, NULL)) return 3;
    while (GetMessage(&msg, NULL, 0, 0)) {
        if (msg.message == WM_TIMER && msg.wParam == 1) {
            KillTimer(NULL, 1);
            hook(0, VK_CONTROL, 0L);
            hook(0, VK_SPACE, 0L);
            hook(0, VK_CONTROL, 0x80000000L);
            break;
        }
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
