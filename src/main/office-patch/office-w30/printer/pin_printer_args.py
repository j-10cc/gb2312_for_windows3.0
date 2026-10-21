"""Preserve caller-owned device/port strings across the modal driver call."""
from pathlib import Path
import sys,struct,hashlib,json,subprocess
P=Path(__file__).resolve().parent;ROOT=next(p for p in P.parents if (p/'src/main').is_dir() and (p/'release').is_dir())
sys.path.insert(0,str(ROOT/'src/main/native-gb2312'))
from ne import NEModule,word
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def build():
 source=ROOT/'src/test/native-gb2312/work/build/GB2312-INSTALL/PAYLOAD/SYS/CEPSON.DRV'
 m=NEModule(source);b=bytearray(m.data)
 assert sha(b)=='BE51CBA461D9CBDE44CCABE4EE1AA480F2CC5952106B91A601BA95E55EEBD52D'
 base,size,flags=m.segment(2);code=bytearray(b[base:base+size]);assert size==11553
 assert code[0x47e:0x482]==bytes.fromhex('0ee833fc')
 assembly=['bits 16',f'org {size}',
  'db 0x1e,0x58,0x90,0x45,0x55,0x8b,0xec,0x1e,0x8e,0xd8','push si','push di']
 for name,offset in [('dev',22),('port',18)]:
  assembly += [f'cmp word [bp+{offset}],0',f'jz skip_lock_{name}',f'push word [bp+{offset}]',f'call_lock_{name}:','db 0x9a','dw 0xffff,0',f'skip_lock_{name}:']
 for offset in range(30,5,-2):assembly+=[f'push word [bp+{offset}]']
 assembly+=['push cs','call 0xb5','push ax']
 for name,offset in [('port',18),('dev',22)]:
  assembly += [f'cmp word [bp+{offset}],0',f'jz skip_unlock_{name}',f'push word [bp+{offset}]',f'call_unlock_{name}:','db 0x9a','dw 0xffff,0',f'skip_unlock_{name}:']
 assembly+=['pop ax','pop di','pop si','pop ds','pop bp','dec bp','retf 26']
 output=ROOT/'src/test/office-patch/work/printer';output.mkdir(parents=True,exist_ok=True)
 asm=output/'printer-args.asm';asm.write_text('\n'.join(assembly)+'\n')
 subprocess.run([str(ROOT/'external/nasm/nasm-2.16.03/nasm.exe'),'-f','bin','-o','printer-args.bin','printer-args.asm'],cwd=output,check=True)
 wrapper=(output/'printer-args.bin').read_bytes()
 assert wrapper[:10]==code[0xb5:0xbf]
 additions=[]
 sites=[i for i in range(len(wrapper)) if wrapper[i:i+5]==b'\x9a\xff\xff\0\0']
 assert len(sites)==4
 for i,site in enumerate(sites):additions.append(struct.pack('<BBHHH',3,1,size+site+1,1,23 if i<2 else 24))
 struct.pack_into('<h',code,0x480,size-0x482)
 count=word(b,base+size);old=bytes(b[base+size+2:base+size+2+count*8])
 b+=b'\0'*((-len(b))%(1<<m.shift));newbase=len(b)
 b+=code+wrapper+struct.pack('<H',count+4)+old+b''.join(additions)
 struct.pack_into('<HH',b,m.table+8,newbase>>m.shift,size+len(wrapper))
 struct.pack_into('<H',b,m.table+8+6,size+len(wrapper))
 e=m.ne+word(b,m.ne+4);end=e+word(b,m.ne+6);ordinal=1
 while e<end and b[e]:
  count,seg=b[e:e+2];e+=2
  for _ in range(count):
   if seg==255:
    if ordinal==90:
     assert b[e+3]==2 and word(b,e+4)==0xb5
     struct.pack_into('<H',b,e+4,size)
    e+=6
   elif seg:e+=3
   ordinal+=1
 (output/'CEPSON.DRV').write_bytes(b)
 report=dict(source_sha256=sha(m.data),output_sha256=sha(b),source_asm_sha256=sha(asm.read_bytes()),wrapper_bytes=len(wrapper),entry=90,segment=2,wrapper_offset=size,kernel_imports={'LockSegment':23,'UnlockSegment':24},relocation_sites=[size+i+1 for i in sites],bytes=len(b))
 (output/'printer-build.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
if __name__=='__main__':build()
