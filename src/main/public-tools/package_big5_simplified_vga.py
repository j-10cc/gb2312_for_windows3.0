"""Assemble a local-only reversible WIFE bitmap package for VGA installs."""

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
import json
from pathlib import Path
import shutil


def script(prefix: str, label: str) -> bytes:
    lines = ["@ECHO OFF",
             f"IF NOT EXIST {prefix}FSUNG.FON GOTO NOFILES",
             f"IF NOT EXIST {prefix}FSUNG16.B5Q GOTO NOFILES",
             f"IF NOT EXIST {prefix}FSUNG20.B5Q GOTO NOFILES",
             f"COPY /B {prefix}FSUNG.FON C:\\WINDOWS\\SYSTEM\\CFSUNG.FON",
             "IF ERRORLEVEL 1 GOTO FAILED",
             f"COPY /B {prefix}FSUNG16.B5Q C:\\WINDOWS\\SYSTEM\\CFSUNG16.B5Q",
             "IF ERRORLEVEL 1 GOTO FAILED",
             f"COPY /B {prefix}FSUNG20.B5Q C:\\WINDOWS\\SYSTEM\\CFSUNG20.B5Q",
             "IF ERRORLEVEL 1 GOTO FAILED",
             f"ECHO {label} VGA WIFE bitmap files installed.",
             "GOTO END",
             ":NOFILES", "ECHO Run from the complete package directory.", "GOTO END",
             ":FAILED", "ECHO Copy failed. Run TRAD.BAT to restore the original files.",
             ":END"]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_system", type=Path)
    p.add_argument("generated_dir", type=Path)
    p.add_argument("package_dir", type=Path)
    args = p.parse_args()
    target = args.package_dir
    if target.resolve() == args.original_system.resolve():
        raise ValueError("package directory must be separate from the original Windows system")
    target.mkdir(parents=True, exist_ok=True)
    original_fon = args.original_system / "CFSUNG.FON"
    simplified_fon = args.generated_dir / "SFSUNG.FON"
    shutil.copyfile(original_fon, target / "TFSUNG.FON")
    if simplified_fon.resolve() != (target / simplified_fon.name).resolve():
        shutil.copyfile(simplified_fon, target / simplified_fon.name)
    elif not simplified_fon.is_file():
        raise FileNotFoundError(simplified_fon)
    for size in (16, 20):
        original = args.original_system / f"CFSUNG{size}.B5Q"
        simplified = args.generated_dir / f"SFSUNG{size}.B5Q"
        shutil.copyfile(original, target / f"TFSUNG{size}.B5Q")
        if simplified.resolve() != (target / simplified.name).resolve():
            shutil.copyfile(simplified, target / simplified.name)
        elif not simplified.is_file():
            raise FileNotFoundError(simplified)
    (target / "SIMP.BAT").write_bytes(script("S", "Simplified Big5"))
    (target / "TRAD.BAT").write_bytes(script("T", "Traditional Big5"))
    hashes = {item.name: hashlib.sha256(item.read_bytes()).hexdigest()
              for item in sorted(target.iterdir()) if item.suffix.upper() in (".B5Q", ".FON")}
    (target / "SHA256.JSON").write_text(json.dumps(hashes, indent=2) + "\n", encoding="ascii")
    print(json.dumps(hashes, indent=2))


if __name__ == "__main__":
    main()
