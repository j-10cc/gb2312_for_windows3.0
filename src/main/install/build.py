"""Build the current Office and Windows DOS installers into test work/build."""
from pathlib import Path
import os,shutil,subprocess,sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'src/main').is_dir() and (p/'release').is_dir())
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'windows'))
from build_office_dos5 import build
from build_path_tool import main as build_windows

def main():
    build()
    build_windows()
    out=ROOT/'src/test/install/work/build/windows'
    shutil.copy2(HERE/'windows/GBTERM.C',out/'GBTERM.C')
    watcom=ROOT/'external/open-watcom';env=os.environ.copy()
    env.update(WATCOM=str(watcom),INCLUDE=str(watcom/'h'),LIB=str(watcom/'lib286/dos'))
    env['PATH']=str(watcom/'binnt64')+os.pathsep+env['PATH']
    result=subprocess.run([str(watcom/'binnt64/wcl.exe'),'-0','-bt=dos','-fe=GBTERM.EXE','GBTERM.C'],
                          cwd=out,env=env,capture_output=True,text=True)
    (out/'compile-term.log').write_text(result.stdout+result.stderr,'utf-8')
    print(result.stdout+result.stderr)
    result.check_returncode()

if __name__=='__main__':main()
