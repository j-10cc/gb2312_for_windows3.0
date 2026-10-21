"""List untranslated readable NE resource strings in stock Windows apps."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import re
from pathlib import Path

from build_gb2312_menu_ui import LABELS, TITLES
from build_gb2312_resource_ui import DIALOG_LABELS, CONTROL_ICONS
from inspect_win16_resources import resources, strings


ROOT = _LAYOUT_ROOT
ORIGINALS = ROOT / "src/test/native-gb2312/work/build/expanded/english"
KNOWN = {s.lower().replace("&", "").rstrip(".: ") for s, _ in LABELS}
KNOWN.update(s.lower().replace("&", "").rstrip(".: ") for s in DIALOG_LABELS)
KNOWN.update(s.lower().replace("&", "").rstrip(".: ") for s, _ in TITLES)
KNOWN.update(s.lower().replace("&", "").rstrip(".: ") for s, _ in CONTROL_ICONS.values())


def normalize(value: str) -> str:
    return value.split("\t", 1)[0].replace("&", "").strip().rstrip(".: ").lower()


def main() -> None:
    for name in ("PROGMAN.EXE", "CONTROL.EXE", "WINFILE.EXE"):
        missed = set()
        for kind, block, _, payload in resources(ORIGINALS / name):
            if kind == 6:
                found = (value for _, value in strings(payload, block))
            elif kind in (4, 5):
                found = (part.decode("cp1252", "replace") for part
                         in re.findall(rb"[ -~]{3,}", payload))
            else:
                continue
            for value in found:
                clean = normalize(value)
                if (clean and len(clean) < 80 and
                    re.search(r"[a-z]{3,}", clean) and
                    clean not in KNOWN):
                    missed.add(value)
        print(name, len(missed))
        for value in sorted(missed, key=str.lower):
            print("  ", value)


if __name__ == "__main__":
    main()
