from pathlib import Path
import os,subprocess,shutil,json,hashlib
P=Path(__file__).resolve().parent;watcom=next(p for p in P.parents if (p/'src/main').is_dir() and (p/'release').is_dir())/'external/open-watcom'
env=os.environ.copy();env.update(WATCOM=str(watcom),INCLUDE=f'{watcom}/h;{watcom}/h/win',LIB=f'{watcom}/lib286;{watcom}/lib286/win');env['PATH']=str(watcom/'binnt64')+os.pathsep+env['PATH']
def lit(s):return ''.join(chr(b) if 32<=b<127 and b not in (34,92) else '\\%03o'%b for b in s.encode('gb2312'))
helper='''/* Owned Excel windows only. Do not touch the system menu definition. */
static void LocalizeSystem(HWND window) {
    HMENU menu=GetSystemMenu(window,FALSE);char before[80];int state;
    if (!menu) return;
'''
for command,new in [(0xf120,'还原&R'),(0xf010,'移动&M'),(0xf000,'大小&S'),(0xf020,'最小化&N'),(0xf030,'最大化&X'),(0xf060,'关闭&C\tAlt+F4'),(0xf130,'切换至&T\tCtrl+Esc')]:
 helper+='    state=GetMenuState(menu,0x%04X,MF_BYCOMMAND);\n    if (state!=-1) {\n        GetMenuString(menu,0x%04X,before,sizeof(before),MF_BYCOMMAND);\n        if (lstrcmp(before,"%s"))\n            ChangeMenu(menu,0x%04X,"%s",0x%04X,MF_CHANGE|(state&3));\n    }\n'%(command,command,lit(new),command,lit(new),command)
helper+='}\n\n'
rows=[]
for video,source in [('CGA',P/'patches/5.4/excel-launcher-layout-r3.c'),('VGA',P.parents[1]/'phase4/excel_charts/source/excel_gb_launcher.c')]:
 s=source.read_text('utf-8');anchor='BOOL __export FAR PASCAL FindExcelChild';assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor)
 old='    if (formula_window) return TRUE;\n    GetClassName(window, class_name, sizeof(class_name));'
 new='''    GetClassName(window, class_name, sizeof(class_name));
    if (!lstrcmpi(class_name,"XLWS") || !lstrcmpi(class_name,"XLCH") ||
        !lstrcmpi(class_name,"XLNOTE")) LocalizeSystem(window);
    if (formula_window) return TRUE;'''
 assert s.count(old)==1;s=s.replace(old,new)
 old='    if (!formula_window)\n        EnumChildWindows(window, (WNDENUMPROC)child_callback, 0L);';assert s.count(old)==1;s=s.replace(old,'    LocalizeSystem(window);\n    EnumChildWindows(window, (WNDENUMPROC)child_callback, 0L);')
 folder=P/f'build/5.7/launcher-{video.lower()}-r1';folder.mkdir(parents=True,exist_ok=True);f=folder/'excel57.c';f.write_text(s,encoding='ascii');shutil.copy2(f,P/f'patches/5.7/excel-{video.lower()}-system-r1.c')
 subprocess.run([str(watcom/'binnt64/wcc.exe'),'-0','-bt=windows',f.name],cwd=folder,env=env,check=True)
 subprocess.run([str(watcom/'binnt64/wlink.exe'),'system','windows','name','EXCEL.EXE','file','excel57.obj','option','modname=XLGB'],cwd=folder,env=env,check=True)
 shutil.copy2(folder/'EXCEL.EXE',P/f'release/5.7-r1/{video}/EXCEL.EXE')
 rows.append(dict(video=video,parent_source=str(source),source_sha256=hashlib.sha256(f.read_bytes()).hexdigest().upper(),output_sha256=hashlib.sha256((folder/'EXCEL.EXE').read_bytes()).hexdigest().upper()))
(P/'build/5.7/launchers-r1.json').write_text(json.dumps(rows,indent=2)+'\n')
