"""Replace Big5-slotted outlines in a local CompuFont TrueType package.

The original user-owned CFSUNG.FON and the OFL source font are read only.
Only a new output file is written. Big5 cmap entries and glyph IDs stay fixed.
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
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = _LAYOUT_ROOT
sys.path.insert(0, str(ROOT / "src/test/native-gb2312/work/build/tool-deps"))

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from build_big5_simplified_fonts import DICTIONARY, read_mapping


BASE_SHA256 = "4a10d9ce7869f014ec180f749ebc169dd796756fc78ab3a38bbdd9ea5eb7c97f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def noto_outline(glyph_set, glyph_name: str):
    bounds_pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(bounds_pen)
    if bounds_pen.bounds is None:
        return None
    x_min, y_min, x_max, y_max = bounds_pen.bounds
    width, height = x_max - x_min, y_max - y_min
    if width <= 0 or height <= 0:
        return None
    scale = min(1.0, 980 / width, 980 / height)
    x_shift = (1000 - (x_min + x_max) * scale) / 2
    y_shift = (1000 - (y_min + y_max) * scale) / 2
    recording = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(recording)
    target = TTGlyphPen(None)
    recording.replay(TransformPen(target, (scale, 0, 0, scale, x_shift, y_shift)))
    return target.glyph()


def build(original: Path, source: Path, destination: Path) -> dict[str, object]:
    if original.resolve() == destination.resolve() or source.resolve() == destination.resolve():
        raise ValueError("output must differ from both input fonts")
    if sha256(original) != BASE_SHA256:
        raise ValueError("unexpected CFSUNG.FON baseline; inspect format before patching")
    target_font = TTFont(original)
    reference = TTFont(original)
    noto = TTFont(source)
    cmap_table = target_font["cmap"].tables
    if (len(cmap_table) != 1 or cmap_table[0].platformID != 3
            or cmap_table[0].platEncID != 0 or cmap_table[0].format != 4
            or target_font["maxp"].numGlyphs != 13590):
        raise ValueError("unexpected CompuFont Big5 outline layout")
    cmap = dict(cmap_table[0].cmap)
    source_cmap = dict(noto.getBestCmap() or {})
    source_glyphs = noto.getGlyphSet(location={"wght": 400}) if "fvar" in noto else noto.getGlyphSet()
    mappings = read_mapping(DICTIONARY)
    stats: dict[str, object] = {"original_sha256": sha256(original),
                                "source_sha256": sha256(source),
                                "replaced": 0, "compufont_source": 0,
                                "noto_source": 0, "missing_source": [],
                                "missing_big5_slot": []}
    missing_source: list[str] = stats["missing_source"]  # type: ignore[assignment]
    missing_slot: list[str] = stats["missing_big5_slot"]  # type: ignore[assignment]
    simplified_cache = {}
    for lead in range(0x81, 0xFF):
        for trail in (*range(0x40, 0x7F), *range(0xA1, 0xFF)):
            code = lead << 8 | trail
            try:
                original_char = bytes((lead, trail)).decode("cp950")
            except UnicodeDecodeError:
                continue
            if len(original_char) != 1:
                continue
            choices = mappings.get(original_char, (original_char,))
            if choices[0] == original_char:
                continue
            target_name = cmap.get(code)
            if target_name is None:
                missing_slot.append(f"{code:04X} U+{ord(original_char):04X}")
                continue
            glyph = None
            method = None
            chosen = None
            for choice in choices:
                if choice in simplified_cache:
                    glyph, method = simplified_cache[choice]
                else:
                    try:
                        source_code = int.from_bytes(choice.encode("cp950"), "big")
                    except UnicodeEncodeError:
                        source_code = -1
                    existing_name = cmap.get(source_code)
                    if existing_name is not None:
                        glyph = copy.deepcopy(reference["glyf"][existing_name])
                        method = "compufont_source"
                    elif ord(choice) in source_cmap:
                        glyph = noto_outline(source_glyphs, source_cmap[ord(choice)])
                        method = "noto_source" if glyph is not None else None
                    else:
                        glyph = method = None
                    simplified_cache[choice] = (glyph, method)
                if glyph is not None:
                    chosen = choice
                    break
            if glyph is None or method is None:
                missing_source.append(f"{code:04X} U+{ord(original_char):04X}")
                continue
            target_font["glyf"][target_name] = copy.deepcopy(glyph)
            target_font["glyf"][target_name].recalcBounds(target_font["glyf"])
            stats[method] = int(stats[method]) + 1
            stats["replaced"] = int(stats["replaced"]) + 1
            if code in (0xC5E9, 0xBFE9):
                print(f"{code:04X} {original_char} -> {chosen} via {method}")
    target_font["maxp"].recalc(target_font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    target_font.save(destination)
    check = TTFont(destination)
    if (check["maxp"].numGlyphs != reference["maxp"].numGlyphs
            or check["cmap"].tables[0].cmap != cmap
            or check["cfnt"].data != reference["cfnt"].data):
        raise ValueError("output changed glyph IDs, Big5 mapping, or CompuFont metadata")
    stats["output_sha256"] = sha256(destination)
    stats["output_bytes"] = destination.stat().st_size
    stats["max_points"] = check["maxp"].maxPoints
    stats["max_contours"] = check["maxp"].maxContours
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("ofl_source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.original, args.ofl_source, args.destination),
                     ensure_ascii=False, indent=2))
