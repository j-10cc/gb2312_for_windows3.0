"""Put simplified glyphs in the existing Big5 slots of the CHCGA font banks.

The output keeps the v1 CHCGA layout and the original Big5 byte semantics.
Only copied font files are changed; the Traditional source banks and driver
remain untouched. OpenCC TSCharacters supplies a deterministic per-character
mapping. Phrase-sensitive conversion is outside the scope of a font bank.
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
import json
from pathlib import Path

from build_font import HEADER, big5_slot, pack_dbcs, read_unifont
from build_legible_fonts import SOURCES, TRAILS, hint_glyph


ROOT = _LAYOUT_ROOT
DICTIONARY = ROOT / "external/licenses/opencc/TSCharacters.txt"


def read_mapping(path: Path) -> dict[str, tuple[str, ...]]:
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith("#"):
            continue
        source, choices = line.split("\t")
        targets = tuple(choices.split())
        if len(source) != 1 or not targets or any(len(target) != 1 for target in targets):
            raise ValueError(f"not a single-character mapping: {line!r}")
        result[source] = targets
    return result


def build(source: Path, target: Path, mapping: dict[str, tuple[str, ...]],
          glyphs: dict[int, tuple[int, tuple[int, ...]]]) -> dict[str, object]:
    if source.resolve() == target.resolve():
        raise ValueError("refusing to overwrite the Traditional source bank")
    data = bytearray(source.read_bytes())
    magic, version, width, height, ascii_width, slots, stride, ascii_at, dbcs_at, valid = HEADER.unpack_from(data)
    geometry = {14: (14, 7), 10: (12, 6), 8: (10, 5)}
    if height not in geometry or (magic, version, width, ascii_width, stride) != (
        f"CH{height:02d}".encode(), 1, *geometry[height], height * 2
    ) or len(data) != dbcs_at + slots * stride:
        raise ValueError(f"unexpected source bank layout: {source}")

    stats: dict[str, object] = {"bank": target.name, "big5_slots": 0,
                                "mapped_to_simplified": 0, "alternate_choice": 0,
                                "unchanged": 0, "missing_simplified_glyph": []}
    missing: list[str] = stats["missing_simplified_glyph"]  # type: ignore[assignment]
    for lead in range(0x81, 0xFF):
        for trail in TRAILS:
            pair = bytes((lead, trail))
            try:
                char = pair.decode("cp950")
            except UnicodeDecodeError:
                continue
            if len(char) != 1:
                continue
            stats["big5_slots"] += 1
            choices = mapping.get(char, (char,))
            if choices[0] == char:
                stats["unchanged"] += 1
                continue
            simplified = next((choice for choice in choices if ord(choice) in glyphs), choices[0])
            glyph = glyphs.get(ord(simplified))
            if glyph is None:
                missing.append(f"{lead:02X}{trail:02X} U+{ord(char):04X} -> U+{ord(simplified):04X}")
                continue
            slot = big5_slot(lead, trail)
            assert slot is not None
            at = dbcs_at + slot * stride
            data[at:at + stride] = pack_dbcs(hint_glyph(*glyph, width, height), width)
            stats["mapped_to_simplified"] += 1
            if simplified != choices[0]:
                stats["alternate_choice"] += 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--heights", type=int, nargs="+", choices=(14, 10, 8),
                        default=(10, 8), help="banks to build (default: 10 8)")
    args = parser.parse_args()
    mapping = read_mapping(DICTIONARY)
    glyphs = read_unifont(SOURCES)
    reports = []
    for height in args.heights:
        source = args.source_dir / f"CHCGA{height:02d}.FNT"
        target = args.output_dir / f"SCGA{height:02d}.FNT"
        reports.append(build(source, target, mapping, glyphs))
    report = {"dictionary": "OpenCC TSCharacters.txt; first drawable choice per character",
              "source_files_are_unmodified": True, "banks": reports}
    (args.output_dir / "FONTMAP.JSON").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in reports:
        print(item["bank"], "changed", item["mapped_to_simplified"],
              "missing", len(item["missing_simplified_glyph"]))


if __name__ == "__main__":
    main()
