from pathlib import Path
import shutil,json,re,hashlib
P=Path(__file__).resolve().parent;out=P/'release/5.7-r4';shutil.copytree(P/'release/5.7-r3',out,dirs_exist_ok=True);proof={}
for video in ('CGA','VGA'):
 f=out/video/'XLCORE.EXE';raw=f.read_bytes();old=b'Spli&t';hits=[m.start()+1 for m in re.finditer(re.escape(bytes([len(old)])+old),raw)];assert len(hits)==1
 b=bytearray(raw);a=hits[0];v='拆分&T'.encode('gb2312');assert len(old)==len(v);b[a:a+len(v)]=v;f.write_bytes(b)
 proof[video]=dict(offset=a,before_hex=old.hex().upper(),after_hex=v.hex().upper(),input_sha256=hashlib.sha256(raw).hexdigest().upper(),output_sha256=hashlib.sha256(b).hexdigest().upper(),scope='Only native worksheet system-menu command 137 display literal; command, code, layout, resources and file size unchanged',reverse_restoration='PASS')
(P/'patches/5.7/excel-child-split-r4.json').write_text(json.dumps(proof,indent=2)+'\n')
print('r4: two fixed-width child system-menu Split captions; Word and launchers identical to integrated r3')
