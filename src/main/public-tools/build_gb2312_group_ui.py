"""Generate Program Manager icon captions from audited .GRP item names."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import struct
from pathlib import Path


ROOT = _LAYOUT_ROOT
SOURCE = ROOT / "external/win31igdrv/WINDOWS"
TARGET = ROOT / "src/test/native-gb2312/gb2312_first/GBGRP.H"

LABELS = [
    ("Main", "主群组"), ("Accessories", "附件"), ("Games", "游戏"),
    ("File Manager", "文件管理器"), ("Control Panel", "控制面板"),
    ("Print Manager", "打印管理器"),
    ("Clipboard Viewer", "剪贴板查看器"),
    ("MS-DOS Prompt", "DOS 提示符"),
    ("Windows Setup", "Windows 安装"),
    ("PIF Editor", "PIF 编辑器"), ("Read Me", "自述文件"),
    ("Write", "书写器"), ("Paintbrush", "画图"),
    ("Terminal", "终端"), ("Notepad", "记事本"),
    ("Recorder", "录制器"), ("Cardfile", "卡片盒"),
    ("Calendar", "日历"), ("Calculator", "计算器"),
    ("Clock", "时钟"), ("Solitaire", "纸牌"),
    ("Reversi", "黑白棋"),
]


def names(path: Path) -> set[str]:
    data = path.read_bytes()
    if data[:4] != b"PMCC":
        raise ValueError(f"{path}: bad group signature")
    count = struct.unpack_from("<H", data, 32)[0]
    if count > 64:
        raise ValueError(f"{path}: too many items")
    offsets = struct.unpack_from("<" + "H" * count, data, 34)
    result = set()
    for offset in (struct.unpack_from("<H", data, 22)[0],
                   *(struct.unpack_from("<H", data, at + 18)[0]
                     for at in offsets if at)):
        if offset and offset < len(data):
            result.add(data[offset:data.index(b"\0", offset)].decode(
                "cp1252", "replace"))
    return result


def main() -> None:
    observed = set().union(*(names(SOURCE / name) for name in
                             ("MAIN.GRP", "ACCESSOR.GRP", "GAMES.GRP")))
    missing = {english for english, _ in LABELS if english not in observed}
    if missing != {"Reversi"}:
        raise ValueError(f"Unexpected group caption audit: {missing}")
    lines = ["/* Generated from original-format Program Manager .GRP names. */",
             "typedef struct { const char *english; const char *chinese; } GBGRPLABEL;",
             "static GBGRPLABEL gb_group_labels[] = {"]
    for english, chinese in LABELS:
        encoded = "".join(f"\\x{value:02X}" for value in
                          chinese.encode("gb2312"))
        lines.append(f'    {{"{english}", "{encoded}"}},')
    lines += ["};", f"#define GB_GROUP_LABEL_COUNT {len(LABELS)}", ""]
    TARGET.write_text("\n".join(lines), encoding="ascii")
    print(TARGET)


if __name__ == "__main__":
    main()
