"""Publish only current installer changes and matching guides to both final ZIPs."""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]

from pathlib import Path
import hashlib,json,zipfile
from package_io import read_package

ROOT = _LAYOUT_ROOT
WORK=ROOT/'src/test/install/work/no-checks'
FINAL=ROOT/'release'
def sha(b):return hashlib.sha256(b).hexdigest()
def dos(p):return p.read_text('utf-8').replace('\r\n','\n').replace('\n','\r\n').encode('gb2312')

def publish():
    results=json.loads((WORK/'results.json').read_text('utf-8'))
    assert results['status']=='PASS'
    exe=(ROOT/'src/test/install/work/build/compiler/INSTALL.EXE').read_bytes()
    assert b'DOS5-R4' in exe and all(x not in exe for x in [b'CRC32',b'SHA-256',b'HASH CONFLICT'])
    compile_log=(ROOT/'src/test/install/work/build/compiler/compile.log').read_text('utf-8')
    assert '0 warnings, 0 errors' in compile_log
    meta=json.loads((ROOT/'src/test/install/fixtures/release/manifest.json').read_text('utf-8'))
    previous=dict(meta['packages']);changes={};outputs={}
    for stem in ['W30SC21','GB30SC21']:
        old=read_package(FINAL/(stem+'.ZIP'));data=dict(old)
        data['GUIDE.TXT']=dos(ROOT/'docs/manual/安装手册.md')
        if stem=='W30SC21':
            for n in ['GBPATH.EXE','GBTERM.EXE']:
                data[n]=(ROOT/'src/test/install/work/build/windows'/n).read_bytes()
            for n in ['INSTALL.BAT','FINALIZE.BAT']:
                data[n]=(ROOT/'src/main/install/windows'/n).read_bytes()
            allowed={'GUIDE.TXT','GBPATH.EXE','GBTERM.EXE','INSTALL.BAT','FINALIZE.BAT'}
        else:
            data['GUIDE.TXT']+=b'\r\n\r\n'+dos(ROOT/'docs/manual/Word和Excel使用手册.md')
            for n in ['INSTALL.EXE','REMOVE.EXE','RECOVER.EXE']:data[n]=exe
            allowed={'GUIDE.TXT','INSTALL.EXE','REMOVE.EXE','RECOVER.EXE'}
        delta={n for n in data if data[n]!=old.get(n)}
        assert delta<=allowed,delta
        changes[stem]=sorted(delta)
        with zipfile.ZipFile(FINAL/(stem+'.ZIP')) as z:manifest=json.loads(z.read('MANIFEST.JSN'))
        manifest['revision']='HP200LX-R3' if stem=='W30SC21' else 'DOS5-R4'
        manifest['office_installer_revision']='DOS5-R4'
        manifest['runtime_checksum']='none'
        if stem=='GB30SC21':manifest['minimum_dos']='5.0'
        manifest['files']={n:{'bytes':len(b),'sha256':sha(b)} for n,b in sorted(data.items())}
        out=WORK/(stem+'.ZIP')
        with zipfile.ZipFile(out,'w') as z:
            for n,b in sorted({**data,'MANIFEST.JSN':(json.dumps(manifest,indent=2)+'\n').encode()}.items()):
                z.writestr(zipfile.ZipInfo(n,(2026,10,20,0,0,0)),b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        assert read_package(out)==data
        outputs[stem]=out
    for stem,out in outputs.items():
        dest=FINAL/(stem+'.ZIP');out.replace(dest)
        digest=sha(dest.read_bytes())
        (ROOT/'src/test/install/fixtures/release'/(stem+'.sha256')).write_text(digest+'  '+dest.name+'\n','ascii')
        with zipfile.ZipFile(dest) as z:n=len(z.namelist())
        meta['packages'][dest.name]={'sha256':digest,'bytes':dest.stat().st_size,'files':n}
    meta['installer_sha256']=sha(exe)
    meta['office_crc_fix']['superseded_by']='DOS5-R4; CRC checks apply to historical R3 only.'
    meta['installer_no_checks']={
        'date':'2026-10-20','windows_revision':'HP200LX-R3','office_revision':'DOS5-R4',
        'runtime_checksums':'none; no SHA, CRC, file-length fingerprint or content comparison passes',
        'windows_changes':'Fixed IME/driver path offsets; no font-bank validation, group checksum verification, media inventory or SHELL byte comparison.',
        'office_changes':'Copy selected files from media to targets once; edit required INI/group configuration. Existing-file backups retained; no payload postimage copies or verification rereads.',
        'current_installer_sha256':sha(exe),
        'gbpath_sha256':sha((ROOT/'src/test/install/work/build/windows/GBPATH.EXE').read_bytes()),
        'gbterm_sha256':sha((ROOT/'src/test/install/work/build/windows/GBTERM.EXE').read_bytes()),
        'previous_packages':previous,'changes':changes,'verification':results,
        'source_sha256':{p.name:sha(p.read_bytes()) for p in sorted((ROOT/'src/main/install/office').iterdir()) if p.suffix in ['.c','.h']},
        'windows_source_sha256':{p.name:sha(p.read_bytes()) for p in sorted((ROOT/'src/main/install/windows').iterdir()) if p.suffix.lower() in ['.c','.bat']},
        'build':'Open Watcom, 8086 DOS targets; zero compiler warnings/errors.',
        'unchanged':'Windows/Office application payloads, fonts, Pinyin 2.1, and all Windows 2.x files.'}
    (ROOT/'src/test/install/fixtures/release/manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(meta['packages'],indent=2))

if __name__=='__main__':publish()
