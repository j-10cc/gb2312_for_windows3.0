"""Build the 8086 DOS helper used by the relocatable installer."""

from __future__ import annotations

# Project paths after the src/main + src/test directory reorganization.
import sys as _layout_sys
from pathlib import Path as _LayoutPath
_LAYOUT_ROOT = next(p for p in _LayoutPath(__file__).resolve().parents
                    if (p / "src/main").is_dir() and (p / "release").is_dir())
_layout_sys.path[:0] = [str(_LAYOUT_ROOT / p) for p in (
    "src/main/native-gb2312", "src/main/public-tools", "src/main/cga-driver",
    "src/main/install", "src/main/install/windows", "src/test/install")]


import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCOM = _LAYOUT_ROOT / "external/open-watcom"
OUT = _LAYOUT_ROOT / "src/test/install/work/build/windows/GBPATH.EXE"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "GBPATH.C", OUT.parent / "GBPATH.C")
    env = os.environ.copy()
    env.update({
        "WATCOM": str(WATCOM),
        "INCLUDE": str(WATCOM / "h"),
        "LIB": str(WATCOM / "lib286"),
        "PATH": str(WATCOM / "binnt64") + os.pathsep + env.get("PATH", ""),
    })
    subprocess.run([str(WATCOM / "binnt64/wcc.exe"), "-0", "-bt=dos",
                    "GBPATH.C"], cwd=OUT.parent, env=env, check=True)
    subprocess.run([str(WATCOM / "binnt64/wlink.exe"), "system", "dos",
                    "option", "stack=8192", "name", str(OUT),
                    "file", "GBPATH.obj"],
                   cwd=OUT.parent, env=env, check=True)
    if OUT.read_bytes()[:2] != b"MZ":
        raise ValueError("GBPATH is not a DOS executable")
    print(f"{OUT}: {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
