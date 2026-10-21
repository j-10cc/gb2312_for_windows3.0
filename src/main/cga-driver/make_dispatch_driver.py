"""Inspect/patch the WIFE printer dispatcher; never use it as display.drv.

The input is the *expanded* DISPATCH.BIN from the user's own installation media.
The original binary is never modified. DISPATCH.BIN lacks the display-only
ordinals 90, 91, 101-104 and 500; it is for printer drivers, not CGA.DRV.
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
import re
import struct
from pathlib import Path


TAG = b"TargetDriverNameTag:\0"


def make_dispatch(template: bytes, target: str) -> bytes:
    name = target.upper().encode("ascii")
    if not re.fullmatch(rb"[A-Z0-9_]{1,8}\.DRV", name):
        raise ValueError("target must be a DOS 8.3 .DRV filename")
    if name == b"CGA.DRV":
        raise ValueError("DISPATCH.BIN is a printer wrapper, not a CGA display wrapper")
    if template[:2] != b"MZ" or struct.unpack_from("<I", template, 0x3C)[0] >= len(template):
        raise ValueError("input must be an expanded MZ/NE driver template")
    ne = struct.unpack_from("<I", template, 0x3C)[0]
    if template[ne : ne + 2] != b"NE":
        raise ValueError("input is not an NE driver template")
    if template.count(TAG) != 1:
        raise ValueError("TargetDriverNameTag must occur exactly once")
    at = template.index(TAG) + len(TAG)
    # The template reserves 128 zero bytes after the tag in its data segment.
    if any(template[at : at + 128]):
        raise ValueError("target slot is not blank; input may already be patched")
    patched = bytearray(template)
    patched[at : at + len(name)] = name
    return bytes(patched)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    if args.template.resolve() == args.output.resolve():
        raise ValueError("output must differ from template")
    try:
        result = make_dispatch(args.template.read_bytes(), args.target)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Created {args.output} ({len(result)} bytes), target {args.target.upper()}")


if __name__ == "__main__":
    main()
