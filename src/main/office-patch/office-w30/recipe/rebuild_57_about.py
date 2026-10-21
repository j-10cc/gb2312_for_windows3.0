from pathlib import Path
import sys,shutil
P=Path(__file__).resolve().parent;stage=P/'build/word-final57-stage'
f=stage/'CASHMERE/help.c';s=f.read_text('latin1')
def lit(t):return ''.join('\\%03o'%b for b in t.encode('gb2312'))
old='SzToSt(szNone, st);';assert s.count(old)==1;s=s.replace(old,'SzToSt(SzShared("'+lit('无')+'"), st);')
old='FSetCabSz(pcmb->hcab, f8087 ? SzSharedKey("Present", Present) : \n\t\t\t\tszNone, Iag(CABABOUT, hszAboutMath));';assert s.count(old)==1;s=s.replace(old,'FSetCabSz(pcmb->hcab, f8087 ? SzSharedKey("'+lit('有')+'", Present) :\n\t\t\t\tSzShared("'+lit('无')+'"), Iag(CABABOUT, hszAboutMath));')
f.write_text(s,encoding='latin1');shutil.copy2(f,P/'patches/5.7/help-about-r1.c')
sys.path.insert(0,str(P/'support'));import rebuild_table_candidate as b
b.HERE=P/'build/5.7';b.SOURCE=P/'build/word-advanced53-stage';b.STAGE=stage;b.MODULES=('help',)
sys.argv=[sys.argv[0],'--resume','--output',str(P/'build/5.7/word-system-r1')];b.main()
