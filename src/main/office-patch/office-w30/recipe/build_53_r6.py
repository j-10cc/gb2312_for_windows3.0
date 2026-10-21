"""Preview iconbar captions; parser and command descriptors stay untouched."""
from pathlib import Path
import shutil,re,json,hashlib
from audit_ne import audit
P=Path(__file__).resolve().parent;out=P/'release/5.3-r6';shutil.copytree(P/'release/5.3-r5',out,dirs_exist_ok=True);path=out/'WORD/WINWORD.EXE';raw=path.read_bytes();b=bytearray(raw);ne=audit(path);rows=[]
def change(seg,old,new,owner):
 s=ne['segments'][seg-1];value=new.encode('gb2312');assert len(value)<=len(old);hits=[s['start']+m.start() for m in re.finditer(re.escape(old+b'\0'),raw[s['start']:s['end']])];assert hits,(seg,old)
 for at in hits:
  after=value.ljust(len(old),b' ');b[at:at+len(old)]=after;rows.append({'offset':at,'before_hex':old.hex().upper(),'after_hex':after.hex().upper(),'original':old.decode('gb2312'),'display':new,'owner':owner,'segment':seg})
for old,new in [(b'&Print...','打印&P...'),(b'&Boundaries','边界&B'),(b'Page &View','页面&V'),('&取消  '.encode('gb2312'),'取消&C')]:change(120,old,new,'ibdefs.h: preview iconbar templates')
for old,new in [(b'One P&age','单页&A'),(b'Two P&ages','双页&A'),(b'&Close','关闭&C')]:change(141,old,new,'prvw2.c: runtime preview labels')
path.write_bytes(b);restored=bytearray(b)
for c in reversed(rows):at=c['offset'];old=bytes.fromhex(c['before_hex']);restored[at:at+len(old)]=old
assert restored==raw
(P/'patches/5.3/preview-toolbar-r6.json').write_text(json.dumps({'input_sha256':hashlib.sha256(raw).hexdigest().upper(),'output_sha256':hashlib.sha256(b).hexdigest().upper(),'changes':rows,'reverse_restoration':'PASS','scope':'Only existing preview UI strings in iconbar3/prvw2; no code, IDs, rectangles, parser or print data changes.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('5.3-r6:',len(rows),'preview toolbar labels')
