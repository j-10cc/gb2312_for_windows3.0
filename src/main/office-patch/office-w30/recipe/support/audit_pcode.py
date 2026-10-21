"""Audit historical OMF p-code procedure numbers against the module table."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

def index(data, at):
    n=data[at]; at+=1
    if n&128: n=((n&127)<<8)|data[at]; at+=1
    return n,at

def publics(path):
    data=path.read_bytes(); at=0; result={}
    while at+3<=len(data):
        kind=data[at]; size=struct.unpack_from('<H',data,at+1)[0]
        body=data[at+3:at+2+size]; at+=3+size
        if kind!=0x90: continue
        group,p=index(body,0); segment,p=index(body,p)
        if segment==0: p+=2
        while p<len(body):
            n=body[p]; p+=1
            name=body[p:p+n].decode('ascii'); p+=n
            value=struct.unpack_from('<H',body,p)[0]; p+=2
            _,p=index(body,p)
            if name.startswith('@') and segment==0: result[name]=value
    return result

def externs(path):
    data=path.read_bytes(); at=0; result=[]
    while at+3<=len(data):
        kind=data[at];size=struct.unpack_from('<H',data,at+1)[0]
        body=data[at+3:at+2+size];at+=3+size
        if kind!=0x8c:continue
        p=0
        while p<len(body):
            n=body[p];p+=1;result.append(body[p:p+n].decode('ascii'));p+=n
            _,p=index(body,p)
    return result

def audit(stage):
    opus=stage/'OPUS'
    modules=[x.strip().lower() for x in (opus/'PCODEMAP.TXT').read_text().splitlines() if x.strip()]
    linked=re.findall(r'([\w]+)\.obj',(opus/'OPUS.LNK').read_text(),re.I)
    mismatches=[]; checked=[]
    for name in linked:
        path=opus/(name.upper()+'.OBJ')
        if name.lower() not in modules: continue
        symbols=publics(path)
        if not symbols: continue
        counts=Counter(v>>8 for v in symbols.values())
        expected=modules.index(name.lower())
        row=dict(module=name.lower(),expected=expected,actual=dict(counts),procedures=len(symbols))
        checked.append(row)
        if set(counts)!={expected}: mismatches.append(row)
    return dict(modules=len(modules),checked=checked,mismatches=mismatches)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',type=Path);a=p.parse_args()
    r=audit(a.stage);print(json.dumps(r,indent=2))
