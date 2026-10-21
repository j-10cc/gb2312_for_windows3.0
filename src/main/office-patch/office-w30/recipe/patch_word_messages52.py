from pathlib import Path
import ast,re,json,hashlib
from audit_ne import audit
P=Path(__file__).resolve().parent
def encode_message(s):
 out=bytearray();i=0
 while i<len(s):
  if ord(s[i]) in range(1,9) or ord(s[i])==31:out+=bytes([ord(s[i]),ord(s[i+1])]);i+=2
  else:out+=s[i].encode('gb2312');i+=1
 return bytes(out)
def patch(path, translations_path='patches/5.2/word-message-translations.json'):
 raw=path.read_bytes();out=bytearray(raw);ne=audit(path);translations=json.loads((P/translations_path).read_text(encoding='utf-8'));source={}
 for name in ('message.h','wordtech/error.c','DLBENUM.C'):
  s=(P/'snapshot/word-stage/CASHMERE'/name).read_text(encoding='latin1')
  for literal,key in re.findall(r'St(?:Shared)?Key\s*\(\s*("(?:\\.|[^"\\])*")\s*,\s*(\w+)\s*\)',s):source[key]=(ast.literal_eval('b'+literal),name)
 changes=[];unlocated=[]
 for key,new in translations.items():
  assert key in source,key
  old,owner=source[key];new=encode_message(new);assert len(new)<=len(old),(key,len(new),len(old))
  # Preserve the parameter opcode and width bytes, including widths >=0x20.
  def params(s):
   result=[];i=0
   while i<len(s):
    if s[i] in range(1,9) or s[i]==31:result.append(s[i:i+2]);i+=2
    else:i+=1
   return result
  assert params(old)==params(new),(key,params(old),params(new))
  matches=[]
  for seg in ne['segments']:
   if not seg.get('file_backed'):continue
   if owner=='DLBENUM.C' and seg['index']!=84:continue
   for m in re.finditer(re.escape(bytes([len(old)])+old),raw[seg['start']:seg['end']]):matches.append((seg['start']+m.start()+1,seg['index']))
  if not matches:unlocated.append(key);continue
  for at,index in matches:
   after=new.ljust(len(old),b' ');out[at:at+len(old)]=after;changes.append({'key':key,'owner_source':owner,'offset':at,'segment':index,'before_hex':old.hex().upper(),'after_hex':after.hex().upper(),'display':translations[key]})
 restored=bytearray(out)
 for c in changes:at=c['offset'];old=bytes.fromhex(c['before_hex']);restored[at:at+len(old)]=old
 assert bytes(restored)==raw
 return bytes(out),{'input_sha256':hashlib.sha256(raw).hexdigest().upper(),'output_sha256':hashlib.sha256(out).hexdigest().upper(),'changes':changes,'unlocated_or_inherited':unlocated,'reverse_restoration':'PASS'}
if __name__=='__main__':
 out=P/'release/5.2-r3';(out/'WORD').mkdir(parents=True,exist_ok=True)
 data,proof=patch(P/'release/5.2-r2/WORD/WINWORD.EXE');(out/'WORD/WINWORD.EXE').write_bytes(data)
 import shutil
 for video in ('CGA','VGA'):shutil.copytree(P/f'release/5.2-r2/{video}',out/video,dirs_exist_ok=True)
 (P/'patches/5.2/word-messages-r3.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(len(proof['changes']),'message fields; unlocated',proof['unlocated_or_inherited'])
