"""Set a rebuilt Windows 3.0 DDK NE driver's minimum Windows version to 3.00.

The bundled RC 3.11 stamps 3.10, which Windows 3.0 refuses to load. This
changes only NE header bytes 0x3E-0x3F and never overwrites the input file.
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
import struct
from pathlib import Path


def fix(data: bytes) -> bytes:
    if data[:2] != b"MZ" or len(data) < 0x40:
        raise ValueError("not an MZ executable")
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if ne + 0x40 > len(data) or data[ne : ne + 2] != b"NE":
        raise ValueError("not an NE executable")
    current = struct.unpack_from("<H", data, ne + 0x3E)[0]
    if current != 0x030A:
        raise ValueError(f"expected RC 3.11 minimum version 3.10, got 0x{current:04X}")
    result = bytearray(data)
    struct.pack_into("<H", result, ne + 0x3E, 0x0300)
    return bytes(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_drv", type=Path)
    parser.add_argument("output_drv", type=Path)
    args = parser.parse_args()
    if args.input_drv.resolve() == args.output_drv.resolve():
        parser.error("output must differ from input")
    result = fix(args.input_drv.read_bytes())
    args.output_drv.parent.mkdir(parents=True, exist_ok=True)
    args.output_drv.write_bytes(result)
    print(f"Created {args.output_drv} with NE minimum Windows version 3.00")


if __name__ == "__main__":
    main()
