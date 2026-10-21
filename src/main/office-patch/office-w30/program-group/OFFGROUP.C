#include <windows.h>
#include <dde.h>
#include <string.h>

/* Windows 3.0 Program Manager DDE installer. No shell or system files change. */
static HWND client, server;
static HGLOBAL pending;
static char commands[4][256];
static const char group_name[] = "\xD6\xD0\xCE\xC4\xB0\xEC\xB9\xAB";
static const char created_text[] = "\263\314\320\362\327\351\322\321\317\324\312\276\241\243";
static const char removed_text[] =
    "\xB3\xCC\xD0\xF2\xD7\xE9\xD2\xD1\xC9\xBE\xB3\xFD\xA1\xA3";
static const char failed_text[] = "\316\336\267\250\317\324\312\276\263\314\320\362\327\351\241\243\307\353\315\313\263\366 Windows \272\363\326\330\305\334 INSTALL\241\243";
static const char exists_text[] =
    "\xB3\xCC\xD0\xF2\xD7\xE9\xD2\xD1\xB4\xE6\xD4\xDA\xA1\xA3";
static int step, failed;
static int command_count = 4, removing;
static int attempts;

static void Trace(const char *message)
{
    /* The installed helper does not write a log to a fixed drive. */
    (void)message;
}

static void NextCommand(void)
{
    char FAR *buffer;
    unsigned length;
    if (step == command_count) {
        Trace("DONE");
        PostMessage(server, WM_DDE_TERMINATE, client, 0L);
        DestroyWindow(client);
        return;
    }
    length = strlen(commands[step]) + 1;
    Trace(commands[step]);
    pending = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, length);
    if (!pending) { failed = 1; DestroyWindow(client); return; }
    buffer = GlobalLock(pending);
    if (!buffer) { GlobalFree(pending); pending = NULL; failed = 1; DestroyWindow(client); return; }
    _fmemcpy(buffer, commands[step], length);
    GlobalUnlock(pending);
    if (!PostMessage(server, WM_DDE_EXECUTE, client, MAKELONG(0, pending))) {
        GlobalFree(pending); pending = NULL; failed = 1; DestroyWindow(client);
    }
}

long FAR PASCAL __export ClientProc(HWND window, UINT message,
                                     WPARAM wparam, LPARAM lparam)
{
    switch (message) {
    case WM_DDE_ACK:
        if (!server) {
            Trace("INIT_ACK");
            server = (HWND)wparam;
            NextCommand();
        } else if ((HWND)wparam == server && pending) {
            unsigned status = LOWORD(lparam);
            HGLOBAL returned = (HGLOBAL)HIWORD(lparam);
            if (returned == pending) GlobalFree(pending);
            pending = NULL;
            if (!(status & 0x8000)) {
                Trace("EXEC_NACK");
                failed = 1;
                PostMessage(server, WM_DDE_TERMINATE, client, 0L);
                DestroyWindow(window);
            } else {
                Trace("EXEC_ACK");
                ++step;
                NextCommand();
            }
        }
        return 0L;
    case WM_DDE_TERMINATE:
        if ((HWND)wparam == server) {
            server = NULL;
            DestroyWindow(window);
        }
        return 0L;
    case WM_TIMER:
        if (!server && ++attempts <= 20) {
            ATOM application = GlobalAddAtom("PROGMAN");
            ATOM topic = GlobalAddAtom("PROGMAN");
            Trace("INIT_SEND");
            SendMessage((HWND)-1, WM_DDE_INITIATE, client,
                        MAKELONG(application, topic));
            GlobalDeleteAtom(application);
            GlobalDeleteAtom(topic);
            if (!server) Trace("INIT_RETRY");
        } else if (attempts > 20 || (server && attempts++ > 25)) {
            Trace("TIMEOUT");
            failed = 1;
            if (server) PostMessage(server, WM_DDE_TERMINATE, client, 0L);
            DestroyWindow(window);
        }
        return 0L;
    case WM_DESTROY:
        KillTimer(window, 1);
        PostQuitMessage(0);
        return 0L;
    }
    return DefWindowProc(window, message, wparam, lparam);
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous, LPSTR arg, int show)
{
    WNDCLASS cls;
    MSG msg;
    char path[100];
    char windows_path[100];
    char group_path[100];
    HFILE existing;
    int n;
    (void)show;
    while (*arg == ' ' || *arg == '\t') ++arg;
    removing = (*arg == 'R' || *arg == 'r');
    Trace("START");
    n = GetModuleFileName(instance, path, sizeof(path));
    Trace(path);
    while (n > 0 && path[n - 1] != '\\') --n;
    if (n > 0) path[n - 1] = 0;
    if (n < 4 || path[1] != ':' || path[2] != '\\' || n > 70) {
        Trace("BAD_PATH");
        MessageBox(NULL, "\307\353\264\323\260\262\327\260\304\277\302\274\324\313\320\320\040\117\106\106\107\122\117\125\120\056\105\130\105\241\243",
                   group_name, MB_OK | MB_ICONEXCLAMATION);
        return 2;
    }
    if (!GetWindowsDirectory(windows_path, sizeof(windows_path)) ||
        lstrlen(windows_path) > 70) return 2;
    Trace(windows_path);
    if (removing) {
        MessageBox(NULL, "Exit Windows, then run REMOVE.EXE with the Office path.", group_name, MB_OK);
        return 2;
    }
    if (!previous) {
        cls.style = 0;
        cls.lpfnWndProc = ClientProc;
        cls.cbClsExtra = cls.cbWndExtra = 0;
        cls.hInstance = instance;
        cls.hIcon = cls.hCursor = NULL;
        cls.hbrBackground = NULL;
        cls.lpszMenuName = NULL;
        cls.lpszClassName = "OFFGROUP30";
        if (!RegisterClass(&cls)) return 3;
    }
    Trace("CLASS_READY");
    client = CreateWindow("OFFGROUP30", "", WS_POPUP, 0, 0, 1, 1,
                          NULL, NULL, instance, NULL);
    if (!client) return 4;
    Trace("WINDOW_READY");
    lstrcpy(commands[0], "[ShowGroup(");
    lstrcat(commands[0], group_name);
    lstrcat(commands[0], ",1)]");
    command_count = 1;
    SetTimer(client, 1, 2000, NULL);
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    if (failed) {
        Trace("FAILED");
        MessageBox(NULL, failed_text, group_name,
                   MB_OK | MB_ICONEXCLAMATION);
        return 7;
    }
    MessageBox(NULL, removing ? removed_text : created_text,
               group_name, MB_OK);
    return 0;
}
