"""Repack SDM-local label pools and relative TM pointers without NE growth.

SDM TM.wSlot is relative to that TM; DLT.bpTitle is relative to the DLT.
All control flags, CAB links, IDs, procedure references and rectangles stay.
"""
from pathlib import Path
import re,struct,json,hashlib
from audit_ne import audit
P=Path(__file__).resolve().parent
def r(p):return json.loads((P/p).read_text(encoding='utf-8'))
def patch(path,census_path='inventory/dialog-owner-census-5.2.json',translation_path='patches/5.2/word-dialog-translations.json'):
 raw=path.read_bytes();result=bytearray(raw);ne=audit(path);census=r(census_path);translations=r(translation_path);idd={m[0]:int(m[1]) for m in re.findall(r'^#define\s+(IDD\w+)\s+(\d+)',(P/'snapshot/word-stage/CASHMERE/idd.h').read_text(encoding='latin1'),re.M)}
 types={m[0]:int(m[1]) for m in re.findall(r'^#define\s+(tmt\w+)\s+(\d+)',(P/'snapshot/word-stage/CASHMERE/lib/sdmtmpl.h').read_text(encoding='latin1'),re.M)}
 proofs=[];spans=[]
 for name in census['word_scope']:
  rows=[x for x in census['word'] if x['dialog']==name];source=(P/rows[0]['source']).read_text(encoding='latin1');m=re.search(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\},\s*(IDD\w+)',source);assert m,name
  coords=tuple(map(int,m.groups()[:4]));header=struct.pack('<5H',*coords,idd[m[5]]);hits=[]
  for index in rows[0]['owner_ne_segments']:
   s=ne['segments'][index-1];hits += [(s['start']+q.start(),index) for q in re.finditer(re.escape(header),raw[s['start']:s['end']])]
  assert hits,name
  for at,index in hits:
   seg=ne['segments'][index-1]
   items=re.findall(r'\{\s*(tmt\w+)([^\r\n]*)',source);assert items[-1][0]=='tmtEnd',name;pool_start=at+20+len(items)*8;strings=[]
   intro=source[:source.index('/* Item Info */')];title=re.findall(r'"([^"\r\n]*)"',intro)
   if title:strings.append((at+18,at,title[-1].encode('latin1')))
   for n,(typ,line) in enumerate(items):
    tm=at+20+8*n;actual=struct.unpack_from('<H',raw,tm)[0]&63;assert actual==types[typ],(name,n,typ,actual)
    tokens=re.findall(r'"([^"\r\n]*)"',line)
    if tokens:strings.append((tm+2,tm,tokens[0].encode('latin1')))
   current=[]
   for pointer,base,old in strings:
    target=base+struct.unpack_from('<H',raw,pointer)[0];end=raw.index(b'\0',target,seg['end']);assert pool_start<=target<=end<seg['end'],(name,target,pool_start)
    current.append((pointer,base,old,target,end))
   if not current:continue
   assert min(x[3] for x in current)==pool_start,(name,'pool start');pool_end=max(x[4] for x in current)+1;pool=bytearray();labels=[];dedup={}
   for pointer,base,old,target,end in current:
    original=old.decode('gb2312');before=raw[target:end].decode('gb2312');new=translations.get(original)
    if new is None:
     assert not original.isascii() or not re.search('[A-Za-z]',original),(name,original)
     new=original
    original_keys=re.findall(r'(?<!&)&([^&])',original);new_keys=re.findall(r'(?<!&)&([^&])',new);assert [x.upper() for x in original_keys]==[x.upper() for x in new_keys],(name,original,new)
    data=new.encode('gb2312')+b'\0'
    if data not in dedup:dedup[data]=len(pool);pool+=data
    relative=pool_start+dedup[data]-base;assert 0<relative<65536
    struct.pack_into('<H',result,pointer,relative);labels.append({'original':original,'parent_display':before,'display':new,'pointer_offset':pointer,'relative_base':base,'parent_text_offset':target,'text_offset':base+relative})
   assert len(pool)<=pool_end-pool_start,(name,len(pool),pool_end-pool_start)
   result[pool_start:pool_end]=pool.ljust(pool_end-pool_start,b'\0');spans += [(pool_start,pool_end)]+[(p,p+2) for p,_,_,_,_ in current];proofs.append({'dialog':name,'segment':index,'template_offset':at,'pool_start':pool_start,'pool_end':pool_end,'used_bytes':len(pool),'parent_pool_bytes':pool_end-pool_start,'source':rows[0]['source'],'labels':labels,'control_structure_and_rectangles_unchanged':True})
 changes=[];start=None
 for i,(a,b) in enumerate(zip(raw,result)):
  if a!=b and start is None:start=i
  if a==b and start is not None:changes.append({'offset':start,'before_hex':raw[start:i].hex().upper(),'after_hex':result[start:i].hex().upper()});start=None
 if start is not None:changes.append({'offset':start,'before_hex':raw[start:].hex().upper(),'after_hex':result[start:].hex().upper()})
 restored=bytearray(result)
 for c in changes:restored[c['offset']:c['offset']+len(bytes.fromhex(c['before_hex']))]=bytes.fromhex(c['before_hex'])
 assert bytes(restored)==raw and len(result)==len(raw)
 return bytes(result),{'input_sha256':hashlib.sha256(raw).hexdigest().upper(),'output_sha256':hashlib.sha256(result).hexdigest().upper(),'format_proof':'20-byte DLT header, 8-byte TM, TM-relative string pointers, template-local pool; source types and owned NE segment matched.','templates':proofs,'changes':changes,'reverse_restoration':'PASS'}
if __name__=='__main__':
 data,proof=patch(P/'release/5.1-r11/WORD/WINWORD.EXE');out=P/'release/5.2-r1/WORD';out.mkdir(parents=True,exist_ok=True);(out/'WINWORD.EXE').write_bytes(data);(P/'patches/5.2/word-sdm-r1.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Word:',len(proof['templates']),'owned SDM pools repacked; all individual mnemonics preserved; exact reverse restoration.')
