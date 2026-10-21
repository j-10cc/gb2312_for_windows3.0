"""Assemble reversible DOS file-swap kit for the experimental CGA driver."""

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


ROOT = _LAYOUT_ROOT


def switch_script(source_prefix: str, display_name: str) -> bytes:
    # ASCII and CRLF keep the script usable in DOS 5 and on the HP 200LX.
    lines = [
        "@ECHO OFF",
        "IF NOT EXIST C:\\WINDOWS\\SYSTEM.INI GOTO NOBASE",
        "IF NOT EXIST C:\\WINDOWS\\SYSTEM\\CGA.DRV GOTO NOBASE",
        f"IF NOT EXIST {source_prefix}CGA10.FNT GOTO NOFILES",
        f"IF NOT EXIST {source_prefix}CGA08.FNT GOTO NOFILES",
        f"COPY /B {source_prefix}CGA10.FNT C:\\WINDOWS\\SYSTEM\\CHCGA10.FNT",
        "IF ERRORLEVEL 1 GOTO FAILED",
        f"COPY /B {source_prefix}CGA08.FNT C:\\WINDOWS\\SYSTEM\\CHCGA08.FNT",
        "IF ERRORLEVEL 1 GOTO FAILED",
        f"ECHO {display_name} font files installed. Start Windows with WIN /R.",
        "GOTO END",
        ":NOBASE",
        "ECHO C:\\WINDOWS or CGA.DRV missing. Install the CHCGA driver first.",
        "GOTO END",
        ":NOFILES",
        "ECHO Font bank missing. Run this BAT from its package directory.",
        "GOTO END",
        ":FAILED",
        "ECHO Copy failed. Run TRAD.BAT to restore the Traditional font files.",
        ":END",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    package = args.package_dir
    package.mkdir(parents=True, exist_ok=True)
    for height in (10, 8):
        original = ROOT / "output" / f"CHCGA{height:02d}.FNT"
        target = package / f"TCGA{height:02d}.FNT"
        if original.resolve() == target.resolve():
            raise ValueError("refusing to overwrite the original font")
        shutil.copyfile(original, target)
        if not (package / f"SCGA{height:02d}.FNT").is_file():
            raise FileNotFoundError(package / f"SCGA{height:02d}.FNT")
    (package / "SIMP.BAT").write_bytes(switch_script("S", "Simplified Big5"))
    (package / "TRAD.BAT").write_bytes(switch_script("T", "Traditional Big5"))
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(package.iterdir()) if path.suffix.upper() == ".FNT"}
    (package / "SHA256.JSON").write_text(
        json.dumps(hashes, indent=2) + "\n", encoding="ascii")
    print(json.dumps(hashes, indent=2))


if __name__ == "__main__":
    main()
