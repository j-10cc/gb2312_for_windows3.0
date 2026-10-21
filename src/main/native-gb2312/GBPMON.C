/* Win16 diagnostic: record top-level windows after Program Manager starts. */
#include <windows.h>
#include <stdio.h>

int PASCAL WinMain(HINSTANCE instance, HINSTANCE previous,
                   LPSTR command, int show)
{
    DWORD start = GetTickCount();
    FILE *output;
    HWND window;
    char class_name[64], title[96];
    (void)instance; (void)previous; (void)command; (void)show;
    while (GetTickCount() - start < 5000UL) Yield();
    output = fopen("GBPMON.LOG", "wb");
    if (!output) return 1;
    window = GetWindow(GetDesktopWindow(), GW_CHILD);
    while (window) {
        GetClassName(window, class_name, sizeof(class_name));
        GetWindowText(window, title, sizeof(title));
        fprintf(output, "%s|%s\r\n", class_name, title);
        window = GetWindow(window, GW_HWNDNEXT);
    }
    fclose(output);
    return 0;
}
