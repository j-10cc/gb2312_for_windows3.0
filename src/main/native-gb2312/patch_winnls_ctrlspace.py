"""Make the Windows 3.0 WINNLS keyboard path toggle on Ctrl+Space.

The Traditional Chinese WINNLS checks its Shift-held state at the space-key
branch.  Its Ctrl-held state is maintained by the same native keyboard hook.
This one-byte operand patch changes only that state selection.
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


import argparse
from pathlib import Path

from ne import NEModule


def build(source: Path, target: Path) -> None:
    module = NEModule(source)
    offset, length, _ = module.segment(2)
    if length <= 0x10F2:
        raise ValueError("unexpected WINNLS segment length")
    site = offset + 0x10EE
    expected = bytes.fromhex("83 3e 42 00 00 74 5a")
    if module.data[site:site + len(expected)] != expected:
        raise ValueError("WINNLS Ctrl+Space patch site differs from 3.0a sample")
    patched = bytearray(module.data)
    patched[site + 2] = 0x40
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(patched)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(
        "src/test/native-gb2312/work/build/expanded/chinese/WINNLS.DLL"))
    parser.add_argument("--target", type=Path, default=Path(
        "src/test/native-gb2312/work/build/ime/WINNLS.DLL"))
    args = parser.parse_args()
    build(args.source, args.target)
    print(args.target)


if __name__ == "__main__":
    main()
