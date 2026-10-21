"""Reassemble reviewed patches in fresh paths, then finish owned display pools."""
from pathlib import Path
import json,shutil,re,struct,hashlib,os,subprocess
from audit_ne import audit
from patch_word_sdm52 import patch
P=Path(__file__).resolve().parent;out=P/'release/5.7-r1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def W(n,v):
 f=P/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
W('build/5.7/parent-lock.json',dict(parent='release/5.6-r1/manifest.json',sha256=sha(P/'release/5.6-r1/manifest.json')))
# Every replay writes new 5.7 proof files. Historical releases stay immutable.
s=(P/'build_53_r5.py').read_text('utf-8')
s=s.replace("s=(P/'build_53_r2.py').read_text(encoding='utf-8')", "s=(P/'build_53_r2.py').read_text(encoding='utf-8').replace('word-parent52-r2-chain.json','../5.7/word-parent52-chain.json').replace('patches/5.3/word-parent52-extra-r2.json','patches/5.7/word-parent52-extra.json')")
s=s.replace('release/5.3-r5','release/5.7-r1').replace(".replace('word-layout-r2','word-layout-r5')",".replace('word-layout-r2','../5.7/word-system-r1')")
s=s.replace('patches/5.3/runtime-r5.json','patches/5.7/runtime-parent53.json').replace('patches/5.3/messages-r5.json','patches/5.7/messages-parent53.json').replace("'word-sdm-r5.json'","'../5.7/word-sdm-parent53.json'")
exec(compile(s,str(P/'build_53_r5.py'),'exec'))
s=(P/'build_53_r6.py').read_text('utf-8').replace('release/5.3-r6','release/5.7-r1').replace("shutil.copytree(P/'release/5.3-r5',out,dirs_exist_ok=True);",'').replace('patches/5.3/preview-toolbar-r6.json','patches/5.7/preview-toolbar-parent53.json')
exec(compile(s,str(P/'build_53_r6.py'),'exec'))
path=out/'WORD/WINWORD.EXE';raw=path.read_bytes();b=bytearray(raw);ne=audit(path);rows=[]
for c in json.loads((P/'patches/5.3/preview-initial-r7.json').read_text())['changes']:
 seg=ne['segments'][c['segment']-1];old=bytes.fromhex(c['before_hex']);hits=[seg['start']+m.start() for m in re.finditer(re.escape(old+b'\0'),raw[seg['start']:seg['end']])];assert len(hits)==1
 at=hits[0];v=bytes.fromhex(c['after_hex']);b[at:at+len(v)]=v;rows.append(dict(c,offset=at))
path.write_bytes(b);W('patches/5.7/preview-initial-parent53.json',dict(input_sha256=hashlib.sha256(raw).hexdigest().upper(),output_sha256=sha(path),changes=rows))
for video in ('CGA','VGA'):shutil.copytree(P/f'release/5.6-r1/{video}',out/video,dirs_exist_ok=True)
scope='about apprun cmpfile filenam2 hyphen ribbon ribbon3 ruler ruler3 showvars spell spellmm thesaur usrdlg vrfcnvtr'.split()
mapping=(P/'build/word-final57-stage/OPUS/PROGRAM/WINWORD.MAP').read_text('latin1')
segments={name.lower():int(seg,16) for seg,name in re.findall(r'^\s*([0-9A-F]+):0000\s+[0-9A-F]+H\s+(\w+)_PCODE',mapping,re.M)}
owners={}
for f in (P/'snapshot/word-stage/CASHMERE').rglob('*.c'):
 for name in re.findall(r'#include\s+"([^"/]+)\.sdm"',f.read_text('latin1'),re.I):owners.setdefault(name.lower(),set()).add(f.stem.lower())
# These four SDMs are included through ibdefs.h under RIBBON/RULERIB,
# both explicitly defined by iconbar2.c, rather than a direct C include.
for name in ('ribbon','ribbon3','ruler','ruler3'):owners[name]={'iconbar2'}
tr={'Conventional Memory:':'常规内存:','Expanded Memory:':'扩充内存:','Math Co-processor:':'数学协处理器:','Disk Space:':'磁盘空间:','Run Application':'运行程序','&Clipboard':'剪贴板&C','Control &Panel':'控制面板&P','Compare File &Name:':'比较文件名&N:','&Files:':'文件&F:','&Directories:':'目录&D:','New File &Name:':'新文件名&N:','Hyphenate':'断字','Hyphenate &at:':'断字处&A:','&Hyphenate Caps':'大写字断字&H','&Confirm':'确认&C','Hot &Zone:':'断字区&Z:','&Yes':'是&Y','&No':'否&N','Font:':'字体:','Pts:':'磅:','Style:':'样式:','&Variables:':'变量&V:','&Set...':'设置&S...','Close':'关闭','&Start':'开始&S','Check Spelling':'拼写检查','&Options >>':'选项&O >>','&Word':'字词&W','&Check':'检查&C','&Delete':'删除&D','Dictionaries':'词典','&Main:':'主词典&M:','S&upplemental:':'补充词典&U:','&Ignore All CAPS':'忽略大写&I','&Always Suggest':'始终建议&A','Spelling':'拼写','Not in Dictionary:':'词典中无此词:','Change &To:':'更改为&T:','S&uggestions:':'建议&U:','&Ignore':'忽略&I','&Suggest':'建议&S','&Change':'更改&C','&Add':'添加&A','Add To &Dictionary:':'添加到词典&D:','Ig&nore All CAPS':'忽略大写&N','A&lways Suggest':'始终建议&L','Thesaurus':'同义词','&Look Up:':'查询&L:','S&ynonyms:':'同义词&Y:','&Definitions:':'释义&D:','&Replace':'替换&R','&Synonyms':'同义词&S','&Original':'原词&O','XXX':'XXX','Convert &File From:':'源格式&F:'}
W('patches/5.7/word-dialog-translations.json',tr)
idd={a:int(b) for a,b in re.findall(r'^#define\s+(IDD\w+)\s+(\d+)',(P/'snapshot/word-stage/CASHMERE/idd.h').read_text('latin1'),re.M)}
raw=path.read_bytes();ne=audit(path);census=[];found=[];status=[]
for name in scope:
 f=P/f'snapshot/word-stage/OPUS/{name}.sdm';s=f.read_text('latin1');mods=sorted(owners.get(name,set()));ids=[segments[m] for m in mods if m in segments]
 m=re.search(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\},\s*(IDD\w+)',s);hits=[]
 if m and ids:
  token=struct.pack('<5H',*map(int,m.groups()[:4]),idd[m[5]])
  for i in ids:
   seg=ne['segments'][i-1];hits += [seg['start']+q.start() for q in re.finditer(re.escape(token),raw[seg['start']:seg['end']])]
 texts=re.findall(r'"([^"\r\n]*)"',s)
 if hits and texts:
  found.append(name)
  for n,t in enumerate(texts):census.append(dict(id=f'word.sdm.{name}.{n:03}',dialog=name,source=str(f.relative_to(P)),original=t,owner_modules=mods,owner_ne_segments=ids,source_sha256=sha(f)))
 status.append(dict(dialog=name,owner_modules=mods,owner_ne_segments=ids,compiled_template_hits=hits,source_field_count=len(texts),disposition='COMPILED_DISPLAY_PATCH' if hits and texts else 'NO_LITERAL_FIELDS' if not texts else 'NOT_LOCATED_IN_OWNED_RELEASE_SEGMENTS',dynamic='PENDING' if name in ('about','apprun','cmpfile','hyphen','showvars','vrfcnvtr') and hits else 'STATIC_ONLY'))
W('inventory/dialog-owner-census-5.7.json',dict(word_scope=found,word=census,remaining_source_templates=status))
b,proof=patch(path,'inventory/dialog-owner-census-5.7.json','patches/5.7/word-dialog-translations.json');path.write_bytes(b);W('patches/5.7/word-sdm-r1.json',proof)
# Fixed-width RT_STRING display edits. Unselected parser and file-format fields remain exact.
tr={296:'未指定数据点编号。',298:'刻度间隔必须大于 0。',299:'无此图表类型选项。',308:'同名文档是支持文档。\r\n图表不能作为支持文档。',310:'次要单位必须小于主要单位。',311:'最小值必须小于最大值。',312:'对数刻度单位至少为 10。',313:'找不到帮助程序。',343:'无法打开从属文档：其中引用了同名的不同工作表。',369:'现有分类将被永久删除。',390:'帮助号: |',392:'创建 Lotus 1-2-3 图形?',393:'内存不足，无法运行 Microsoft Excel。\r\n',401:'帮助引用无效。',406:'无法将 |0R x |1C 复制到 |2。',407:'数据库已隐藏。',408:'请更新 Windows/386 后运行 Microsoft Excel；详情请联系产品支持。',409:'不能在数据表单中输入公式。',528:'宏错误所在单元格:',529:'宏中断所在单元格:',530:'引用参数无效，位置:',552:'首列为分类&F',554:'首行为分类&F',599:'外部复制: ',607:'取消文档保护',616:'同名时省略列名&O',617:'同名时省略行名&O',628:"'|' 已受保护。",637:'新记录',646:'数值',647:'文本',648:'逻辑值',649:'引用',650:'错误值',651:'类型',652:'数组值',685:'(所有层级) ',703:'常规内存: |0 / |1 KB 可用',704:'    扩充内存: |0 / |1 KB 可用',705:'  数学协处理器: 有',706:'  数学协处理器: 无',707:'版本 2.1d',708:'1990年7月5日'}
W('patches/5.7/excel-string-translations.json',tr);proof={}
for video in ('CGA','VGA'):
 f=out/video/'XLCORE.EXE';raw=f.read_bytes();b=bytearray(raw);changes=[];seen=set()
 for kind in audit(f)['resource_kinds']:
  if kind['type']&32767!=6:continue
  for res in kind['resources']:
   at=res['start']
   for slot in range(16):
    n=raw[at];sid=((res['id']&32767)-1)*16+slot;old=raw[at+1:at+1+n];at+=n+1
    if sid not in tr:continue
    text=old.decode('gb2312');new=tr[sid];v=new.encode('gb2312');assert len(v)<=n,(sid,text,new,n,len(v));assert re.findall(r'\|\d?',text)==re.findall(r'\|\d?',new),(sid,text,new);assert text.count('\r\n')==new.count('\r\n'),sid
    assert [x.upper() for x in re.findall(r'&([^&])',text)]==[x.upper() for x in re.findall(r'&([^&])',new)],sid
    offset=at-n;b[offset:at]=v.ljust(n,b' ');seen.add(sid);changes.append(dict(string_id=sid,offset=offset,before_hex=old.hex().upper(),after_hex=bytes(b[offset:at]).hex().upper(),original=text,display=new,coverage='STATIC_DISPLAY_ONLY'))
 assert seen==set(tr),(video,set(tr)-seen)
 # About also uses one runtime NUL string instead of LoadString(707).
 old=b'Version 2.1d';hits=[m.start() for m in re.finditer(re.escape(old+b'\0'),raw)]
 for at in hits:
  v='版本 2.1d'.encode('gb2312').ljust(len(old),b' ');b[at:at+len(old)]=v;changes.append(dict(offset=at,before_hex=old.hex().upper(),after_hex=v.hex().upper(),original=old.decode(),display='版本 2.1d',coverage='STATIC_DISPLAY_ONLY'))
 f.write_bytes(b);back=bytearray(b)
 for c in reversed(changes):a=c['offset'];v=bytes.fromhex(c['before_hex']);back[a:a+len(v)]=v
 assert back==raw;proof[video]=dict(input_sha256=hashlib.sha256(raw).hexdigest().upper(),output_sha256=sha(f),changes=changes,reverse_restoration='PASS')
W('patches/5.7/excel-strings-r1.json',proof)
print('5.7-r1 assembled;',len(found),'Word templates;',sum(len(p['changes']) for p in proof.values()),'Excel physical display fields')
