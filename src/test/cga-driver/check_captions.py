"""Prepare/run a disposable real-mode Program Manager caption fixture.

Requires user-owned media, the release ZIP and local Watcom/DOSBox-X.
No production installation or archive is changed. --run launches DOSBox-X.
"""
from pathlib import Path
import argparse, os, shutil, struct, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src/main/public-tools')]
from expand_szdd import expand, SIGNATURE

WORK = ROOT / 'src/test/cga-driver/work/captions'

def prepare():
    win = WORK / 'C/WINDOWS'
    system = win / 'SYSTEM'
    system.mkdir(parents=True, exist_ok=True)
    def unpack(d): return expand(d) if d.startswith(SIGNATURE) else d
    for p in (ROOT / 'external/media/windows/windows30a-tc').iterdir():
        if p.is_file():
            d = unpack(p.read_bytes())
            (win / p.name).write_bytes(d)
            (system / p.name).write_bytes(d)
    with zipfile.ZipFile(ROOT / 'release/W30SC21.ZIP') as z:
        for n in z.namelist():
            if '/' not in n:
                d = unpack(z.read(n))
                (win / n).write_bytes(d)
                (system / n).write_bytes(d)
        for n in z.namelist():
            if n.startswith('ZHRES/') and n.endswith('.CGA'):
                name=Path(n).stem + ('.DLL' if Path(n).stem == 'SHELL' else '.EXE')
                (win/name).write_bytes(z.read(n)); (system/name).write_bytes(z.read(n))
        fonts = ROOT / 'src/test/native-gb2312/work/build/fonts'
        fonts.mkdir(parents=True, exist_ok=True)
        for n in ('CHCGA12.FNT','CHCGA10.FNT','CHCGA08.FNT'):
            (fonts/n).write_bytes(z.read(n))
    # WIN.COM is the original real-mode loader plus English CGA logo code/data.
    media = ROOT / 'external/media/windows/windows30a'
    (win/'WIN.COM').write_bytes((win/'WIN.CNF').read_bytes() +
        unpack((media/'CGALOGO.LGO').read_bytes()) + unpack((media/'CGALOGO.RLE').read_bytes()))
    (win/'SYSTEM.INI').write_bytes(b'[boot]\r\nshell=CAPTURE.EXE\r\nsystem.drv=system.drv\r\nkeyboard.drv=keyboard.drv\r\nmouse.drv=mouse.drv\r\nnetwork.drv=\r\ncomm.drv=comm.drv\r\nsound.drv=sound.drv\r\nlanguage.dll=langeng.dll\r\ndisplay.drv=cga.drv\r\nfixedfon.fon=cgafix.fon\r\noemfonts.fon=cgaoem.fon\r\nfonts.fon=cgas12.fon\r\n')
    (win/'WIN.INI').write_bytes(b'[windows]\r\nNetWarn=0\r\n[Desktop]\r\nIconSpacing=100\r\n')
    for n in ('WIFERM.INI','WIFEMAN.INI'):
        (win/n).write_bytes(b'[CodeRanges]\r\nANSI=00(81,fe)\r\nSYMBOL=02(81,fe)\r\nOEM=ff(81,fe)\r\nCHINESEBIG5=88(81,fe)\r\n[FontDrivers]\r\nCWIN3=C:\\WINDOWS\\SYSTEM\\CFFONT.FOD\r\n[DefaultFont]\r\nFontDriver=C:\\WINDOWS\\SYSTEM\\CFFONT.FOD\r\nFontPackage=C:\\WINDOWS\\SYSTEM\\CFSUNG.FON\r\nBig5PartialTable=C:\\WINDOWS\\B5PART.TBL\r\n[OutlineHandTune]\r\nCFShouSung1=C:\\WINDOWS\\SYSTEM\\CFSUNG16.B5Q\r\nCFShouSung2=C:\\WINDOWS\\SYSTEM\\CFSUNG20.B5Q\r\n')
    data=bytearray((ROOT/'external/win31igdrv/WINDOWS/MAIN.GRP').read_bytes())
    count=struct.unpack_from('<H',data,32)[0]
    def append(s):
        at=len(data); data.extend(s.encode('gb2312')+b'\0'); return at
    labels=['剪贴板查看器','画图','游戏','附件','终端','文件管理器','控制面板','计算器']
    for i in range(count):
        at=struct.unpack_from('<H',data,34+2*i)[0]
        if not at: continue
        struct.pack_into('<hh',data,at,60+140*(i%4),60*(i//4))
        struct.pack_into('<H',data,at+18,append(labels[i]))
    struct.pack_into('<H',data,22,append('图标标题测试'))
    if len(data)%2:data.append(0)
    struct.pack_into('<H',data,6,len(data))
    struct.pack_into('<H4h',data,8,1,0,0,600,145)
    struct.pack_into('<H',data,4,0)
    struct.pack_into('<H',data,4,(-sum(struct.unpack('<'+'H'*(len(data)//2),data)))&65535)
    (win/'TEST.GRP').write_bytes(data)
    (win/'PROGMAN.INI').write_bytes(b'[Settings]\r\nWindow=0 0 640 200 3\r\n[Groups]\r\nGroup1=C:\\WINDOWS\\TEST.GRP\r\n')
    watcom=ROOT/'external/open-watcom'
    env=os.environ.copy();env.update(WATCOM=str(watcom),INCLUDE=str(watcom/'h')+';'+str(watcom/'h/win'),LIB=str(watcom/'lib286')+';'+str(watcom/'lib286/win'),PATH=str(watcom/'binnt64')+os.pathsep+env.get('PATH',''))
    subprocess.run([str(watcom/'binnt64/wcl.exe'),'-0','-bt=windows','-l=windows','-os','-fe=CAPTURE.EXE',str(Path(__file__).with_name('CAPTURE.C'))],cwd=win,env=env,check=True)
    (WORK/'C/RUN.BAT').write_bytes(b'@ECHO OFF\r\nPATH C:\\WINDOWS;C:\\WINDOWS\\SYSTEM\r\nCD \\WINDOWS\r\nWIN /R\r\nEXIT\r\n')

def run(driver, label, font=None):
    win=WORK/'C/WINDOWS'; c=WORK/'C'
    d=driver.read_bytes()
    for size in (12,10,8):
        old=f'C:\\WINDOWS\\SYSTEM\\CHCGA{size:02}.FNT'.encode().ljust(80,b'\0')
        # Reject unexpected path layouts before changing a test driver.
        assert d.count(old)==1, (driver,size)
    (win/'SYSTEM/CGA.DRV').write_bytes(d)
    (win/'CGA.DRV').write_bytes(d)
    if font is not None:
        for target in (win/'CGAS12.FON',win/'SYSTEM/CGAS12.FON'):
            target.write_bytes(font.read_bytes())
    for n in ('SCREEN.BIN','SCREEN2.BIN','METRICS.BIN','EXTENT.LOG'):
        if (c/n).exists():(c/n).unlink()
    conf='[sdl]\noutput=surface\n[dosbox]\nmachine=cga\nmemsize=1\n[cpu]\ncore=normal\ncputype=8086_prefetch\ncycles=max\nfpu=false\n[dos]\nxms=false\nems=false\numb=false\n[autoexec]\nmount c C\nVER SET 5 0\nc:\nRUN.BAT\n'
    (WORK/'run.conf').write_text(conf,'ascii')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen([str(ROOT/'external/dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe'),'-noconsole','-conf','run.conf'],cwd=WORK,startupinfo=startup,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    import time
    try:
        deadline=time.monotonic()+60
        while time.monotonic()<deadline and proc.poll() is None:
            if (c/'SCREEN2.BIN').exists() and (c/'SCREEN2.BIN').stat().st_size==16384:break
            time.sleep(.5)
    finally:
        if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
    for n in ('SCREEN.BIN','SCREEN2.BIN','METRICS.BIN','EXTENT.LOG'):
        if (c/n).exists():shutil.copy2(c/n,WORK/(label+'-'+n))
    assert (WORK/(label+'-SCREEN.BIN')).exists(), 'Windows fixture did not capture'
    assert (c/'SCREEN.BIN').read_bytes() != (c/'SCREEN2.BIN').read_bytes(), 'Program group did not minimize'
    sys.path.insert(0,str(ROOT/'external/pydeps'))
    from PIL import Image
    for suffix in ('','2'):
        raw=(WORK/(label+'-SCREEN'+suffix+'.BIN')).read_bytes()
        im=Image.new('RGB',(640,200))
        for y in range(200):
            for x in range(640):
                bit=raw[(y%2)*8192+(y//2)*80+x//8]&(128>>(x%8))
                im.putpixel((x,y),(255,255,255) if bit else (0,0,0))
        im.resize((1280,400)).save(WORK/(label+suffix+'.png'))
    print(WORK/(label+'.png'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--driver',type=Path);p.add_argument('--font',type=Path);p.add_argument('--label',default='capture');a=p.parse_args()
    if a.prepare:prepare()
    if a.driver:run(a.driver,a.label,a.font)
