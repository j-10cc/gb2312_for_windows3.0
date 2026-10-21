"""Isolated incremental build: application and document system menu captions."""
from pathlib import Path
import shutil,sys,json,hashlib
P=Path(__file__).resolve().parent
stage=P/'build/word-final57-stage';parent=P/'build/word-advanced53-stage'
(P/'build/5.7/word-system-r1').mkdir(parents=True,exist_ok=True)
(P/'patches/5.7').mkdir(parents=True,exist_ok=True)
assert not stage.exists();shutil.copytree(parent,stage)
def literal(s):return ''.join(chr(b) if 32<=b<127 and b not in (34,92) else '\\%03o'%b for b in s.encode('gb2312'))
proof=[]
for module,changes in {
 'init2':{'R&un...':'运行&U...'},
 'open':{'&Restore':'还原&R','&Move':'移动&M','&Size':'大小&S','Ma&ximize':'最大化&X','&Close':'关闭&C','Spli&t':'拆分&T','&Next Window':'下一窗口&N'},
}.items():
 f=stage/f'CASHMERE/{module}.c';s=f.read_text('latin1');before=s
 for old,new in changes.items():
  needle='SzSharedKey("'+old+'",';assert s.count(needle)==1,(module,old)
  s=s.replace(needle,'SzSharedKey("'+literal(new)+'",')
 if module=='init2':
  anchor='\t/* change Window\'s separators\' bcms to negative values */';assert s.count(anchor)==1
  code='\t/* Application-owned menu captions; command IDs and state are retained. */\n'
  for command,new in [(0xf120,'还原&R'),(0xf010,'移动&M'),(0xf000,'大小&S'),(0xf020,'最小化&N'),(0xf030,'最大化&X'),(0xf060,'关闭&C\tAlt+F4'),(0xf130,'切换至&T\tCtrl+Esc')]:
   code+='\tw = GetMenuState(hSysMenu, 0x%04X, MF_BYCOMMAND);\n\tif (f && w != -1) ChangeMenu(hSysMenu, 0x%04X,\n\t\t(LPSTR) SzShared("%s"), 0x%04X, MF_CHANGE | (w & 3));\n'%(command,command,literal(new),command)
  s=s.replace(anchor,code+'\n'+anchor)
 f.write_text(s,encoding='latin1');shutil.copy2(f,P/f'patches/5.7/{module}-system-r1.c')
 proof.append(dict(module=module,parent_sha256=hashlib.sha256(before.encode('latin1')).hexdigest().upper(),source_sha256=hashlib.sha256(s.encode('latin1')).hexdigest().upper()))
(P/'patches/5.7/word-system-source.json').write_text(json.dumps(proof,indent=2)+'\n')
sys.path.insert(0,str(P/'support'));import rebuild_table_candidate as b
b.HERE=P/'build/5.7';b.SOURCE=parent;b.STAGE=stage;b.MODULES=('init2','open')
sys.argv=[sys.argv[0],'--resume','--output',str(P/'build/5.7/word-system-r1')];b.main()
