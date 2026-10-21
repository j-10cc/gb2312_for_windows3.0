"""Build DOS 5/8086 Office maintenance with the retained job record layout."""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]

from pathlib import Path
import os,shutil,subprocess

ROOT = _LAYOUT_ROOT
WORK=ROOT/'src/test/install/work/build'

def build(source=None,out=None):
    source=source or ROOT/'src/main/install/office'
    out=out or WORK/'compiler';out.mkdir(parents=True,exist_ok=True)
    for p in source.glob('*'):
        if p.suffix.lower() in ['.c','.h']:shutil.copy2(p,out/p.name)
    w=ROOT/'external/open-watcom';env=os.environ.copy()
    env.update(WATCOM=str(w),INCLUDE=str(w/'h'),LIB=str(w/'lib286/dos'))
    env['PATH']=str(w/'binnt64')+os.pathsep+env['PATH']
    r=subprocess.run([str(w/'binnt64/wcl.exe'),'-0','-bt=dos','-ml','-ot',
        '-k24576','-fe=INSTALL.EXE','install62.c'],cwd=out,env=env,capture_output=True,text=True)
    (out/'compile.log').write_text(r.stdout+r.stderr,'utf-8')
    assert r.returncode==0,r.stdout+r.stderr
    assert (out/'INSTALL.EXE').read_bytes()[:2]==b'MZ'
    print(r.stdout+r.stderr)

if __name__=='__main__':build()
