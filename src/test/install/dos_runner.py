"""DOSBox command runner for current-install fixtures."""
from pathlib import Path
import subprocess
ROOT=next(p for p in Path(__file__).resolve().parents if (p/"src/main").is_dir() and (p/"release").is_dir())
DOSBOX=ROOT/"external/dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe"

def run(work,commands,label,version=5,cycles='max'):
    lines=[]
    for i,cmd in enumerate(commands):
        lines.append(cmd+f' > C:\\{label}{i}.LOG')
        for n in [90,30,20,2,1]:lines.append(f'IF ERRORLEVEL {n} GOTO X{i}R{n}')
        lines.extend([f'ECHO 0>C:\\{label}{i}.RC',f'GOTO NEXT{i}'])
        for n in [90,30,20,2,1]:lines.extend([f':X{i}R{n}',f'ECHO {n}>C:\\{label}{i}.RC',f'GOTO NEXT{i}'])
        lines.append(f':NEXT{i}')
    lines.append('EXIT')
    (work/'C/RUN.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode())
    strict=label in ['OLD5','DOS4','CPU5'] or (label=='PLAN5' and work.name=='CGA')
    cpu='core=normal\ncputype=8086_prefetch' if strict else 'core=dynamic\ncputype=386'
    conf=('[sdl]\noutput=surface\n[dosbox]\nmachine='+('cga' if work.name=='CGA' else 'svga_s3')+
        '\nmemsize=1\n[cpu]\n'+cpu+'\ncycles='+cycles+'\nfpu=false\n[dos]\n'
        'xms=false\nems=false\numb=false\nlfn=false\nfiles=60\nfloppy drive data rate limit=10000000\n'
        'hard drive data rate limit=10000000\n[autoexec]\nmount a A -freesize 128\nmount c C\nVER SET '+str(version)+' 0\nc:\nRUN.BAT\n')
    (work/(label+'.conf')).write_text(conf,'ascii')
    subprocess.run([str(DOSBOX),'-noconsole','-conf',label+'.conf'],cwd=work,
        timeout=240,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    rows=[]
    for i,cmd in enumerate(commands):
        rc=int((work/f'C/{label}{i}.RC').read_text().strip())
        log=(work/f'C/{label}{i}.LOG').read_text('ascii',errors='replace')
        rows.append({'command':cmd,'rc':rc,'log':log})
    print(label,[(r['rc'],r['log'][-160:]) for r in rows],flush=True)
    return rows

