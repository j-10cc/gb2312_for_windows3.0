"""Reapply the reviewed 5.2 UI patches after the display-only placeholder build."""
from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent
# The two existing assembly scripts are replayed with explicit fresh paths.
# This retains their preimage assertions and exact reverse-restoration checks.
s=(P/'build_52_r10.py').read_text(encoding='utf-8')
s=s.replace("out=P/'release/5.2-r10'","out=P/'release/5.2-r12'").replace("P/'release/5.2-r9'","P/'release/5.2-r11'").replace('word-macro-r10','word-placeholder-r12').replace('word-r10-chain.json','word-r12-chain.json')
exec(compile(s,str(P/'build_52_r10.py'),'exec'))
s=(P/'build_52_r11.py').read_text(encoding='utf-8').split('\nextra={')[0]
lines=s.splitlines();lines=[line for line in lines if not line.startswith("P=Path(__file__).resolve().parent;out=")];s='\n'.join(lines)
exec(compile(s,str(P/'build_52_r11.py'),'exec'))
(P/'patches/5.2/word-extra-r12.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
from audit_ne import audit
a,z=audit(P/'release/5.2-r11/WORD/WINWORD.EXE'),audit(out/'WORD/WINWORD.EXE')
changed=[x['index'] for x,y in zip(a['segments'],z['segments']) if x.get('payload_sha256')!=y.get('payload_sha256')];assert changed==[1,85],changed
assert a['segments'][-1]['payload_sha256']==z['segments'][-1]['payload_sha256']
(P/'patches/5.2/word-placeholder-r12.json').write_text(json.dumps({'scope':'Only the empty-template display in the statistics CAB uses a private Chinese string; global szNone and its printer/macro semantics unchanged.','changed_segments':changed,'DGROUP_payload_unchanged':True,'build_manifest':'build/5.2/word-placeholder-r12/manifest.json','patch_chain':'patches/5.2/word-r12-chain.json'},indent=2)+'\n');print('r12 private statistics placeholder complete')
