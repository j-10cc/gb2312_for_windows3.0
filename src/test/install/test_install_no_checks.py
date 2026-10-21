"""Focused current-install checks; no old-version recovery scenarios."""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]

from pathlib import Path
import json, re, shutil, zipfile, struct
from expand_szdd import expand, SIGNATURE
from dos_runner import run

ROOT = _LAYOUT_ROOT
WORK=ROOT/'src/test/install/work/no-checks'

def fixture(video):
    work=WORK/video
    (work/'A/WINDOWS/SYSTEM').mkdir(parents=True)
    (work/'C').mkdir()
    win=work/'A/WINDOWS'
    with zipfile.ZipFile(ROOT/'release/W30SC21.ZIP') as z:
        z.extractall(work/'A/W30')
        for name in z.namelist():
            if '/' in name or name=='MANIFEST.JSN':continue
            data=z.read(name)
            if data.startswith(SIGNATURE):data=expand(data)
            (win/name).write_bytes(data)
            if Path(name).suffix.upper() in ['.EXE','.DLL','.DRV','.FON','.GR2','.GR3','.386','.IME']:
                (win/'SYSTEM'/name).write_bytes(data)
    for name in ['GBPATH.EXE','GBTERM.EXE']:
        shutil.copy2(ROOT/'src/test/install/work/build/windows'/name,work/'A/W30'/name)
    with zipfile.ZipFile(ROOT/'release/GB30SC21.ZIP') as z:z.extractall(work/'A/OFFPK')
    for name in ['INSTALL.EXE','REMOVE.EXE','RECOVER.EXE']:
        shutil.copy2(ROOT/'src/test/install/work/build/compiler/INSTALL.EXE',work/'A/OFFPK'/name)
    prefix='cga' if video=='CGA' else 'vga'
    (win/'SYSTEM.INI').write_bytes(('[boot]\r\nshell=progman.exe\r\nsystem.drv=system.drv\r\nkeyboard.drv=keyboard.drv\r\n'
        'display.drv='+('cga' if video=='CGA' else 'cvga')+'.drv\r\nfixedfon.fon='+prefix+'fix.fon\r\noemfonts.fon='+prefix+'oem.fon\r\nfonts.fon='+('cgas12' if video=='CGA' else 'vgasys')+'.fon\r\n').encode())
    (win/'WIN.INI').write_bytes(b'[windows]\r\nNetWarn=1\r\n')
    for name in ['WIFEMAN.INI','WIFERM.INI']:
        (win/name).write_bytes(b'[FontDrivers]\r\n[DefaultFont]\r\n[OutlineHandTune]\r\n')
    (win/'PROGMAN.INI').write_bytes(b'[Settings]\r\nWindow=0 0 640 200 3              \r\n[Groups]\r\n')
    for name in ['CMAIN.GRP','CACCESOR.GRP','CGAMES.GRP']:
        data=bytearray(48);data[:4]=b'PMCC'
        struct.pack_into('<H',data,6,len(data));struct.pack_into('<H',data,22,34)
        data[34:39]=b'Main\0'
        struct.pack_into('<H',data,4,(-sum(struct.unpack('<24H',data)))&65535)
        (win/name).write_bytes(data)
    office=work/'A/OFFICE';office.mkdir();(office/'USER.DOC').write_bytes(b'USER DOCUMENT')
    return work

def test(video):
    work=fixture(video);win=work/'A/WINDOWS';office=work/'A/OFFICE'
    # Current Windows MEDIA path update and actual FINALIZE batch.
    before=(win/'SYSTEM/SHELL.DLL').read_bytes()[6048:6144]
    result=run(work,['A:','CD \\W30',f'GBPATH MEDIA {video} A:\\NEW',
        f'CALL FINALIZE {video} A:\\WINDOWS'],'CPU5',cycles='max')
    assert all(row['rc']==0 for row in result),result
    assert all((win/n).exists() for n in ['GBPCH.OK','GBWIF.OK','GBLAY.OK'])
    assert (win/'SYSTEM/SHELL.DLL').read_bytes()[6048:6144]==before
    assert (win/'PHON.IME').read_bytes()[9750:9830]==b'A:\\WINDOWS\\GBPY.DAT'.ljust(80,b'\0')
    assert (win/'SYSTEM/PHON.IME').read_bytes()==(win/'PHON.IME').read_bytes()
    if video=='CGA':
        assert (win/'SYSTEM/CGA.DRV').read_bytes()[9194:9274]==b'A:\\WINDOWS\\SYSTEM\\CHCGA12.FNT'.ljust(80,b'\0')
        for n in ['CHCGA12.FNT','CHCGA10.FNT','CHCGA08.FNT']:
            assert (win/'SYSTEM'/n).read_bytes()==(work/'A/W30'/n).read_bytes()
    # Office uses the user's exact command, no preflight/CANCEL or legacy tests.
    result=run(work,[f'A:\\OFFPK\\INSTALL {video} A:\\OFFICE A:\\WINDOWS PROVISION'],'CPU5',cycles='max')
    assert result[0]['rc']==0 and 'INSTALL FINISHED' in result[0]['log'],result
    assert all(word not in result[0]['log'] for word in ['SHA','CRC','HASH','VERIFIED','BIOS video'])
    for n,rel in [('WINWORD.EXE','WORD/WINWORD.EXE'),('EXCEL.EXE',video+'/EXCEL.EXE'),('XLCORE.EXE',video+'/XLCORE.EXE')]:
        assert (office/n).read_bytes()==(work/'A/OFFPK/APP'/rel).read_bytes()
    assert (office/'USER.DOC').read_bytes()==b'USER DOCUMENT'
    # Office's patched CGA driver has a different build position from Windows'.
    if video=='CGA':assert (win/'SYSTEM/CGA.DRV').read_bytes()[9276:9356]==b'A:\\WINDOWS\\SYSTEM\\CHCGA12.FNT'.ljust(80,b'\0')
    assert (win/'COFFICE.GRP').read_bytes().startswith(b'PMCC')
    assert b'COFFICE.GRP' in (win/'PROGMAN.INI').read_bytes()
    assert b'A:\\WINDOWS\\SYSTEM\\CFFONT.FOD' in (win/'WIFEMAN.INI').read_bytes().upper()
    tx=(office/'GB30TX/CURRENT').read_text();folder=office/'GB30TX'/tx
    assert (folder/'COMMIT.TAG').exists()
    assert not list(folder.glob('*.CRC')) and not list(folder.glob('*.SHA'))
    assert not (folder/'P0000.PST').exists()
    for p in [ROOT/'src/test/install/work/build/compiler/INSTALL.EXE',WORK/'windows/GBPATH.EXE',WORK/'windows/GBTERM.EXE']:
        assert all(x not in p.read_bytes() for x in [b'CRC32+SIZE',b'SHA-256',b'checksum conflict',b'Scanning input'])
    return {'video':video,'status':'PASS','dos':'DOSBox-X DOS API 5.0; strict 8086; no FPU/XMS/EMS/UMB/LFN',
        'scope':'Current Windows path update and FINALIZE on prepared Setup fixture; current Office install, exact copied apps and required configuration.',
        'excluded':'No full graphical Windows Setup, real HP200LX test, old-version recovery or performance benchmark.'}

if __name__=='__main__':
    results={'status':'PASS','tests':[test('CGA'),test('VGA')]}
    (WORK/'results.json').write_text(json.dumps(results,indent=2)+'\n','utf-8')
    print(json.dumps(results,indent=2),flush=True)
