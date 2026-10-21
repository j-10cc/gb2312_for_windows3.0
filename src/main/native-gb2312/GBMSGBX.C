#include <windows.h>

static char line[160];
static char value[80];

static void Log(HFILE file, char *text)
{
    _lwrite(file, text, lstrlen(text));
}

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    HFILE file;
    HINSTANCE user;
    HDC dc;
    HRSRC resource;
    DWORD units, extent;
    int id, size;
    (void)instance; (void)previous; (void)command; (void)show;
    file = _lcreat("C:\\GBMSG.LOG", 0);
    if (file == HFILE_ERROR) return 1;
    user = GetModuleHandle("USER");
    wsprintf(line, "USER=%u\r\n", (UINT)user); Log(file, line);
    GetModuleFileName(user, value, sizeof(value));
    wsprintf(line, "FILE=%s\r\n", (LPSTR)value); Log(file, line);
    resource = FindResource(user, MAKEINTRESOURCE(6), RT_STRING);
    wsprintf(line, "RESOURCE=%u\r\n", (UINT)resource); Log(file, line);
    for (id = 0; id <= 127; ++id) {
        value[0] = 0;
        size = LoadString(user, id, value, sizeof(value));
        if (!size) continue;
        wsprintf(line, "ID %d size %d hex %02X %02X %02X %02X\r\n",
                 id, size, (BYTE)value[0], (BYTE)value[1],
                 (BYTE)value[2], (BYTE)value[3]);
        Log(file, line);
    }
    units = GetDialogBaseUnits();
    wsprintf(line, "DLU %u %u\r\n", LOWORD(units), HIWORD(units));
    Log(file, line);
    dc = GetDC(NULL);
    extent = GetTextExtent(dc, "Yes(Y)", 6);
    wsprintf(line, "TEXT %u %u\r\n", LOWORD(extent), HIWORD(extent));
    Log(file, line);
    ReleaseDC(NULL, dc);
    _lclose(file);
    MessageBox(NULL, "MessageBox test", "GBMSGBX", MB_YESNOCANCEL);
    return 0;
}
