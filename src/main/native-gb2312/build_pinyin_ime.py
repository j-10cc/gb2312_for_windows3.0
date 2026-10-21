"""Build the native Win16 Pinyin IME and its GB2312 dictionary."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import os
import argparse
import re
import subprocess
import sys
import json
import hashlib
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = _LAYOUT_ROOT
WATCOM = ROOT / "external/open-watcom"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/ime"  # Existing INI template only; do not rewrite it.
sys.path.insert(0, str(ROOT / "src/main/public-tools"))
from build_gb2312_pinyin import build as build_dictionary  # noqa: E402
from patch_winnls_ctrlspace import build as patch_winnls  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--stack-bytes", type=int, choices=(2048, 4096, 8192), default=2048)
    parser.add_argument("--output", type=Path, default=_LAYOUT_ROOT / "src/test/native-gb2312/work/build/pinyin21",
                        help="separate build directory; frozen Office releases are never rewritten")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / ("diagnostics/PHON.IME" if args.diagnostics else "PHON.IME")
    target.parent.mkdir(parents=True, exist_ok=True)
    keys, coverage, size = build_dictionary(output / "GBPY.DAT", phrases=True)
    if not 400 <= keys <= 500 or coverage < 6500 or size > 0x7FFFFFFF:
        raise ValueError("Pinyin dictionary layout changed")
    env = os.environ.copy()
    env.update({
        "WATCOM": str(WATCOM),
        "INCLUDE": ";".join((str(WATCOM / "h"), str(WATCOM / "h/win"))),
        "LIB": ";".join((str(WATCOM / "lib286"), str(WATCOM / "lib286/win"))),
        "PATH": str(WATCOM / "binnt64") + os.pathsep + env.get("PATH", ""),
    })
    command = [str(WATCOM / "binnt64/wcc.exe"), "-0", "-bt=windows", "-os"]
    if args.diagnostics:
        command.append("-dPINYIN_DIAGNOSTICS")
    subprocess.run(command + ["PINYIN_NATIVE.C"], cwd=HERE, env=env, check=True)
    subprocess.run([str(WATCOM / "binnt64/wlink.exe"), "system", "windows",
                    "name", str(target), "file", "PINYIN_NATIVE.obj",
                    "export", "DLGPROC.1=PinyinDlgProc", "export",
                    "IMEWNDPROC.2", "option", "modname=PHON",
                    "option", f"stack={args.stack_bytes}", "option", "heapsize=256"],
                   cwd=HERE, env=env, check=True)
    report = subprocess.run([str(WATCOM / "binnt64/wdump.exe"), "-q", "-e",
                             str(target)], cwd=HERE, env=env,
                            check=True, capture_output=True, text=True).stdout
    for number, name in ((1, "DLGPROC"), (2, "IMEWNDPROC")):
        if not re.search(rf"^\s*{number}: {name}\.\d+ seg ", report, re.M):
            raise ValueError(f"missing PHON.IME export {number}: {name}")
    ini = (OUT / "IMEINFO.INI").read_bytes()
    if not re.search(rb"(?m)^Description=[^\r\n]*", ini):
        raise ValueError("IMEINFO.INI Description missing")
    updated = re.sub(rb"(?m)^Description=[^\r\n]*",
                     b"Description=" + "Windows 3.0 简体中文全拼输入法 2.1".encode("gb2312"),
                     ini, count=1)
    (output / "IMEINFO.INI").write_bytes(updated)
    patch_winnls(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/patched/WINNLS.DLL",
                 output / "WINNLS.DLL")
    from ne import NEModule
    module = NEModule(target)
    allocations = [struct.unpack_from("<H", module.data, module.table + i * 8 + 6)[0]
                   or 65536 for i in range(module.count)]
    from build_gb2312_pinyin import collect, collect_phrases, normalize
    from pinyin_common import common_phrases, provenance
    table = collect()[0]
    rows = collect_phrases(table)
    phrase_table = output / 'PHRASES.TSV'
    phrase_table.write_text(''.join(k+'\t'+t.decode('gb2312')+'\n' for k,t in rows),'utf-8')
    manifest = {"version": "2.1", "diagnostics": args.diagnostics,
                "phrase_readings": len(rows), "distinct_phrases": len({t for k,t in rows}),
                "common_import": dict(provenance(), filtering=common_phrases(table, normalize)[1]),
                "syllables": keys, "character_coverage": coverage,
                "dictionary_bytes": size, "segment_allocations": allocations,
                "heap_bytes": struct.unpack_from("<H", module.data, module.ne + 0x10)[0],
                "stack_bytes": struct.unpack_from("<H", module.data, module.ne + 0x12)[0],
                "source_sha256": hashlib.sha256((HERE / "PINYIN_NATIVE.C").read_bytes()).hexdigest(),
                "dictionary_reader_sha256": hashlib.sha256((HERE / "PINYIN_DICT.H").read_bytes()).hexdigest(),
                "dictionary_inputs_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (ROOT/'src/main/public-tools/build_gb2312_pinyin.py', ROOT/'src/main/public-tools/pinyin_common.py',
                               ROOT/'src/main/public-tools/pinyin-phrases.tsv')},
                "phrase_table_sha256": hashlib.sha256(phrase_table.read_bytes()).hexdigest(),
                "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (target, output / "GBPY.DAT", output / "WINNLS.DLL", output / "IMEINFO.INI")}}
    (target.parent / "BUILD.json").write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
    print(f"PHON.IME: native Pinyin, {keys} syllables, "
          f"{coverage} GB2312 characters with readings, {size} dictionary bytes")


if __name__ == "__main__":
    main()
