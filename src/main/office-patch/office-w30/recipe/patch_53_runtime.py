from pathlib import Path
import json,re,ast,hashlib,shutil
from audit_ne import audit
P=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest().upper()
names='''= expression|= 表达式
Ask|询
Author|作者
Auto No.|自动编号
Auto No. legal|法律编号
Auto No. outline|大纲编号
Comments|批注
Create date|创建日期
Data|数据
Date|日期
DDE|DDE
DDE Auto|自动 DDE
Edit time|编辑时间
File name|文件名
Fill-in|填写
Formulas|公式
Glossary|图文集
Goto Button|定位按钮
If|如
Import|导入
Include|包含
Index|索引
Index entry|索引项
Info|信息
Keywords|关键词
Last saved by|上次保存者
Macro Button|宏按钮
Merge rec.|合并记录
Next|下一
Next if|若下一
No. of chars|字符数
No. of pages|页数
No. of words|字数
Page|页码
Page ref.|页码引用
Print|打印
Print date|打印日期
Quote|引用
Reference|引用书签
Referenced doc.|引用文档
Rev. number|修订次数
Save date|保存日期
Sequence|序列
Set|设
Skip if|条件跳
Style ref.|样式引用
Subject|主题
TC|TC
Template|模板
Time|时间
Title|标题
TOC|TOC'''
names=dict(line.split('|',1) for line in names.splitlines())
helps='''Select format; then type numeric expression|先选格式，再输入数值表达式
Type bookmark name and text for prompt|输入书签名及提示文字
Choose OK to insert; type new name to change|选择确定插入，输入新名可更改
Choose OK to insert an automatic arabic number|选择确定插入自动阿拉伯数字
Choose OK to insert an automatic legal number|选择确定插入自动法律编号
Choose OK to insert an automatic outline number|选择确定插入自动大纲编号
Choose OK to insert; type new text to change|选择确定插入，输入新文字可更改
Choose OK to insert date document was created|选择确定插入文档创建日期
Type data file name [header-file] for merging|输入合并数据文件名及可选标题文件
Type or select desired date format|输入或选择日期格式
Type program name, file name; optional place|输入程序名、文件名及可选位置
Choose OK to insert the minutes of editing time|选择确定插入编辑时间分钟数
Choose OK to insert file name of document|选择确定插入文档文件名
Type text for prompt|输入提示文字
Select or type a command; type options and elements|选择或输入命令，再输入选项和元素
Type or select a glossary name|输入或选择图文集名称
Type Go To instruction and text for field's result|输入定位指令及域结果文字
Type condition, if-true text, and if-false text|输入条件、条件成立及不成立的文字
Type file name|输入文件名
Type file name; optional place reference|输入文件名及可选位置引用
Type or select index formatting switches|输入或选择索引格式开关
Type text of index entry and optional switches|输入索引项文字及可选开关
Type or select type of Summary Info|输入或选择摘要信息类型
Choose OK to insert name who last saved file|选择确定插入上次保存者姓名
Select or type macro name and text for field's result|选择或输入宏名称及域结果文字
Choose OK to insert merge record number|选择确定插入合并记录号
Choose OK to insert a NEXT print merge field|选择确定插入 NEXT 打印合并域
Type condition for when to merge next record|输入合并下一记录的条件
Choose OK to insert number of characters|选择确定插入字符数
Choose OK to insert number of pages|选择确定插入页数
Choose OK to insert number of words|选择确定插入字数
Type or select desired page number format|输入或选择页码格式
Type or select bookmark name for reference|输入或选择引用书签名
Type printer codes or PostScript code|输入打印机或 PostScript 代码
Select date format and choose OK|选择日期格式并确定
Type text you want as field's result|输入所需域结果文字
Type file name for table of contents or index|输入目录或索引的文件名
Choose OK to insert revision number|选择确定插入修订次数
Type switch or bookmark name|输入开关或书签名
Type bookmark name and associated data|输入书签名及相关数据
Type condition for when to skip a record|输入跳过记录的条件
Type or select style name or a number 1 to 9|输入或选择样式名或数字 1 至 9
Type text; optional switches for table id, TOC level|输入文字及表格标识、目录级别可选开关
Choose OK to insert name of document template|选择确定插入文档模板名称
Type or select desired time format|输入或选择时间格式
Choose OK to insert; type new title to change|选择确定插入，输入新标题可更改
Type or select optional switches|输入或选择可选开关'''
helps=dict(line.split('|',1) for line in helps.splitlines())
keys={
'NoteEndSec':'节末','NoteBottom':'页底','NoteBeneath':'正文下','NoteEndDoc':'文档末',
'PrintDoc':'文档','PrintSummary':'摘要信息','PrintAnnotations':'批注','PrintStyles':'样式','PrintGlsy':'图文集','PrintKeys':'快捷键分配',
'PrintBinManual':'手动','PrintBinEnvelope':'信封','PrintBinTractor':'连续纸','PrintBinAuto':'自动','PrintBin1':'纸盒1','PrintBin2':'纸盒2','PrintBin3':'纸盒3','PrintMixed':'混合',
'BrclNone':'无','BrclSingle':'单线','BrclThick':'粗线','BrclDouble':'双线',
'HtHeader':'页眉','HtFooter':'页脚','FirstHeader':'首页页眉','FirstFooter':'首页页脚','EvenHeader':'偶数页眉','EvenFooter':'偶数页脚','OddHeader':'奇数页眉','OddFooter':'奇数页脚',
'FootnoteSeparator':'脚注分隔符','FootnoteContSeparator':'续注分隔符','FootnoteContNotice':'续注提示',
'SecNoBreak':'连续','SecNewColumn':'新栏','SecNewPage':'新页','SecEvenPage':'偶数页','SecOddPage':'奇数页',
'PosLeft':'左','PosCenter':'居中','PosRight':'右','PosInside':'内侧','PosOutside':'外侧','PosInline':'嵌入','PosTop':'顶','PosBottom':'底'}
def patch(path):
 raw=path.read_bytes();b=bytearray(raw);ne=audit(path);rows=[];protected=[]
 mapping=(P/'build/word-advanced53-stage/OPUS/PROGRAM/WINWORD.MAP').read_text(encoding='latin1');modules={name.lower():int(n,16) for n,name in re.findall(r'^\s*([0-9A-F]+):0000\s+[0-9A-F]+H\s+(\w+)_PCODE',mapping,re.M)}
 def change(module,old,new,owner,stz=False):
  after=new.encode('gb2312');assert len(after)<=len(old)-(1 if stz else 0),(owner,old,new,len(after));seg=ne['segments'][modules[module]-1];token=bytes([len(old)])+old;hits=[seg['start']+m.start()+1 for m in re.finditer(re.escape(token),raw[seg['start']:seg['end']])];assert hits,(module,owner,old)
  for at in hits:
   data=after.ljust(len(old)-(1 if stz else 0),b' ')+(b'\0' if stz else b'')
   if b[at:at+len(old)]==data:continue
   assert b[at:at+len(old)]==old,(owner,at)
   b[at:at+len(old)]=data;rows.append({'offset':at,'before_hex':old.hex().upper(),'after_hex':data.hex().upper(),'original':old.rstrip(b'\0').decode('ascii'),'display':new,'owner':owner,'segment':seg['index']})
 for module in ('dlbenum','hddwin','dlglook2'):
  s=(P/f'snapshot/word-stage/CASHMERE/{module}.c').read_text(encoding='latin1')
  for literal,key in re.findall(r'St(?:Shared)?Key\(\s*("(?:\\.|[^"\\])*")\s*,\s*(\w+)\s*\)',s):
   if key in keys:change(module,ast.literal_eval('b'+literal),keys[key],module+':'+key)
 s=(P/'snapshot/word-stage/CASHMERE/insfield.h').read_text(encoding='latin1')
 for name,body in re.findall(r'#define (fd\w+Def)(.*?)(?=\n#define|\n/\*|\Z)',s,re.S):
  vals=[ast.literal_eval('b'+v) for v in re.findall(r'StShared\(("(?:\\.|[^"\\])*")\)',body)]
  if len(vals)!=3:continue
  display,syntax,help=vals;protected.append({'field':name,'syntax_hex':syntax.hex().upper()})
  # '= expression' aliases the syntax literal; keep that shared token intact.
  if display!=syntax and names[display[:-1].decode()]!=display[:-1].decode():change('insfield',display,names[display[:-1].decode()],name+':display',True)
  change('insfield',help,helps[help[:-1].decode()],name+':help',True)
 for c in protected:
  token=bytes.fromhex(c['syntax_hex']);seg=ne['segments'][modules['insfield']-1];assert bytes([len(token)])+token in b[seg['start']:seg['end']],c
 restored=bytearray(b)
 for c in reversed(rows):at=c['offset'];v=bytes.fromhex(c['before_hex']);restored[at:at+len(v)]=v
 assert bytes(restored)==raw
 return bytes(b),{'changes':rows,'protected_field_syntax':protected,'input_sha256':sha(raw),'output_sha256':sha(b),'reverse_restoration':'PASS','field_list_order_and_syntax_unchanged':True}
if __name__=='__main__':
 out=P/'release/5.3-r3';shutil.copytree(P/'release/5.3-r2',out,dirs_exist_ok=True);data,proof=patch(out/'WORD/WINWORD.EXE');(out/'WORD/WINWORD.EXE').write_bytes(data);(P/'patches/5.3/runtime-r3.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('5.3-r3',len(proof['changes']),'runtime display fields')
