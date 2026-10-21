from pathlib import Path
import json,hashlib,os,subprocess,shutil
P=Path(__file__).resolve().parent;source=P.parents[1]/'phase6/OFFGROUP.C';s=source.read_text('ascii')
def lit(t):return ''.join('\\%03o'%b for b in t.encode('gb2312'))
for old,new,short in [('Word \\xCE\\xC4\\xD7\\xD6\\xB4\\xA6\\xC0\\xED','Word '+lit('文字处理'),'Word '+lit('文档')),('Excel \\xB5\\xE7\\xD7\\xD3\\xB1\\xED\\xB8\\xF1','Excel '+lit('电子表格'),'Excel '+lit('表格'))]:
 needle='"\\\\'+('WINWORD.EXE,' if old.startswith('Word') else 'EXCEL.EXE,')+old+',"'
 assert s.count(needle)==1,needle
 short='Word' if old.startswith('Word') else 'Excel'
 prefix='\\\\'+('WINWORD.EXE,' if old.startswith('Word') else 'EXCEL.EXE,')
 s=s.replace(needle,'(GetSystemMetrics(SM_CYSCREEN)<=200 ? "'+prefix+short+'," : "'+prefix+new+',")')
s=s.replace('"Run OFFGROUP.EXE from its installed directory."','"'+lit('请从安装目录运行 OFFGROUP.EXE。')+'"').replace('"Office group", MB_OK','group_name, MB_OK')
folder=P/'build/5.7/program-group-r1';folder.mkdir(parents=True,exist_ok=True);f=folder/'OFFGROUP.C';f.write_text(s,encoding='ascii');shutil.copy2(f,P/'patches/5.7/OFFGROUP-final.c')
watcom=next(p for p in P.parents if (p/'src/main').is_dir() and (p/'release').is_dir())/'external/open-watcom';env=os.environ.copy();env.update(WATCOM=str(watcom),INCLUDE=f'{watcom}/h;{watcom}/h/win',LIB=f'{watcom}/lib286;{watcom}/lib286/win');env['PATH']=str(watcom/'binnt64')+os.pathsep+env['PATH']
subprocess.run([str(watcom/'binnt64/wcc.exe'),'-0','-bt=windows',f.name],cwd=folder,env=env,check=True)
subprocess.run([str(watcom/'binnt64/wlink.exe'),'system','windows','name','OFFGROUP.EXE','file','OFFGROUP.OBJ'],cwd=folder,env=env,check=True)
shutil.copy2(folder/'OFFGROUP.EXE',P/'release/5.7-r4/OFFGROUP.EXE')
proof=dict(parent_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),source_sha256=hashlib.sha256(f.read_bytes()).hexdigest().upper(),output_sha256=hashlib.sha256((folder/'OFFGROUP.EXE').read_bytes()).hexdigest().upper(),scope='Only conditional product-name display captions for <=200-pixel CGA and bad-directory message; unchanged commands, icon sources, positions, DDE sequence, add/remove/existence behavior. Chinese group name retained. CGA Progman measured Chinese icon labels too narrowly, so product names are used as compact aliases.',captions=dict(cgar=['中文办公','Word','Excel'],vga=['中文办公','Word 文字处理','Excel 电子表格']))
(P/'build/5.7/program-group-r1.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
