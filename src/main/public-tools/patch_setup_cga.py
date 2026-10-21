"""Add the English CGA installation profile to Chinese Windows 3.0 SETUP.INF.

Writes a new file. The caller must place the listed English CGA files alongside
the Chinese setup media before running Setup on the patched copy.
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


INSERTIONS = {
    b"[display]\r\n": (
        b"cga = 1:cga.drv, \"CGA 640x200 GB2312\", \"200,96,48\", "
        b"1:cga.gr2, 1:cgalogo.lgo, 1:vddcga.386, 1:cga.gr3,, 1:cgalogo.rle\r\n"
    ),
    b"[sysfonts]\r\n": b"1:cgas12.fon,\"CGA 640x200 GB2312 System Font\",\"200,96,48\"\r\n",
    b"[fixedfonts]\r\n": b"1:cgafix.fon,\"CGA 640x200 Fixed Font\",\"200,96,48\"\r\n",
    b"[oemfonts]\r\n": b"1:cgaoem.fon,\"CGA 640x200 Terminal Font\",\"200,96,48\",1\r\n",
    b"[CVGA.GR3]\r\n": (
        b"[CGA.GR3]\r\n"
        b"1:CGA40WOA.FON,1:CGA40850.FON\r\n"
        b"1:CGA80WOA.FON,1:CGA80850.FON\r\n\r\n"
    ),
}

REQUIRED_ENGLISH = (
    "CGA.DRV", "CGA.GR2", "CGA.GR3", "CGASYS.FON", "CGAFIX.FON",
    "CGAOEM.FON", "CGALOGO.LGO", "CGALOGO.RLE", "VDDCGA.386",
    "CGA40WOA.FON", "CGA40850.FON", "CGA80WOA.FON", "CGA80850.FON",
)


def patch_setup(source: bytes) -> bytes:
    data = source
    for marker, payload in INSERTIONS.items():
        if data.count(marker) != 1:
            raise ValueError(f"expected exactly one {marker!r} section")
        data = data.replace(marker, marker + payload, 1)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chinese_inf", type=Path)
    parser.add_argument("output_inf", type=Path)
    parser.add_argument("--english-files", type=Path)
    args = parser.parse_args()
    if args.chinese_inf.resolve() == args.output_inf.resolve():
        raise ValueError("output must differ from original SETUP.INF")
    if args.english_files is not None:
        missing = [name for name in REQUIRED_ENGLISH if not (args.english_files / name).is_file()]
        if missing:
            raise FileNotFoundError("missing English CGA files: " + ", ".join(missing))
    args.output_inf.parent.mkdir(parents=True, exist_ok=True)
    args.output_inf.write_bytes(patch_setup(args.chinese_inf.read_bytes()))
    print(f"Created {args.output_inf}; copy {len(REQUIRED_ENGLISH)} English CGA files into the setup directory")


if __name__ == "__main__":
    main()
