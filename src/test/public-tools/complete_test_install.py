"""Complete an isolated Setup test directory using expanded user-owned media.

This fills files omitted from a fast first-stage Setup experiment. It does not
modify either installation source or claim the resulting image is a supported
Windows installation.
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
import re
import shutil
from pathlib import Path


MODULE_SUFFIXES = {".DRV", ".DLL", ".EXE", ".FON", ".FOD", ".B5Q", ".BIN", ".GR2"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expanded_chinese", type=Path)
    parser.add_argument("setup_test_c", type=Path)
    parser.add_argument("destination_c", type=Path)
    args = parser.parse_args()
    if args.destination_c.exists():
        raise FileExistsError(args.destination_c)
    if args.destination_c.resolve() in (args.expanded_chinese.resolve(), args.setup_test_c.resolve()):
        raise ValueError("destination must differ from sources")

    source_ini = (args.setup_test_c / "WINDOWS" / "SYSTEM.INI").read_bytes()
    patched_ini, count = re.subn(rb"(?im)^shell=setup\.exe(?=\r?$)", b"shell=progman.exe", source_ini)
    if count != 1:
        raise ValueError("expected first-stage Setup shell=setup.exe")
    if not (args.setup_test_c / "WINDOWS" / "SYSTEM" / "CFSUNG.FON").is_file():
        raise FileNotFoundError("first-stage image must include the joined CFSUNG.FON")

    shutil.copytree(args.setup_test_c, args.destination_c)
    windows = args.destination_c / "WINDOWS"
    system = windows / "SYSTEM"
    for source in args.expanded_chinese.iterdir():
        if not source.is_file():
            continue
        if source.suffix.upper() in MODULE_SUFFIXES:
            target = system / source.name
            if not target.exists():
                shutil.copy2(source, target)
        elif source.suffix.upper() in {".TBL", ".INI", ".HLP"}:
            target = windows / source.name
            if not target.exists():
                shutil.copy2(source, target)

    ini = windows / "SYSTEM.INI"
    ini.write_bytes(patched_ini)
    (args.destination_c / "RUNWIN.BAT").write_bytes(b"@ECHO OFF\r\nCD \\WINDOWS\r\nWIN /R\r\n")
    print(f"Completed isolated test image at {args.destination_c}")


if __name__ == "__main__":
    main()
