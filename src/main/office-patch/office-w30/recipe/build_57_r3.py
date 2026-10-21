from pathlib import Path
import json,shutil,re,hashlib
from patch_word_messages52 import patch
P=Path(__file__).resolve().parent;out=P/'release/5.7-r3';shutil.copytree(P/'release/5.7-r2',out,dirs_exist_ok=True);f=out/'WORD/WINWORD.EXE'
b,proof=patch(f,'patches/5.7/word-final-message-translations.json');assert not proof['unlocated_or_inherited'],proof['unlocated_or_inherited'];f.write_bytes(b)
# NoPrinters is reused for two distinct source literals. The generic keyed
# importer deliberately selects the last; patch the other exact owned record.
raw=f.read_bytes();old=b'Cannot change printer; no printers installed';token=bytes([len(old)])+old;hits=[m.start()+1 for m in re.finditer(re.escape(token),raw)];assert len(hits)==1
b=bytearray(raw);at=hits[0];v='未安装打印机，无法更换打印机'.encode('gb2312').ljust(len(old),b' ');assert len(v)==len(old);b[at:at+len(v)]=v;f.write_bytes(b)
proof['duplicate_key_record']=dict(offset=at,before_hex=old.hex().upper(),after_hex=v.hex().upper(),owner='wordtech/error.c; NoPrinters display variant',display='未安装打印机，无法更换打印机');proof['final_sha256']=hashlib.sha256(b).hexdigest().upper()
(P/'patches/5.7/word-final-messages-r3.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('5.7-r3 Word message fields',len(proof['changes'])+1)
