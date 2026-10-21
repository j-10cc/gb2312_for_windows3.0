"""Verify the two final installation archives without development fixtures."""

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import hashlib,json,re,zipfile

from pathlib import Path

ROOT = _LAYOUT_ROOT

FINAL=ROOT/'release'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        data = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(data.pop('MANIFEST.JSN'))
    assert set(data) == set(manifest['files'])
    for name, row in manifest['files'].items():
        assert sha(data[name]).lower() == row['sha256'].lower(), name
    return data

def verify():
    meta = json.loads((ROOT/'src/test/install/fixtures/release/manifest.json').read_text('utf-8'))
    packages = {}
    for name,row in meta['packages'].items():
        archive = FINAL/name
        assert sha(archive.read_bytes()) == row['sha256']
        assert (ROOT/'src/test/install/fixtures/release'/(archive.stem+'.sha256')).read_text().split()[0] == row['sha256']
        data = load_zip(archive)
        for n in data:
            assert all(re.fullmatch(r'[A-Z0-9_-]{1,8}(\.[A-Z0-9_-]{1,3})?',c) for c in n.split('/')), n
        for n in ['GUIDE.TXT', 'PY21DOC/GUIDE.TXT']:
            text = data[n].decode('gb2312')
            assert '\r\r\n' not in text
            assert '\n' not in text.replace('\r\n','')
        packages[archive.stem] = data
    w,o = packages['W30SC21'], packages['GB30SC21']
    for name in ['PHON.IME','GBPY.DAT','WINNLS.DLL','IMEINFO.INI']:
        assert w[name] == o['DEPEND/IME/'+name]
    assert sha(w['PHON.IME']) == meta['runtime_ime_sha256']
    assert sha(w['GBPY.DAT']) == meta['dictionary_sha256']
    for name,value in meta['terminology_modules'].items():
        assert sha(w[('ZHRES/' if 'terminology_stage' in meta else '')+name]) == value
    assert o['INSTALL.EXE'] == o['REMOVE.EXE'] == o['RECOVER.EXE']
    assert sha(o['INSTALL.EXE']) == meta['installer_sha256']
    if 'office_dos5_fix' in meta:
        if 'installer_no_checks' not in meta:
            assert b'DOS 5.0 or later required' in o['INSTALL.EXE']
        latest=meta.get('installer_no_checks',meta.get('office_crc_fix',meta.get('office_progress_fix',meta['office_dos5_fix'])))
        assert latest['current_installer_sha256'] == sha(o['INSTALL.EXE'])
    if 'office_progress_fix' in meta and 'office_crc_fix' not in meta:
        assert b'GB Office installer DOS5-R2' in o['INSTALL.EXE']
        assert b'bytes processed' in o['INSTALL.EXE']
    if 'office_crc_fix' in meta and 'installer_no_checks' not in meta:
        assert b'GB Office installer DOS5-R3' in o['INSTALL.EXE']
        assert b'CRC32+SIZE' in o['INSTALL.EXE']
        assert b'SHA-256' not in o['INSTALL.EXE']
    if 'installer_no_checks' in meta:
        assert b'DOS5-R4 (8086, direct copy)' in o['INSTALL.EXE']
        assert all(s not in o['INSTALL.EXE'] for s in [b'CRC32',b'SHA-256',b'HASH CONFLICT'])
    inf = w['SETUP.INF'].decode('gb2312')
    for term in ['控制面板', '写字板', '计算器', '附件', '游戏']: assert term in inf
    for term in ['控制台', '小作家', '小算盘', '游乐场']: assert term not in inf
    for name in ['INSTALL.BAT', 'FINALIZE.BAT']:
        assert b'GBPATH LAYOUT %1 %2' in w[name]
        assert b'COPY PY21DOC\\*.*' in w[name]
        for sidecar in ['CONTROL.TRM','PIFEDIT.TRM','USERFONT.TRM']: assert sidecar.encode() in w[name]
        if 'hp200lx_fix' in meta:
            for bank in ['CHCGA12.FNT','CHCGA10.FNT','CHCGA08.FNT']:
                assert ('COPY '+bank+' %2\\SYSTEM').encode() in w[name]
            if 'installer_no_checks' in meta:
                assert b'GBPATH CGAOK' not in w[name]
            else:
                assert b'GBPATH CGAOK %2' in w[name]
            assert b'ECHO [1/7]' in w[name]
            assert b'IF "%2"=="" GOTO USAGE' in w[name]
    if 'hp200lx_fix' in meta:
        assert b'WIN /R' in w['WINR.BAT']
        expected=meta['installer_no_checks']['gbpath_sha256'] if 'installer_no_checks' in meta else meta['hp200lx_fix']['new_gbpath_sha256']
        assert expected == sha(w['GBPATH.EXE'])
    print('PASS: ZIP CRC, all member SHA-256, DOS 8.3, GB2312/CRLF manuals, terminology, matched Pinyin 2.1.')

if __name__=='__main__': verify()
