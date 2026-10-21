"""Port-E9 trace in a separate diagnostic build; never modifies release bytes."""
import os
import shutil
import subprocess
from test_runtime import ROOT, NATIVE, OUT
from test_office import run


def main():
    target=OUT/'common-trace'
    target.mkdir(exist_ok=True)
    source=(NATIVE/'PINYIN_NATIVE.C').read_text('utf-8')
    source='#include <conio.h>\nstatic void Trace(const char *p) { while (*p) outp(0xe9,*p++); }\n'+source
    patches={
        '    case WM_CHAR:\n        c = (BYTE)wparam;':'    case WM_CHAR:\n        Trace("CHAR "); outp(0xe9,(BYTE)wparam); Trace("\\n"); c = (BYTE)wparam;',
        '            LoadPage();\n            Redraw();':'            Trace("LOAD\\n"); LoadPage(); Trace("LOADED\\n");\n            Redraw(); Trace("REDRAWN\\n");',
        '    case WM_PAINT:\n        dc = BeginPaint(hwnd, &ps);':'    case WM_PAINT:\n        Trace("PAINT\\n"); dc = BeginPaint(hwnd, &ps); Trace("BEGUN\\n");',
        '        old_font = font ? SelectObject(dc, font) : NULL;':'        Trace("FONT\\n"); old_font = font ? SelectObject(dc, font) : NULL;',
        '        memory = CreateCompatibleDC(dc);':'        Trace("TEXT\\n"); memory = CreateCompatibleDC(dc);',
        '        bitmap_file = OpenGlyphFont();':'        Trace("HEADING\\n"); bitmap_file = OpenGlyphFont(); Trace("OPENED\\n");',
        '        if (bitmap_file != HFILE_ERROR) _lclose(bitmap_file);':'        Trace("CANDIDATES\\n"); if (bitmap_file != HFILE_ERROR) _lclose(bitmap_file);',
        '        EndPaint(hwnd, &ps);':'        Trace("ENDPAINT\\n"); EndPaint(hwnd, &ps); Trace("PAINTED\\n");',
        '    FitApplication();':'    Trace("FIT\\n"); FitApplication(); Trace("FITTED\\n");',
        '    InvalidateRect(ime_window, NULL, TRUE);':'    Trace("INVALIDATE\\n"); InvalidateRect(ime_window, NULL, TRUE); Trace("INVALIDATED\\n");',
        '    HWND destination = Destination();\n    if (!destination || choice >= candidate_count) return;':'    HWND destination = Destination();\n    Trace("COMMIT\\n"); if (!destination || choice >= candidate_count) return;',
    }
    for old,new in patches.items():
        assert old in source,old
        source=source.replace(old,new)
    (target/'PINYIN_NATIVE.C').write_text(source,'utf-8')
    shutil.copy2(NATIVE/'PINYIN_DICT.H',target/'PINYIN_DICT.H')
    for name in ('GBPY.DAT','WINNLS.DLL','IMEINFO.INI'): shutil.copy2(OUT/name,target/name)
    wc=ROOT/'external/open-watcom'
    env=os.environ.copy()
    env.update(WATCOM=str(wc),INCLUDE=f'{wc}/h;{wc}/h/win',LIB=f'{wc}/lib286;{wc}/lib286/win',
               PATH=str(wc/'binnt64')+os.pathsep+env.get('PATH',''))
    subprocess.run([str(wc/'binnt64/wcc.exe'),'-0','-bt=windows','-os','PINYIN_NATIVE.C'],cwd=target,env=env,check=True)
    subprocess.run([str(wc/'binnt64/wlink.exe'),'system','windows','name','PHON.IME','file','PINYIN_NATIVE.obj',
                    'export','DLGPROC.1=PinyinDlgProc','export','IMEWNDPROC.2','option','modname=PHON',
                    'option','stack=2048','option','heapsize=256'],cwd=target,env=env,check=True)
    print(run('word','vga','s','common21-trace-word',runtime=target,native_capture=True))


if __name__=='__main__':main()
