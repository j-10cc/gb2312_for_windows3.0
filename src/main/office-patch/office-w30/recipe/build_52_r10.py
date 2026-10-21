"""Carry r9 and reapply its display patches to the dependency-correct EL build."""
from pathlib import Path
import json,hashlib,shutil
from audit_ne import audit
from patch_word_sdm52 import patch as sdm_patch
from patch_word_messages52 import patch as msg_patch,encode_message
P=Path(__file__).resolve().parent;out=P/'release/5.2-r10';shutil.copytree(P/'release/5.2-r9',out,dirs_exist_ok=True)
source=P/'build/5.2/word-macro-r10/WINWORD.EXE';raw=bytearray(source.read_bytes());d=json.loads((P/'patches/5.1/word-full-menu-directory-r6.json').read_text());before=bytes.fromhex(d['before_hex']);after=bytes.fromhex(d['after_hex']);assert raw.count(before)==1;at=raw.index(before);raw[at:at+len(after)]=after
temp=P/'build/5.2/word-macro-r10/WIN52.EXE';temp.write_bytes(raw);proofs={}
b,proofs['sdm']=sdm_patch(temp);temp.write_bytes(b)
b,proofs['messages']=msg_patch(temp);temp.write_bytes(b)
b=bytearray(b);old_ne=audit(P/'release/5.2-r3/WORD/WINWORD.EXE');new_ne=audit(temp)
for c in json.loads((P/'patches/5.2/word-banter-r4.json').read_text(encoding='utf-8'))['changes']:
 at=c['offset']-old_ne['segments'][9]['start']+new_ne['segments'][9]['start'];before=bytes.fromhex(c['before_hex']);after=bytes.fromhex(c['after_hex']);assert b[at:at+len(before)]==before;b[at:at+len(before)]=after
temp.write_bytes(b);b,proofs['dlb']=msg_patch(temp,'patches/5.2/word-dlb-translations.json');b=bytearray(b)
old_ne=audit(P/'release/5.2-r5/WORD/WINWORD.EXE');new_ne=audit(temp)
for c in json.loads((P/'patches/5.2/word-replace-runtime-r6.json').read_text())['changes']:
 at=c['offset']-old_ne['segments'][149]['start']+new_ne['segments'][149]['start'];before=bytes.fromhex(c['before_hex']);after=bytes.fromhex(c['after_hex']);assert b[at:at+len(before)]==before;b[at:at+len(before)]=after
for c in proofs['messages']['changes']:
 if c['key']=='OverwriteForeign':
  at=c['offset'];n=len(bytes.fromhex(c['after_hex']));b[at:at+n]=encode_message('将 \u0001\u0000 覆写为 \u0001\u0000?').ljust(n,b' ')
(out/'WORD/WINWORD.EXE').write_bytes(b)
proofs['build_manifest']='build/5.2/word-macro-r10/manifest.json';proofs['output_sha256']=hashlib.sha256(b).hexdigest().upper()
(P/'patches/5.2/word-r10-chain.json').write_text(json.dumps(proofs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('r10 Word EL dependency build and all 5.2 display patches reapplied')
