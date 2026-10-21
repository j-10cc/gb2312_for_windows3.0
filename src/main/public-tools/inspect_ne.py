"""Read Windows 3.x NE module names, exported ordinals and import modules."""

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
import hashlib
import struct
from pathlib import Path


def u16(data: bytes, at: int) -> int:
    return struct.unpack_from("<H", data, at)[0]


def names(data: bytes, at: int):
    while data[at]:
        size = data[at]
        name = data[at + 1 : at + 1 + size].decode("ascii", "replace")
        ordinal = u16(data, at + 1 + size)
        yield ordinal, name
        at += 1 + size + 2


def entries(data: bytes, ne: int) -> dict[int, tuple[int, int]]:
    at = ne + u16(data, ne + 4)
    stop = at + u16(data, ne + 6)
    ordinal = 1
    result = {}
    while at < stop and data[at]:
        count, segment = data[at : at + 2]
        at += 2
        if segment == 0:
            ordinal += count
            continue
        for _ in range(count):
            if segment == 0xFF:
                flags, interrupt, actual_segment, offset = struct.unpack_from("<BHBH", data, at)
                at += 6
            else:
                flags, offset = struct.unpack_from("<BH", data, at)
                actual_segment = segment
                at += 3
            result[ordinal] = (actual_segment, offset)
            ordinal += 1
    return result


def inspect(path: Path, show_segments: bool = False, show_relocations: bool = False, show_entries: bool = False) -> None:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"{path}: missing MZ header")
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne : ne + 2] != b"NE":
        raise ValueError(f"{path}: missing NE header")
    resident = dict(names(data, ne + u16(data, ne + 0x26)))
    nonresident_at = struct.unpack_from("<I", data, ne + 0x2C)[0]
    nonresident = dict(names(data, nonresident_at)) if nonresident_at < len(data) else {}
    references_at = ne + u16(data, ne + 0x28)
    imports_at = ne + u16(data, ne + 0x2A)
    module_count = u16(data, ne + 0x1E)
    imported = []
    for index in range(module_count):
        offset = u16(data, references_at + index * 2)
        at = imports_at + offset
        size = data[at]
        imported.append(data[at + 1 : at + 1 + size].decode("ascii", "replace"))
    print(path)
    print("  module:", resident.get(0, "?"))
    print("  flags:", f"0x{u16(data, ne + 0x0C):04X}", "segments:", u16(data, ne + 0x1C))
    print("  imports:", ", ".join(imported))
    print("  exports:", ", ".join(f"{ordinal}:{name}" for ordinal, name in sorted((resident | nonresident).items()) if ordinal))
    if show_entries:
        for ordinal, (segment, offset) in entries(data, ne).items():
            name = resident.get(ordinal, nonresident.get(ordinal, ""))
            if name:
                print(f"    {ordinal:3d} {name:24s} = {segment}:{offset:04X}")
    if show_segments or show_relocations:
        segment_table = ne + u16(data, ne + 0x22)
        shift = u16(data, ne + 0x32)
        for index in range(u16(data, ne + 0x1C)):
            at = segment_table + 8 * index
            sector, length, flags, minimum = struct.unpack_from("<HHHH", data, at)
            length = length or 0x10000
            file_at = sector << shift
            reloc_count = u16(data, file_at + length) if flags & 0x100 else 0
            digest = hashlib.sha256(data[file_at : file_at + length]).hexdigest()[:12]
            if show_segments:
                print(f"  seg {index + 1:2d}: offset={file_at:6d} length={length:5d} flags={flags:04X} min={minimum:5d} reloc={reloc_count:3d} sha={digest}")
            if show_relocations and reloc_count:
                for item in range(reloc_count):
                    address_type, relocation_type, offset, target1, target2 = struct.unpack_from("<BBHHH", data, file_at + length + 2 + item * 8)
                    if relocation_type & 3 == 1 and 1 <= target1 <= len(imported):
                        target = f"{imported[target1 - 1]}.{target2}"
                    elif relocation_type & 3 == 0:
                        target = f"segment {target1}:{target2:04X}"
                    else:
                        target = f"{target1}:{target2}"
                    print(f"    seg {index + 1}:{offset:04X} type={address_type:02X}/{relocation_type:02X} -> {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", type=Path, nargs="+")
    parser.add_argument("--segments", action="store_true")
    parser.add_argument("--relocations", action="store_true")
    parser.add_argument("--entries", action="store_true")
    args = parser.parse_args()
    for path in args.modules:
        inspect(path, show_segments=args.segments, show_relocations=args.relocations, show_entries=args.entries)
