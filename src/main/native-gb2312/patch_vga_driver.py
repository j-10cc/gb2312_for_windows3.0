"""Build the GB2312-specific CFFONT.FOD from the user's original binary.

The original Big5 ordinal converters are replaced in-place with direct
GB2312 94-column indexing. The NE segment sizes and relocations stay fixed.
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
import subprocess
from pathlib import Path

from ne import NEModule

HERE = Path(__file__).resolve().parent
SOURCE = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup-test/C32/WINDOWS/SYSTEM/CFFONT.FOD"
TARGET = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patches/CFFONT.FOD"
SOURCE_SHA256 = "4e570b7db6104ffd103febbb7b58108491baa1ecd13c4711e8032b7d86e0583a"
NASM = _LAYOUT_ROOT / "external/nasm/nasm-2.16.03/nasm.exe"


def patch() -> None:
    module = NEModule(SOURCE)
    data = bytearray(module.data)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("CFFONT.FOD source differs from reviewed binary")
    base, length, _ = module.segment(3)
    if length != 0x1BA4:
        raise ValueError("unexpected CFFONT code segment")
    replacements = ((0x19B0, bytes.fromhex("81 7e 06 bf a3"),
                     bytes.fromhex("81 7e 06 fe a3")),)
    for offset, original, modified in replacements:
        at = base + offset
        if data[at:at + len(original)] != original:
            raise ValueError(f"unexpected CFFONT bytes at 3:{offset:04X}")
        data[at:at + len(original)] = modified
    for segment, start, capacity, source_name in (
        (10, 1, 0xAB, "cffont_gb_bitmap.asm"),
        (17, 0, 0xD8, "cffont_gb_outline.asm"),
    ):
        source = HERE / source_name
        binary = TARGET.parent / (source.stem + ".bin")
        subprocess.run((str(NASM), "-f", "bin", source.name, "-o",
                        str(binary)), cwd=HERE, check=True)
        code = binary.read_bytes()
        if len(code) > capacity:
            raise ValueError(f"replacement {source_name} exceeds segment capacity")
        segment_base, segment_length, _ = module.segment(segment)
        if start + capacity > segment_length:
            raise ValueError("replacement crosses original NE segment")
        data[segment_base + start:segment_base + start + capacity] = (
            code + bytes([0x90]) * (capacity - len(code)))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(data)
    result = NEModule(TARGET)
    if any(result.segment(i) != module.segment(i) for i in range(1, module.count + 1)):
        raise ValueError("NE segment table changed")
    print(f"{TARGET}: sha256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    patch()
