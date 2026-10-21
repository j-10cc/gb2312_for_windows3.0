"""Assemble 5.2 display patches on the incrementally compiled 5.3 layout."""
from pathlib import Path
import json,shutil
from patch_word_sdm52 import patch
P=Path(__file__).resolve().parent
s=(P/'build_52_r12.py').read_text(encoding='utf-8')
# Replay the checked assembler while leaving frozen 5.2 outputs untouched.
s=s[:s.index('\nfrom audit_ne import audit')]
s=s.replace(".replace('word-macro-r10','word-placeholder-r12')", ".replace('word-macro-r10','../5.3/word-layout-r2')")
s=s.replace("out=P/'release/5.2-r12'", "out=P/'release/5.3-r2'")
s=s.replace("'word-r12-chain.json'","'../5.3/word-parent52-r2-chain.json'")
s=s.replace("patches/5.2/word-extra-r12.json","patches/5.3/word-parent52-extra-r2.json")
exec(compile(s,str(P/'build_52_r12.py'),'exec'))
b,proof=patch(out/'WORD/WINWORD.EXE','inventory/dialog-owner-census-5.3.json','patches/5.3/word-dialog-translations.json');(out/'WORD/WINWORD.EXE').write_bytes(b)
# r12 assembler carried Excel r11; retain the accepted latest r15 Excel variants.
for video in ('CGA','VGA'):shutil.copytree(P/f'release/5.2-r15/{video}',out/video,dirs_exist_ok=True)
(P/'patches/5.3/word-sdm-r2.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('5.3-r2 assembled')
