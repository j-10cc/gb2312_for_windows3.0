"""Build GB2312 CGA and VGA fonts for an isolated Windows 3.0a installation.

The original CompuFont files remain untouched. The VGA outline and bitmap
banks use one GB2312 ordinal slot for every defined double-byte character.
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


import copy
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = _LAYOUT_ROOT
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src/main/public-tools"), str(ROOT / "src/test/native-gb2312/work/build/tool-deps")]

from fontTools.ttLib import TTFont  # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen  # noqa: E402
from build_font import read_unifont  # noqa: E402
from build_legible_fonts import SOURCES, build as build_legible  # noqa: E402
from build_gb2312_cga import build as build_cga  # noqa: E402
from build_wife_big5_bitmap import (  # noqa: E402
    BIG5_PREFIX, FULL_GLYPHS, pack_glyph,
)
from build_wife_big5_outline import noto_outline  # noqa: E402

BASE = ROOT / "src/test/native-gb2312/work/build/setup-test/C32/WINDOWS/SYSTEM"
BUILD = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/fonts"
NOTO = Path("C:/Windows/Fonts/NotoSerifSC-VF.ttf")
SOURCE_SHA256 = {
    "NotoSerifSC-VF.ttf": "a4aed9985a5916fbf6690456f8732a9fccd517938e353165d4142b4f11a39280",
    "unifont-base.hex": "0bd74fd86b63d309446b260cba12bb82cf66d7f9532fb83eca9eccf98a9e7d93",
    "wqy.hex": "63515f7a2397012147446227a08ffa84bd0bc3a6951a09ecfe4c87148cbf6584",
}
EXPECTED = {
    "CFSUNG.FON": "4a10d9ce7869f014ec180f749ebc169dd796756fc78ab3a38bbdd9ea5eb7c97f",
    "CFSUNG16.B5Q": "2930ae578d967296da932c77f710ffe22839a90a26f1104695cae8462d569b3a",
    "CFSUNG20.B5Q": "73e31e87add4c071e388281856edaa0242033f77810d057c04dc5214e6e5ed27",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gb_pairs() -> dict[int, str]:
    result = {}
    for lead in range(0xA1, 0xF8):
        for trail in range(0xA1, 0xFF):
            raw = bytes((lead, trail))
            char = raw.decode("gb2312", "ignore")
            if len(char) == 1:
                result[lead << 8 | trail] = char
    if len(result) != 7445:
        raise ValueError("unexpected GB2312 repertoire")
    return result


def checked_original(name: str) -> bytes:
    data = (BASE / name).read_bytes()
    if sha256(data) != EXPECTED[name]:
        raise ValueError(f"unexpected original {name}")
    return data


def gb_ordinal(code: int) -> int:
    return ((code >> 8) - 0xA1) * 94 + ((code & 0xFF) - 0xA1)


def build_outline(target: Path, repertoire: dict[int, str]) -> dict:
    checked_original("CFSUNG.FON")
    font = TTFont(BASE / "CFSUNG.FON", recalcTimestamp=False)
    source = TTFont(NOTO)
    cmap_tables = font["cmap"].tables
    if (len(cmap_tables) != 1 or cmap_tables[0].platformID != 3
            or cmap_tables[0].platEncID != 0 or cmap_tables[0].format != 4
            or font["maxp"].numGlyphs != 13590):
        raise ValueError("unexpected WIFE outline structure")
    cmap = cmap_tables[0].cmap
    glyph_order = font.getGlyphOrder()
    if 5000 + 87 * 94 - 1 >= len(glyph_order):
        raise ValueError("GB2312 ordinal bank exceeds font glyph count")
    source_cmap = source.getBestCmap() or {}
    source_glyphs = (source.getGlyphSet(location={"wght": 400})
                     if "fvar" in source else source.getGlyphSet())
    for code, char in repertoire.items():
        glyph = noto_outline(source_glyphs, source_cmap[ord(char)])
        if glyph is None and char.isspace():
            glyph = TTGlyphPen(None).glyph()
        if glyph is None:
            raise ValueError(f"no outline for {code:04X} {char}")
        name = glyph_order[5000 + gb_ordinal(code)]
        cmap[code] = name
        font["glyf"][name] = copy.deepcopy(glyph)
        font["glyf"][name].recalcBounds(font["glyf"])
    font["maxp"].recalc(font)
    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(target)
    check = TTFont(target)
    loaded_map = check["cmap"].tables[0].cmap
    if (check["maxp"].numGlyphs != 13590
            or check["cfnt"].data != TTFont(BASE / "CFSUNG.FON")["cfnt"].data
            or not all(code in loaded_map for code in repertoire)):
        raise ValueError("generated WIFE outline failed structural validation")
    return {"mapped": len(repertoire), "gb_ordinal_glyph_base": 5000,
            "bytes": target.stat().st_size, "sha256": sha256(target.read_bytes())}


def build_bitmap(size: int, target: Path, repertoire: dict[int, str]) -> dict:
    name = f"CFSUNG{size}.B5Q"
    data = bytearray(checked_original(name))
    if data[:8] != b"BIG5-FQ\0":
        raise ValueError("unexpected B5Q header")
    half_at, full_at = struct.unpack_from("<II", data, 0x110)
    half_stride, stride = struct.unpack_from("<HH", data, 0x11C)
    expected = {16: (0x120, 0x920, 16, 32),
                20: (0x120, 0x1520, 40, 60)}[size]
    if ((half_at, full_at, half_stride, stride) != expected
            or len(data) != full_at + FULL_GLYPHS * stride):
        raise ValueError("unexpected B5Q geometry")
    glyphs = read_unifont(SOURCES)
    mapped = 0
    missing = []
    for code, char in repertoire.items():
        index = BIG5_PREFIX + gb_ordinal(code)
        if index >= FULL_GLYPHS:
            missing.append(code)
            continue
        image = glyphs.get(ord(char))
        if image is None and not char.isspace():
            raise ValueError(f"no bitmap source for {code:04X} {char}")
        at = full_at + index * stride
        data[at:at + stride] = (pack_glyph(image, size) if image
                                 else bytes([0xFF]) * stride)
        mapped += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"mapped": mapped, "unmapped_byte_pairs": [f"{x:04X}" for x in missing],
            "bytes": len(data), "sha256": sha256(data)}


def main() -> None:
    source_paths = [NOTO, *SOURCES]
    sources = {path.name: sha256(path.read_bytes()) for path in source_paths}
    if sources != SOURCE_SHA256:
        raise ValueError("font source differs from the reviewed build")
    repertoire = gb_pairs()
    report = {"encoding": "GB2312/EUC-CN", "valid_pairs": len(repertoire),
              "source_sha256": sources, "cga": {}, "vga": {}}
    # The 12-pixel bank is used by menus and title bars. The 10- and
    # 8-pixel banks remain available for icons and dense document rows.
    build_legible(ROOT / "src/test/native-gb2312/work/build/CHCGA12.FNT", read_unifont(SOURCES), 14, 12, 7)
    for size, width in ((12, 14), (10, 12), (8, 10)):
        target = BUILD / f"CHCGA{size:02d}.FNT"
        valid, missing = build_cga(target, size, width)
        if valid != 7445 or missing != 0:
            raise ValueError("CGA font coverage incomplete")
        report["cga"][target.name] = {"mapped": valid,
                                      "bytes": target.stat().st_size,
                                      "sha256": sha256(target.read_bytes())}
    report["vga"]["CFSUNG.FON"] = build_outline(BUILD / "CFSUNG.FON", repertoire)
    for size in (16, 20):
        name = f"CFSUNG{size}.B5Q"
        report["vga"][name] = build_bitmap(size, BUILD / name, repertoire)
    (BUILD / "FONT-MANIFEST.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cga_mapped": report["cga"]["CHCGA10.FNT"]["mapped"],
                      "vga_outline_mapped": report["vga"]["CFSUNG.FON"]["mapped"],
                      "vga_bitmap_mapped": report["vga"]["CFSUNG16.B5Q"]["mapped"],
                      "vga_bitmap_unmapped": len(report["vga"]["CFSUNG16.B5Q"]["unmapped_byte_pairs"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
