"""Convert the text setup metadata and installed readme to GB2312.

Keep every ASCII character in SETUP.INF and WIN.SRC so file references, section
names, and option syntax remain unchanged.  Binary WIN.CNF is excluded.
"""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import hashlib
import json
from pathlib import Path

from patch_resources import simplify
from test_display import BASE, HERE, ROOT

from sys import path as python_path
python_path.insert(0, str(ROOT / "src/main/public-tools"))
from build_big5_simplified_fonts import DICTIONARY, read_mapping  # noqa: E402

FILES = ("SETUP.INF", "WIN.SRC", "README.TXT", "ETEN.TXT")
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup"


def main() -> None:
    mapping = read_mapping(DICTIONARY)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in FILES:
        source = (BASE / "WINDOWS" / name).read_bytes()
        result, substitutions = simplify(source, mapping)
        if len(source) != len(result):
            raise ValueError(f"{name}: byte offsets changed")
        ascii_source = "".join(c for c in source.decode("cp950") if ord(c) < 128)
        ascii_result = "".join(c for c in result.decode("gb2312") if ord(c) < 128)
        if ascii_source != ascii_result:
            raise ValueError(f"{name}: ASCII structure changed")
        result.decode("gb2312")
        (OUT / name).write_bytes(result)
        report[name] = {
            "bytes": len(result),
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "output_sha256": hashlib.sha256(result).hexdigest(),
            "changed_bytes": sum(a != b for a, b in zip(source, result)),
            "fallback_question_marks": sum(item.endswith("->？") for item in substitutions),
        }
    (OUT / "SETUP-MANIFEST.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: (item["changed_bytes"], item["fallback_question_marks"])
                      for name, item in report.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
