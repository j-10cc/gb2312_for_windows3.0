"""Create an isolated Windows test image with a replacement CGA display driver."""

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
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("src/main/cga-driver", type=Path)
    parser.add_argument("test_root", type=Path)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    target = args.test_root
    if target.exists():
        parser.error(f"test root already exists: {target}")
    source = args.baseline
    if not (source / "WINDOWS" / "SYSTEM.INI").is_file():
        parser.error(f"not a Windows baseline: {source}")
    if not args.driver.is_file():
        parser.error(f"driver not found: {args.driver}")
    if args.font is not None and not args.font.is_file():
        parser.error(f"font not found: {args.font}")
    shutil.copytree(source, target)
    shutil.copy2(args.driver, target / "WINDOWS" / "SYSTEM" / "CGA.DRV")
    if args.font is not None:
        shutil.copy2(args.font, target / "WINDOWS" / "SYSTEM" / args.font.name)
    (target.parent / f"captures-{target.name.lower()}").mkdir(exist_ok=True)
    print(f"Prepared {target}")


if __name__ == "__main__":
    main()
