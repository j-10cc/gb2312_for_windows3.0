from pathlib import Path
import json,re,ast,struct,shutil,hashlib
from audit_ne import audit
P=Path(__file__).resolve().parent;out=P/'release/5.2-r11';shutil.copytree(P/'release/5.2-r10',out,dirs_exist_ok=True)
proof={};path=out/'WORD/WINWORD.EXE';raw=path.read_bytes();b=bytearray(raw);ne=audit(path);changes=[]
source=(P/'snapshot/word-stage/CASHMERE/rerr.h').read_text(encoding='latin1');strings={key:ast.literal_eval('b'+literal) for literal,key in re.findall(r'SzKey\(\s*("(?:\\.|[^"\\])*")\s*,\s*(\w+)\)',source)}
def field(at,before,new,owner):
 after=new.encode('gb2312');assert len(after)<=len(before),(before,new);assert raw[at:at+len(before)]==before
 after=after.ljust(len(before),b' ');b[at:at+len(before)]=after;changes.append({'offset':at,'before_hex':before.hex().upper(),'after_hex':after.hex().upper(),'display':new,'owner':owner})
seg=ne['segments'][176]
for key,new in json.loads((P/'patches/5.2/word-macro-error-translations.json').read_text(encoding='utf-8')).items():
 old=strings[key];hits=[seg['start']+m.start() for m in re.finditer(re.escape(old+b'\0'),raw[seg['start']:seg['end']])];assert len(hits)==1,(key,hits)
 field(hits[0],old,new,'elsubs3/rerr.h; '+key)
for old,new in [(b'Macro interrupted','宏已中断'),(b' Err=',' 错=')]:
 hits=[seg['start']+m.start() for m in re.finditer(re.escape(old+b'\0'),raw[seg['start']:seg['end']])];assert hits,old
 for at in hits:field(at,old,new,'elsubs3.c; error display')
mapping=(P/'build/word-macro52-stage/OPUS/PROGRAM/WINWORD.MAP').read_text(encoding='latin1')
for module,old,new,storage in [('customiz',b'-- Separator --','-- 分隔线 --','nul'),('dlgdoc',b'Minute','分钟','pascal'),('dlgdoc',b'Minutes','分钟','pascal')]:
 index=int(re.search(r'^\s*([0-9A-F]+):0000\s+[0-9A-F]+H\s+'+module+r'_PCODE',mapping,re.M|re.I)[1],16);s=ne['segments'][index-1];token=(bytes([len(old)])+old) if storage=='pascal' else old+b'\0';hits=[s['start']+m.start()+(1 if storage=='pascal' else 0) for m in re.finditer(re.escape(token),raw[s['start']:s['end']])];assert hits,(module,old)
 for at in hits:field(at,old,new,module+'; display-only '+storage)
path.write_bytes(b);proof['Word']={'changes':changes,'input_sha256':hashlib.sha256(raw).hexdigest().upper(),'output_sha256':hashlib.sha256(b).hexdigest().upper()}
extra={
351318:('Paste &List','粘贴列表&L'),351330:('Paste &Name','粘贴名称&N'),
282597:('Cancel','取消'),282604:('Paste','粘贴'),282610:('&All','全&A'),282615:('Fo&rmulas','公式&R'),282625:('&Values','值&V'),282633:('Forma&ts','格式&T'),282642:('&Notes','批注&N'),282649:('Operation','运算'),282659:('N&one','无&O'),282665:('A&dd','加&D'),282670:('&Subtract','减&S'),282680:('&Multiply','乘&M'),282690:('D&ivide','除&I'),282698:('Skip &Blanks','跳过空白&B'),282711:('Transpos&e','转置&E'),
437615:('&Guess','推测&G'),437622:('&Clear','清除&C'),437629:('&Parse Line:','分列行&P:'),349090:('Record Macro','录制宏'),349103:('&Name:','名&N:'),349111:('&Key: Ctrl+','键&K: Ctrl+'),305681:('&Key: Ctrl+','键&K: Ctrl+'),305675:('N&one','无&O'),405734:('Protect Document','保护文档'),405773:('&Windows','窗口&W')}
resources=json.loads((P/'inventory/excel-string-resources.json').read_text(encoding='utf-8'))
for video in ('CGA','VGA'):
 path=out/video/'XLCORE.EXE';raw=path.read_bytes();b=bytearray(raw);changes=[]
 for at,(old,new) in extra.items():
  assert raw[at+len(old)]==0;assert [v.upper() for v in re.findall(r'&([^&])',old)]==[v.upper() for v in re.findall(r'&([^&])',new)],(old,new);field(at,old.encode(),new,'Native owned 5.2 custom dialog')
 # STRING resource 41: preserve all parser/file constants byte-for-byte while
 # repacking its sixteen Pascal fields. LoadString uses IDs, not file offsets.
 resource=next(r for k in audit(path)['resource_kinds'] if k['type']==6 for r in k['resources'] if r['id']==41)
 resource_rows=sorted([r for r in resources if r['variant']==video and 640<=r['string_id']<=655],key=lambda r:r['string_id']);assert len(resource_rows)==16
 pool=bytearray()
 for r in resource_rows:
  value={640:'提取',641:'条件&C',642:'表单&F',655:' / '}.get(r['string_id'],r['text']).encode('gb2312');assert len(value)<256;pool+=bytes([len(value)])+value
 start_res,end_res=resource['start'],resource['end'];assert len(pool)<=end_res-start_res;after=pool.ljust(end_res-start_res,b'\0');b[start_res:end_res]=after;changes.append({'offset':start_res,'before_hex':raw[start_res:end_res].hex().upper(),'after_hex':after.hex().upper(),'owner':'STRING 41; only IDs 640,641,642,655 translated; other twelve field values unchanged'})
 # Repack the seven Data Form button captions within their original local pool.
 labels=[('Ne&w','新&W'),('&Delete','删除&D'),('&Restore','恢复&R'),('Find &Prev','查上项&P'),('Find &Next','查下项&N'),('&Criteria','条件&C'),('E&xit','退出&X')];start,end=443986,444048;pool=bytearray();owned=[]
 for old,new in labels:
  at=raw.index(old.encode()+b'\0',start,end);refs=[x+8 for x in range(443300,start,2) if x+struct.unpack_from('<H',raw,x+8)[0]==at and struct.unpack_from('<H',raw,x+12)[0]==0x5003];assert len(refs)==1,(old,refs);ref=refs[0];target=start+len(pool);before=raw[ref:ref+2];after=struct.pack('<H',target-(ref-8));b[ref:ref+2]=after;changes.append({'offset':ref,'before_hex':before.hex().upper(),'after_hex':after.hex().upper(),'owner':'Data Form TM-relative caption pointer'});pool+=new.encode('gb2312')+b'\0';owned.append({'native_id':struct.unpack_from('<H',raw,ref+10)[0],'original':old,'display':new,'text_offset':target})
 assert len(pool)<=end-start;before=raw[start:end];after=pool.ljust(end-start,b'\0');b[start:end]=after;changes.append({'offset':start,'before_hex':before.hex().upper(),'after_hex':after.hex().upper(),'owner':'Data Form local caption pool; control IDs/order/rectangles unchanged'})
 path.write_bytes(b);proof[video]={'changes':changes,'Data_Form':owned,'input_sha256':hashlib.sha256(raw).hexdigest().upper(),'output_sha256':hashlib.sha256(b).hexdigest().upper()}
for key,p in proof.items():
 path=(out/'WORD/WINWORD.EXE') if key=='Word' else out/key/'XLCORE.EXE';restored=bytearray(path.read_bytes())
 for c in reversed(p['changes']):at=c['offset'];v=bytes.fromhex(c['before_hex']);restored[at:at+len(v)]=v
 assert hashlib.sha256(restored).hexdigest().upper()==p['input_sha256'];p['reverse_restoration']='PASS'
(P/'patches/5.2/runtime-and-extra-dialogs-r11.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('r11 fields:',{k:len(v['changes']) for k,v in proof.items()})
