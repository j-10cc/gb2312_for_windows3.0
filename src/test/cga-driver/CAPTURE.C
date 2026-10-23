#include <windows.h>
#include <dos.h>

/* Unattended real-mode Program Manager fixture. Save physical CGA pixels. */
static unsigned ticks;
static char labels[][16] = {"\xbc\xf4\xcc\xf9\xb0\xe5\xb2\xe9\xbf\xb4\xc6\xf7", "\xbb\xad\xcd\xbc", "\xd3\xce\xcf\xb7"};
static HFILE treefile;
static WNDENUMPROC childproc,topproc;
BOOL __export FAR PASCAL MinimizeGroup(HWND child, LPARAM data)
{
    char title[40];
    char cls[40],line[120];
    (void)data;
    GetWindowText(child,title,sizeof(title));
    GetClassName(child,cls,sizeof(cls));
    wsprintf(line,"%u %s %s\r\n",(UINT)child,(LPSTR)cls,(LPSTR)title);
    _lwrite(treefile,line,lstrlen(line));
    if (title[0] == (char)0xcd && title[1] == (char)0xbc) {
        SetWindowText(child,labels[2]);
        CloseWindow(child);
        return FALSE;
    }
    return TRUE;
}
BOOL __export FAR PASCAL VisitTop(HWND child, LPARAM data)
{
    EnumChildWindows(child,childproc,data);
    return TRUE;
}
LONG __export FAR PASCAL CaptureProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    HFILE file;
    if (msg == WM_TIMER) {
        ++ticks;
        if (ticks == 18) {
            treefile=_lcreat("C:\\TREE.LOG",0);
            EnumWindows(topproc,0L);
            _lclose(treefile);
        }
        if (ticks != 16 && ticks != 32) return 0L;
        file = _lcreat(ticks == 16 ? "C:\\SCREEN.BIN" : "C:\\SCREEN2.BIN", 0);
        if (file != HFILE_ERROR) {
            _lwrite(file, (LPCSTR)MK_FP(0xb800, 0), 16384);
            _lclose(file);
        }
        if (ticks == 32) KillTimer(hwnd, 1);
        return 0L;
    }
    return DefWindowProc(hwnd, msg, wp, lp);
}
int PASCAL WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
    WNDCLASS wc;
    HWND hwnd;
    MSG msg;
    HDC dc;
    HFILE file;
    DWORD extent;
    int i,j;
    char line[100];
    (void)prev; (void)cmd; (void)show;
    wc.style=0; wc.lpfnWndProc=(WNDPROC)CaptureProc;
    wc.cbClsExtra=wc.cbWndExtra=0; wc.hInstance=inst;
    wc.hIcon=NULL; wc.hCursor=NULL; wc.hbrBackground=NULL;
    wc.lpszMenuName=NULL; wc.lpszClassName="CaptionCapture";
    if (!RegisterClass(&wc)) return 1;
    hwnd=CreateWindow(wc.lpszClassName, "", WS_POPUP,
                      0,0,1,1,NULL,NULL,inst,NULL);
    if (!hwnd) return 2;
    childproc=(WNDENUMPROC)MakeProcInstance((FARPROC)MinimizeGroup,inst);
    topproc=(WNDENUMPROC)MakeProcInstance((FARPROC)VisitTop,inst);
    dc=GetDC(NULL); file=_lcreat("C:\\EXTENT.LOG",0);
    for(i=0;i<3;i++) for(j=0;j<lstrlen(labels[i]);j+=2) {
        extent=GetTextExtent(dc,labels[i]+j,2);
        wsprintf(line,"%02X%02X extent=%u,%u\r\n",(BYTE)labels[i][j],(BYTE)labels[i][j+1],LOWORD(extent),HIWORD(extent));
        _lwrite(file,line,lstrlen(line));
    }
    _lclose(file); ReleaseDC(NULL,dc);
    SetTimer(hwnd,1,500,NULL);
    WinExec("PROGMAN.EXE", SW_SHOW);
    while(GetMessage(&msg,NULL,0,0)) {
        TranslateMessage(&msg); DispatchMessage(&msg);
    }
    return 0;
}
