from pathlib import Path
import json,shutil,re,hashlib
from audit_ne import audit
from patch_word_messages52 import patch
P=Path(__file__).resolve().parent;out=P/'release/5.7-r2';shutil.copytree(P/'release/5.7-r1',out,dirs_exist_ok=True);f=out/'WORD/WINWORD.EXE'
(P/'patches/5.7/word-message-translations.json').write_text(json.dumps({'AboutKB':'\u0003\u0000 KB 可用'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
b,proof=patch(f,'patches/5.7/word-message-translations.json');assert len(proof['changes'])==3 and not proof['unlocated_or_inherited'];f.write_bytes(b)
(P/'patches/5.7/word-about-message-r2.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raw=f.read_bytes();b=bytearray(raw);ne=audit(f);changes=[]
for seg,old,new,owner in [(120,b'Show:','显示:','ibdefs.h outline iconbar labels'),(120,b'All','全','ibdefs.h outline iconbar label'),(117,b'Preview Version 1.1a (2401)','预览版 1.1a (2401)','help.c About version display')]:
 s=ne['segments'][seg-1];hits=[s['start']+m.start() for m in re.finditer(re.escape(old+b'\0'),raw[s['start']:s['end']])]
 if old.startswith(b'Preview') and not hits:
  hits=[ss['start']+m.start() for ss in ne['segments'] if ss.get('file_backed') for m in re.finditer(re.escape(old+b'\0'),raw[ss['start']:ss['end']])]
 assert hits,(old,seg)
 for at in hits:
  v=new.encode('gb2312').ljust(len(old),b' ');assert len(v)==len(old);b[at:at+len(v)]=v;changes.append(dict(offset=at,before_hex=old.hex().upper(),after_hex=v.hex().upper(),owner=owner,display=new))
f.write_bytes(b);back=bytearray(b)
for c in reversed(changes):a=c['offset'];v=bytes.fromhex(c['before_hex']);back[a:a+len(v)]=v
assert back==raw
(P/'patches/5.7/word-iconbar-version-r2.json').write_text(json.dumps(dict(input_sha256=hashlib.sha256(raw).hexdigest().upper(),output_sha256=hashlib.sha256(b).hexdigest().upper(),changes=changes,reverse_restoration='PASS'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('5.7-r2: About free memory/version and Outline labels complete')
