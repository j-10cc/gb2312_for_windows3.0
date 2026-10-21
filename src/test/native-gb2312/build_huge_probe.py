"""Build a Win16 probe that draws Chinese across a huge CGA bitmap boundary."""

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
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCOM = _LAYOUT_ROOT / "external/open-watcom"


def main() -> None:
    env = os.environ.copy()
    env.update({
        "WATCOM": str(WATCOM),
        "INCLUDE": ";".join((str(WATCOM / "h"), str(WATCOM / "h/win"))),
        "LIB": ";".join((str(WATCOM / "lib286"), str(WATCOM / "lib286/win"))),
        "PATH": str(WATCOM / "binnt64") + os.pathsep + env.get("PATH", ""),
    })
    subprocess.run([str(WATCOM / "binnt64/wcc.exe"), "-0", "-bt=windows",
                    "GBHUGE.C"], cwd=HERE, env=env, check=True)
    subprocess.run([str(WATCOM / "binnt64/wlink.exe"), "system", "windows",
                    "name", "GBHUGE.EXE", "file", "GBHUGE.obj"],
                   cwd=HERE, env=env, check=True)


if __name__ == "__main__":
    main()
