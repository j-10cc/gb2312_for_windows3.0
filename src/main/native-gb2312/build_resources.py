"""Build version-recorded GB2312 resource modules from local traditional media."""

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
import json
from pathlib import Path

from patch_resources import RESOURCE_CONTEXT, patch, simplify

from sys import path as python_path
python_path.insert(0, str(_LAYOUT_ROOT / "src/main/public-tools"))
from build_big5_simplified_fonts import DICTIONARY, read_mapping  # noqa: E402

ROOT = _LAYOUT_ROOT
BASE = ROOT / "src/test/native-gb2312/work/build/setup-test/C32/WINDOWS/SYSTEM"
WINDOWS = BASE.parent
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patched"
MODULES = (
    "KERNEL.EXE", "GDI.EXE", "USER.EXE", "SHELL.DLL", "WINNLS.DLL",
    "PROGMAN.EXE", "WINFILE.EXE", "NOTEPAD.EXE", "CALC.EXE",
    "CALENDAR.EXE", "CARDFILE.EXE", "PBRUSH.EXE", "WRITE.EXE",
    "CONTROL.EXE", "CLIPBRD.EXE", "CLOCK.EXE", "PIFEDIT.EXE",
    "PRINTMAN.EXE", "RECORDER.EXE", "REVERSI.EXE", "SOL.EXE",
    "SYSEDIT.EXE", "TASKMAN.EXE", "TERMINAL.EXE", "WINHELP.EXE",
    "WINIME.IME", "PHON.IME", "CHAJEI.IME", "QUICK.IME",
    "USERFONT.EXE", "MSDOS.EXE", "WIFEMAN.DLL", "FINSTALL.DLL",
    "SWAPFILE.EXE", "SETUP.EXE",
    "MSNET.DRV", "CEPSON.DRV", "CHPPCL.DRV", "IBMJ5577.DRV",
)

# One user-facing message in USERFONT lives in an NE data segment, outside
# menu/dialog/string resources.  Keep this exact-byte check separate from the
# resource parser so a different binary cannot be silently modified.
INLINE_FIELDS = {
    "USERFONT.EXE": ((0xAB7C, "記憶體不足，無法繼續執行！"),),
}


def patch_inline(name: str, source: Path, target: Path, report: dict) -> None:
    fields = INLINE_FIELDS.get(name, ())
    if not fields:
        return
    original = source.read_bytes()
    data = bytearray(target.read_bytes())
    mappings = read_mapping(DICTIONARY)
    for offset, text in fields:
        raw = text.encode("cp950")
        if original[offset:offset + len(raw) + 1] != raw + b"\0":
            raise ValueError(f"{name}: inline source string differs at {offset:#x}")
        if data[offset:offset + len(raw) + 1] != raw + b"\0":
            raise ValueError(f"{name}: inline destination overlaps another patch")
        translated, _ = simplify(raw, mappings)
        data[offset:offset + len(raw)] = translated
    target.write_bytes(data)
    report["inline_fields"] = len(fields)
    report["output_sha256"] = hashlib.sha256(data).hexdigest()


def main() -> None:
    results = {}
    for name in MODULES:
        source = (WINDOWS if name.endswith(".IME") else BASE) / name
        if not source.is_file():
            results[name] = {"status": "missing_original"}
            continue
        try:
            report = patch(source, OUT / name)
            patch_inline(name, source, OUT / name, report)
            expected = {key[3] for key in RESOURCE_CONTEXT if key[0] == name}
            actual = [item["from"] for item in report["context_overrides"]]
            if len(actual) != len(expected) or set(actual) != expected:
                raise ValueError(f"resource context overrides did not match for {name}: {actual}")
            expected_raw = 2 if name == "PIFEDIT.EXE" else 0
            if len(report["repaired_non_big5_fields"]) != expected_raw:
                raise ValueError(f"raw resource repairs did not match for {name}")
            results[name] = {"status": "patched", **report}
            print(f"{name}: {report['changed_fields']} text fields")
        except (ValueError, UnicodeDecodeError, IndexError) as error:
            results[name] = {"status": "needs_parser_work", "error": str(error)}
            print(f"{name}: SKIPPED ({error})")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESOURCE-MANIFEST.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
