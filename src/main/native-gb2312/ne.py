"""Small read-only helpers for the exact Windows 3.0a NE modules in this project."""

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
import subprocess
import tempfile
from pathlib import Path


def word(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


class NEModule:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise ValueError(f"{path}: no MZ header")
        self.ne = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[self.ne:self.ne + 2] != b"NE":
            raise ValueError(f"{path}: no NE header")
        self.shift = word(self.data, self.ne + 0x32)
        self.count = word(self.data, self.ne + 0x1C)
        self.table = self.ne + word(self.data, self.ne + 0x22)

    def segment(self, number: int) -> tuple[int, int, int]:
        if not 1 <= number <= self.count:
            raise ValueError(f"segment {number} outside 1..{self.count}")
        sector, length, flags, _ = struct.unpack_from(
            "<HHHH", self.data, self.table + (number - 1) * 8
        )
        return sector << self.shift, length or 65536, flags

    def slice(self, number: int, offset: int, size: int) -> bytes:
        base, length, _ = self.segment(number)
        if offset < 0 or size < 0 or offset + size > length:
            raise ValueError("slice crosses segment boundary")
        return self.data[base + offset:base + offset + size]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("module", type=Path)
    p.add_argument("segment", type=int)
    p.add_argument("offset", type=lambda x: int(x, 0))
    p.add_argument("size", type=lambda x: int(x, 0))
    p.add_argument("--disassemble", action="store_true")
    a = p.parse_args()
    module = NEModule(a.module)
    fragment = module.slice(a.segment, a.offset, a.size)
    print(f"{a.module} segment {a.segment}:{a.offset:04X} size {a.size}")
    if a.disassemble:
        root = _LAYOUT_ROOT
        disassembler = root / "external/nasm/nasm-2.16.03/ndisasm.exe"
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "segment.bin"
            binary.write_bytes(fragment)
            subprocess.run([str(disassembler), "-b", "16", "-o",
                            hex(a.offset), str(binary)], check=True)
    else:
        print(fragment.hex(" "))


if __name__ == "__main__":
    main()
