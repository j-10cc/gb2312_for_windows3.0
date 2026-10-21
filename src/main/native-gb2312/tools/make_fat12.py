"""Create a small DOS FAT12 floppy for isolated VirtualBox diagnostics."""

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

SECTOR = 512
SECTORS = 2880
FAT_SECTORS = 9
ROOT_ENTRIES = 224
DATA_SECTOR = 33


def put_fat_entry(fat: bytearray, cluster: int, value: int) -> None:
    offset = cluster + cluster // 2
    if cluster & 1:
        fat[offset] = (fat[offset] & 0x0F) | ((value & 0x0F) << 4)
        fat[offset + 1] = value >> 4
    else:
        fat[offset] = value & 0xFF
        fat[offset + 1] = (fat[offset + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build(destination: Path, sources: list[Path]) -> None:
    if len(sources) > ROOT_ENTRIES:
        raise ValueError("too many files")
    disk = bytearray(SECTOR * SECTORS)
    boot = memoryview(disk)[:SECTOR]
    boot[:3] = b"\xEB\x3C\x90"
    boot[3:11] = b"MSDOS5.0"
    struct.pack_into("<HBHBHHBHHHII", boot, 11,
                     SECTOR, 1, 1, 2, ROOT_ENTRIES, SECTORS, 0xF0,
                     FAT_SECTORS, 18, 2, 0, 0)
    boot[510:512] = b"\x55\xAA"
    fat = bytearray(FAT_SECTORS * SECTOR)
    fat[:3] = b"\xF0\xFF\xFF"
    next_cluster = 2
    for number, source in enumerate(sources):
        data = source.read_bytes()
        name = source.name.upper().split(".")
        if len(name) != 2 or not (1 <= len(name[0]) <= 8) or not (1 <= len(name[1]) <= 3):
            raise ValueError(f"not DOS 8.3: {source.name}")
        name_bytes = (name[0].ljust(8) + name[1].ljust(3)).encode("ascii")
        count = (len(data) + SECTOR - 1) // SECTOR
        if next_cluster + count - 2 > SECTORS - DATA_SECTOR:
            raise ValueError("floppy full")
        first = next_cluster if count else 0
        for index in range(count):
            cluster = next_cluster + index
            put_fat_entry(fat, cluster, 0xFFF if index == count - 1 else cluster + 1)
            start = (DATA_SECTOR + cluster - 2) * SECTOR
            disk[start:start + SECTOR] = data[index * SECTOR:(index + 1) * SECTOR].ljust(SECTOR, b"\0")
        next_cluster += count
        root = (1 + 2 * FAT_SECTORS) * SECTOR + number * 32
        disk[root:root + 11] = name_bytes
        disk[root + 11] = 0x20
        struct.pack_into("<HI", disk, root + 26, first, len(data))
    for start in (SECTOR, (1 + FAT_SECTORS) * SECTOR):
        disk[start:start + len(fat)] = fat
    destination.write_bytes(disk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    build(args.destination, args.sources)
