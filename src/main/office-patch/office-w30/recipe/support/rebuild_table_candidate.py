"""Recompile the table dependency modules against the current p-code map.

The historical snapshot is retained. Only the table, preview, print, error,
selection replacement and page window modules are rebuilt from source here.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from audit_pcode import audit, externs

HERE=Path(__file__).resolve().parent
OFFICE=HERE.parents[1]
ROOT=next(p for p in HERE.parents if (p/'src/main').is_dir() and (p/'release').is_dir())
SOURCE=ROOT/'external/word11a-current'
STAGE=ROOT/'src/test/office-patch/work/word-table-stage'
MODULES=('dlgtable','outwin','prvw2','error','dispbrc','print1','replace')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def dos(config):
    subprocess.run([str(ROOT/'external/dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe'),
                    '-noconsole','-conf',config],cwd=STAGE,check=True,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=300)

def main():
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');p.add_argument('--native-only',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'src/test/office-patch/work/word-linked');args=p.parse_args()
    if not args.resume:
        if STAGE.exists():raise FileExistsError(STAGE)
        shutil.copytree(SOURCE,STAGE)
    if args.native_only and not args.resume:raise ValueError('--native-only requires the existing compiled stage')
    from patch_print import apply
    apply(STAGE)
    before=audit(SOURCE)
    prefix=(STAGE/'dlglook1-zh.conf').read_text('ascii').split('cd \\OPUS')[0]+'cd \\OPUS\n'
    commands=[]
    for name in (() if args.native_only else MODULES):
        source=next((STAGE/'CASHMERE').rglob(name+'.c'))
        dospath='C:\\'+str(source.relative_to(STAGE)).replace('/','\\')
        (STAGE/'OPUS'/(name+'.obj')).unlink(missing_ok=True)
        commands += [f'csl -nb -r -p -Q -mW -DPCODE -DWIN23 -DCRLF -DWIN -DFAST -Z. {dospath} > {name}.log',
                     f'im2obj -r -c -p -T@13 {name}']
    commands += ['masm -Mx -DWIN23 C:\\CASHMERE\\asm\\disp1n.asm; > DASM41.LOG',
                 'masm -Mx -DWIN23 C:\\CASHMERE\\asm\\formatn2.asm; > FNTASM41.LOG',
                 'link5 @opus.lnk > LINK41.LOG','exit']
    for name in ('disp1n.obj','formatn2.obj'):(STAGE/'OPUS'/name).unlink(missing_ok=True)
    (STAGE/'table41.conf').write_text(prefix+'\n'.join(commands)+'\n',encoding='ascii')
    linked=STAGE/'OPUS/PROGRAM/WINWORD.EXE'
    if linked.exists():linked.unlink()
    dos('table41.conf')
    for name in MODULES:
        log=(STAGE/'OPUS'/(name+'.log')).read_text('latin1')
        if 'error:' in log.lower():raise RuntimeError((name,log))
    log=(STAGE/'OPUS/LINK41.LOG').read_text('latin1')
    asm_log=(STAGE/'OPUS/DASM41.LOG').read_text('latin1')
    if not re.search(r'^\s*0 Severe\s+Errors\s*$',asm_log,re.M):raise RuntimeError(asm_log)
    asm_log=(STAGE/'OPUS/FNTASM41.LOG').read_text('latin1')
    if not re.search(r'^\s*0 Severe\s+Errors\s*$',asm_log,re.M):raise RuntimeError(asm_log)
    if not linked.exists() or 'error' in log.lower():raise RuntimeError(log)
    after=audit(STAGE)
    assert not [row for row in after['mismatches'] if row['module'] in MODULES]
    maps=[x.strip()+'_q' for x in (STAGE/'OPUS/PCODEMAP.TXT').read_text().splitlines() if x.strip()]
    assert externs(STAGE/'OPUS/PCODEMAP.OBJ')==maps
    program=linked.parent
    shutil.copy2(linked,program/'WINTEST.EXE')
    subprocess.run([str(ROOT/'external/open-watcom/binnt64/wrc.exe'),'-s0','-20','-bt=windows',
        str(STAGE/'OPUS/WINWORD.RES'),str(program/'WINTEST.EXE')],check=True)
    if (program/'WINTESTM.EXE').exists():(program/'WINTESTM.EXE').unlink()
    dos('wrcpost.conf')
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from build_word_release import fixed_ui
    data=bytearray((program/'WINTESTM.EXE').read_bytes());ne=struct.unpack_from('<I',data,0x3c)[0]
    assert data[ne:ne+2]==b'NE'
    struct.pack_into('<H',data,ne+12,0x0812);struct.pack_into('<H',data,ne+62,0x0203)
    data,changes=fixed_ui(bytes(data))
    release=args.output;release.mkdir(exist_ok=True)
    if (release/'WINWORD.EXE').exists():
        archive=HERE/'diagnostics/candidates'/sha(release/'WINWORD.EXE')
        archive.mkdir(parents=True,exist_ok=True)
        for name in ('WINWORD.EXE','manifest.json'):
            if (release/name).exists():shutil.copy2(release/name,archive/name)
    (release/'WINWORD.EXE').write_bytes(data)
    manifest=dict(input_sha256=sha(OFFICE/'phase6/release/WORD/WINWORD.EXE'),
        output_sha256=sha(release/'WINWORD.EXE'),map_sha256=sha(STAGE/'OPUS/PCODEMAP.TXT'),
        rebuilt={name:dict(source_sha256=sha(next((STAGE/'CASHMERE').rglob(name+'.c'))),
            prior_object_sha256=sha(SOURCE/'OPUS'/(name+'.obj')),
            object_sha256=sha(STAGE/'OPUS'/(name+'.obj'))) for name in MODULES},
        before_mismatches=before['mismatches'],remaining_mismatches=after['mismatches'],
        fixed_ui_fields=len(changes),stage=str(STAGE),
        accepted_parent_sha256='FF61376D95F7F3DB8758A859D44F5082E09E07ED4B316C5E818BAAFBB7EBF493',
        native_draw_source_sha256=sha(STAGE/'CASHMERE/asm/disp1n.asm'),
        native_font_source_sha256=sha(STAGE/'CASHMERE/asm/formatn2.asm'))
    (release/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (HERE/'table-pcode-audit.json').write_text(json.dumps(after,indent=2)+'\n')
    print(json.dumps(dict(output_sha256=manifest['output_sha256'],rebuilt=MODULES,
                         remaining_mismatches=len(after['mismatches']))))

if __name__=='__main__':main()
