"""Build the Win16 Pinyin edit control and message queue probe."""

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
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WATCOM = _LAYOUT_ROOT / "external/open-watcom"


def main() -> None:
    parser = argparse.ArgumentParser()
    variant = parser.add_mutually_exclusive_group()
    variant.add_argument("--peek", action="store_true")
    variant.add_argument("--visual", action="store_true")
    variant.add_argument("--write", action="store_true")
    variant.add_argument("--native", action="store_true")
    variant.add_argument("--native-review", action="store_true")
    variant.add_argument("--native-write", action="store_true")
    variant.add_argument("--native-write-e", action="store_true")
    args = parser.parse_args()
    env = os.environ.copy()
    env.update({
        "WATCOM": str(WATCOM),
        "INCLUDE": ";".join((str(WATCOM / "h"), str(WATCOM / "h/win"))),
        "LIB": ";".join((str(WATCOM / "lib286"), str(WATCOM / "lib286/win"))),
        "PATH": str(WATCOM / "binnt64") + os.pathsep + env.get("PATH", ""),
    })
    command = [str(WATCOM / "binnt64/wcc.exe"), "-0", "-bt=windows"]
    if args.peek:
        command.append("-dIME_PEEK_TEST")
    if args.native_write_e:
        command.append("-dNATIVE_E")
    source = ("GBNATWRITE.C" if args.native_write or args.native_write_e else
              "GBIMEREG.C" if args.native_review else
              "GBNATST.C" if args.native else "GBPYWRITE.C" if args.write
              else "GBPYVIS.C" if args.visual else "GBPINTST.C")
    source_path = HERE / source
    if not source_path.exists():
        source_path = _LAYOUT_ROOT / "src/main/native-gb2312" / source
    subprocess.run(command + [str(source_path)], cwd=HERE, env=env, check=True)
    subprocess.run([str(WATCOM / "binnt64/wlink.exe"), "system", "windows",
                    "name", ("GBWRI.EXE" if args.native_write_e else "GBNATW.EXE" if args.native_write else "GBIMEREG.EXE" if args.native_review else "GBNATST.EXE" if args.native else "PYWRI.EXE" if args.write else "GBPYVIS.EXE" if args.visual else
                             "GBPEEK.EXE" if args.peek else "GBPINTST.EXE"),
                    "file", "GBNATWRITE.obj" if args.native_write or args.native_write_e else "GBIMEREG.obj" if args.native_review else "GBNATST.obj" if args.native else "GBPYWRITE.obj" if args.write else "GBPYVIS.obj" if args.visual else "GBPINTST.obj"],
                   cwd=HERE, env=env, check=True)


if __name__ == "__main__":
    main()
