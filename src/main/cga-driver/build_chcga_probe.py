"""Prepare the Windows 3.0 DDK CGA Big5 real-mode text overlay.

The driver reads the full Big5 screen fonts from disk; 35 embedded glyphs are
only a fallback for the normal size. It still draws directly to CGA memory
and is not a general-purpose Windows Chinese display driver.
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
import shutil
import struct
from pathlib import Path

from build_font import HEADER, big5_slot


CHARACTERS = "程式管理員檔案編輯選項視窗說明群組建立新增開啟關閉退出儲存設定標題內容"
GB_CHARACTERS = "简体中文输入法编辑文件保存测试窗口程序系统汉字拼音"
HOOK_SAVE_ORIGINAL = b"draw_char_string:\r\n\tcall\tget_clip"
HOOK_SAVE_NEW = b"draw_char_string:\r\n\tcall\tchinese_save_context\r\n\tcall\tget_clip"
HOOK_DRAW_ORIGINAL = b"\tcall\tax\t\t\t;This guy does the real work"
HOOK_DRAW_NEW = (b"\tpush\tax\r\n\tcall\tchinese_should_skip_base\r\n\tpop\tax\r\n"
                 b"\tjc\tchinese_skip_english\r\n" + HOOK_DRAW_ORIGINAL
                 + b"\r\nchinese_skip_english:")
HOOK_OVERLAY_ORIGINAL = b"strblt_clean_up:\r\n\ttest\texcel,IS_DEVICE"
HOOK_OVERLAY_NEW = b"strblt_clean_up:\r\n\tcall\tchinese_overlay\r\n\ttest\texcel,IS_DEVICE"
HOOK_FINISH_ORIGINAL = b"exit_strblt:\r\n\r\ncEnd"
HOOK_FINISH_NEW = b"exit_strblt:\r\n\tcall\tchinese_finish\r\n\r\ncEnd"
INCLUDE_ORIGINAL = b"cEnd\r\npage\r\n;--------------------------Private-Routine"
INCLUDE_NEW = b"cEnd\r\n\tinclude CHCGA.INC\r\npage\r\n;--------------------------Private-Routine"


def glyph_records(font: bytes, encoding: str = "cp950") -> tuple[list[tuple[bytes, bytes]], int]:
    magic, version, width, height, ascii_width, slots, record_size, ascii_at, dbcs_at, _ = HEADER.unpack_from(font)
    if magic != f"CH{height:02d}".encode("ascii") or version != 1 or record_size != height * 2:
        raise ValueError("not a compact CHCGA font")
    if (width, height, ascii_width) not in ((14, 14, 7), (14, 12, 7), (12, 10, 6), (10, 8, 5)):
        raise ValueError("unsupported compact font dimensions")
    result = []
    characters = GB_CHARACTERS if encoding == "gb2312" else CHARACTERS
    for char in dict.fromkeys(characters):
        pair = char.encode(encoding)
        if len(pair) != 2:
            raise ValueError(f"not Big5: {char}")
        slot = big5_slot(*pair)
        if slot is None or slot >= slots:
            raise ValueError(f"invalid Big5 slot: {char}")
        image = font[dbcs_at + slot * record_size : dbcs_at + (slot + 1) * record_size]
        if not any(image):
            raise ValueError(f"font lacks glyph: {char}")
        result.append((pair, image))
    return result, height


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ddk_root", type=Path)
    parser.add_argument("font", type=Path)
    parser.add_argument("--small-font", type=Path, help="8-pixel dense document font")
    parser.add_argument("--medium-font", type=Path, help="10-pixel icon caption font")
    parser.add_argument("--trace", action="store_true", help="diagnostic CGA draw call log")
    parser.add_argument("--no-hook", action="store_true", help="link overlay code without invoking it")
    parser.add_argument("--gb2312", action="store_true", help="build strict GB2312 pair decoding and fallback glyphs")
    args = parser.parse_args()
    root = args.ddk_root.resolve()
    common = root / "display" / "1plane" / "bw" / "cgaherc"
    source = common / "strblt.asm"
    original = common / "strblt.original.asm"
    target = common / "cga" / "CHCGA.INC"
    if not original.exists():
        shutil.copy2(source, original)
    base = original.read_bytes()
    for marker in (HOOK_SAVE_ORIGINAL, HOOK_DRAW_ORIGINAL, HOOK_OVERLAY_ORIGINAL,
                   HOOK_FINISH_ORIGINAL, INCLUDE_ORIGINAL):
        if base.count(marker) != 1:
            raise ValueError("DDK STRBLT.ASM hook point differs from expected source")
    patched = base.replace(INCLUDE_ORIGINAL, INCLUDE_NEW, 1)
    if not args.no_hook:
        patched = patched.replace(HOOK_SAVE_ORIGINAL, HOOK_SAVE_NEW, 1)
        patched = patched.replace(HOOK_DRAW_ORIGINAL, HOOK_DRAW_NEW, 1)
        patched = patched.replace(HOOK_OVERLAY_ORIGINAL, HOOK_OVERLAY_NEW, 1)
        patched = patched.replace(HOOK_FINISH_ORIGINAL, HOOK_FINISH_NEW, 1)
    source.write_bytes(patched)

    main_font = args.font.read_bytes()
    encoding = "gb2312" if args.gb2312 else "cp950"
    records, height = glyph_records(main_font, encoding)
    small_height = 8
    small_font = None
    if args.small_font:
        small_font = args.small_font.read_bytes()
        _, small_height = glyph_records(small_font, encoding)
        if small_height >= height:
            raise ValueError("small font must be shorter than normal font")
    medium_font = args.medium_font.read_bytes() if args.medium_font else None
    medium_height = glyph_records(medium_font, encoding)[1] if medium_font else small_height
    if not small_height <= medium_height < height:
        raise ValueError("medium font height is outside the small/main range")
    lines = [f"CHCGA_HEIGHT EQU {height}", f"CHCGA_SMALL_HEIGHT EQU {small_height}",
             f"CHCGA_MEDIUM_HEIGHT EQU {medium_height}",
             f"CHCGA_RECORD EQU {2 + height * 2}", ""]
    if args.trace:
        lines.append("CHCGA_TRACE EQU 1")
    if args.gb2312:
        lines.append("CHCGA_GB2312 EQU 1")
    lines += (_LAYOUT_ROOT / "src/main/cga-driver" / "chcga_overlay.inc").read_text(encoding="ascii").splitlines()
    main_path = f"C:\\WINDOWS\\SYSTEM\\CHCGA{height:02d}.FNT"
    small_path = f"C:\\WINDOWS\\SYSTEM\\CHCGA{small_height:02d}.FNT"
    medium_path = f"C:\\WINDOWS\\SYSTEM\\CHCGA{medium_height:02d}.FNT"
    # The DOS installer rewrites these fixed-width slots for the chosen drive
    # and directory after copying the driver into its final location.
    for path in (main_path, small_path, medium_path):
        if len(path) >= 80:
            raise ValueError("font path exceeds installer slot")
    lines += ["", f"co_font_path db '{main_path}',0",
              f"    db {79 - len(main_path)} dup (0)",
              f"co_small_font_path db '{small_path}',0",
              f"    db {79 - len(small_path)} dup (0)",
              f"co_medium_font_path db '{medium_path}',0",
              f"    db {79 - len(medium_path)} dup (0)",
              "", "chglyph_table label byte"]
    for pair, image in records:
        lines.append("    db " + ",".join(f"0{byte:02X}h" for byte in pair) + f" ; {pair.hex().upper()}")
        for at in range(0, len(image), 14):
            lines.append("    db " + ",".join(f"0{byte:02X}h" for byte in image[at : at + 14]))
    lines.append("chglyph_table_end label byte")
    for name, font, font_height in (("ch_ascii_main", main_font, height),
                                    ("ch_ascii_small", small_font or main_font, small_height),
                                    ("ch_ascii_medium", medium_font or small_font or main_font,
                                     medium_height)):
        _, _, _, _, _, _, _, ascii_at, _, _ = HEADER.unpack_from(font)
        image = font[ascii_at:ascii_at + 128 * font_height]
        if len(image) != 128 * font_height:
            raise ValueError("ASCII font bank is truncated")
        lines.append(name + " label byte")
        for at in range(0, len(image), 14):
            lines.append("    db " + ",".join(f"0{byte:02X}h" for byte in image[at:at + 14]))
    target.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", newline="")
    print(f"Prepared {source} and {target} with {len(records)} {encoding} fallback glyphs")


if __name__ == "__main__":
    main()
