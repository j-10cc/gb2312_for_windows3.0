from pathlib import Path
import json
from patch_53_runtime import patch as runtime
from patch_word_messages52 import patch as messages
P=Path(__file__).resolve().parent;s=(P/'build_53_r2.py').read_text(encoding='utf-8').replace('release/5.3-r2','release/5.3-r5').replace('word-layout-r2','word-layout-r5').replace('word-parent52-r2','word-parent52-r5').replace('word-parent52-extra-r2','word-parent52-extra-r5').replace('word-sdm-r2.json','word-sdm-r5.json');exec(compile(s,str(P/'build_53_r2.py'),'exec'))
path=P/'release/5.3-r5/WORD/WINWORD.EXE';b,r=runtime(path);path.write_bytes(b);(P/'patches/5.3/runtime-r5.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');b,r=messages(path,'patches/5.3/word-message-translations.json');path.write_bytes(b);(P/'patches/5.3/messages-r5.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('5.3-r5 Section two columns; other templates retain r4 layout')
