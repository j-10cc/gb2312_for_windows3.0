"""Build a writable, GB2312-patched copy of the original Windows 3 Setup media.

The original Setup remains responsible for program groups and machine settings.
The media must be prepared for its chosen destination before Setup is started.
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


import hashlib
import json
import shutil
from pathlib import Path

from build_distribution import HERE, ROOT, FONTS, PATCHED
from build_resources import MODULES
from paginate_cga_menus import MODULES as CGA_MENU_MODULES
from patch_resources import patch

sys_path = ROOT / "src/main/public-tools"
from sys import path as python_path
python_path.insert(0, str(sys_path))
from patch_setup_cga import REQUIRED_ENGLISH, patch_setup  # noqa: E402


SOURCE = ROOT / "src/test/native-gb2312/work/build/expanded/chinese"
ENGLISH = ROOT / "external/media/windows/windows30a"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/GB2312-SETUP"
CGA_MENU_COPIES = tuple(
    b'IF "%1"=="CGA" COPY ' + (Path(name).stem + ".CGA").encode("ascii") +
    (b" %2\\SYSTEM\\" if name.endswith(".DLL") else b" %2\\") +
    name.encode("ascii") + b" > NUL"
    for name in CGA_MENU_MODULES
)
CGA_MENU_CHECKS = tuple(b"IF ERRORLEVEL 1 GOTO FAILED" for _ in CGA_MENU_MODULES)


def cga_menu_commands() -> tuple[bytes, ...]:
    commands = []
    for copy, check in zip(CGA_MENU_COPIES, CGA_MENU_CHECKS):
        commands.extend((copy, check))
    return tuple(commands)

INSTALL = b"\r\n".join((
    b"@ECHO OFF",
    b"IF \"%1\"==\"CGA\" GOTO MODEOK",
    b"IF \"%1\"==\"VGA\" GOTO MODEOK",
    b"ECHO Usage: INSTALL CGA D:\\WINDOWS or INSTALL VGA D:\\WINDOWS",
    b"GOTO END",
    b":MODEOK",
    b"IF \"%2\"==\"\" GOTO END",
    b"IF NOT EXIST GBPATH.EXE GOTO BADMEDIA",
    b"IF NOT EXIST SETUP.EXE GOTO BADMEDIA",
    b"IF NOT EXIST SETUP.INF GOTO BADMEDIA",
    b"IF NOT EXIST FINSTALL.DLL GOTO BADMEDIA",
    b"IF NOT EXIST WINNLS.DLL GOTO BADMEDIA",
    b"GBPATH CHECK %2",
    b"IF ERRORLEVEL 1 GOTO BADTARGET",
    b"COPY SETUP.INF SETUP.BAK > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"GBPATH MEDIA %1 %2",
    b"IF NOT EXIST GBMED.OK GOTO FAILED",
    b"MD %2",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"MD %2\\SYSTEM",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG.FON %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG16.B5Q %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"VGA\" COPY CVDDCVGA.386 %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"CGA\" GOTO CGAFONT",
    b"GOTO RUNSETUP",
    b":CGAFONT",
    b"COPY CHCGA10.FNT %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CHCGA12.FNT %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CGAS12.FON %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CHCGA08.FNT %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b":RUNSETUP",
    b"GBPATH SAVESRC %2",
    b"IF NOT EXIST %2\\GBSRC.BAT GOTO FAILED",
    b"ECHO Running Windows Setup. Keep destination %2.",
    b"SETUP",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"CALL %2\\GBSRC.BAT",
    b"GBPATH SOURCE %2",
    b"IF NOT EXIST %2\\GBSRC.OK GOTO BADMEDIA",
    b"IF NOT EXIST %2\\WIN.COM GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\SYSTEM.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\WIN.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\PROGMAN.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\*.GRP GOTO INCOMPLETE",
    b"COPY PHON.IME %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WINNLS.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF EXIST %2\\WINNLS.DLL COPY WINNLS.DLL %2 > NUL",
    b"COPY GBPY.DAT %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY IMEINFO.INI %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WINIME.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CHAJEI.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY QUICK.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WIFEMAN.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY FINSTALL.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG.FON %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG16.B5Q %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG20.B5Q %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"VGA\" COPY CVDDCVGA.386 %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"CGA\" COPY CGA.DRV %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b'IF "%1"=="CGA" GBPATH CGAOK %2',
    b'IF "%1"=="CGA" IF NOT EXIST %2\\GBCGA.OK GOTO FAILED',
    *cga_menu_commands(),
    b"GBPATH PATCH %1 %2",
    b"IF NOT EXIST %2\\GBPCH.OK GOTO FAILED",
    b"COPY %2\\PHON.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"GBPATH WIFE %2",
    b"IF NOT EXIST %2\\GBWIF.OK GOTO FAILED",
    b"IF \"%1\"==\"CGA\" GBPATH LAYOUT CGA %2",
    b"IF \"%1\"==\"CGA\" IF NOT EXIST %2\\GBLAY.OK GOTO FAILED",
    b"ECHO Setup and GB2312 finalization finished at %2.",
    b"GOTO END",
    b":INCOMPLETE",
    b"ECHO Setup has not completed its Windows phase or used a different directory.",
    b"ECHO Finish Setup and then run FINALIZE %1 %2.",
    b"GOTO END",
    b":BADMEDIA",
    b"ECHO Setup media is incomplete.",
    b"GOTO END",
    b":BADTARGET",
    b"ECHO Destination must be a new absolute DOS 8.3 directory.",
    b"GOTO END",
    b":FAILED",
    b"ECHO Installation incomplete. Keep the target and inspect Setup output.",
    b":END",
    b"",
))

FINALIZE = b"\r\n".join((
    b"@ECHO OFF",
    b"IF \"%1\"==\"CGA\" GOTO MODEOK",
    b"IF \"%1\"==\"VGA\" GOTO MODEOK",
    b"ECHO Usage: FINALIZE CGA D:\\WINDOWS or FINALIZE VGA D:\\WINDOWS",
    b"GOTO END",
    b":MODEOK",
    b"IF \"%2\"==\"\" GOTO END",
    b"IF NOT EXIST GBPATH.EXE GOTO BADMEDIA",
    b"IF NOT EXIST FINSTALL.DLL GOTO BADMEDIA",
    b"IF NOT EXIST WINNLS.DLL GOTO BADMEDIA",
    b"GBPATH SOURCE %2",
    b"IF NOT EXIST %2\\GBSRC.OK GOTO BADMEDIA",
    b"IF NOT EXIST %2\\WIN.COM GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\SYSTEM.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\WIN.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\PROGMAN.INI GOTO INCOMPLETE",
    b"IF NOT EXIST %2\\*.GRP GOTO INCOMPLETE",
    b"COPY PHON.IME %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WINNLS.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF EXIST %2\\WINNLS.DLL COPY WINNLS.DLL %2 > NUL",
    b"COPY GBPY.DAT %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY IMEINFO.INI %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WINIME.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CHAJEI.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY QUICK.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY WIFEMAN.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY FINSTALL.DLL %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG.FON %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG16.B5Q %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY CFSUNG20.B5Q %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"VGA\" COPY CVDDCVGA.386 %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"CGA\" COPY CGA.DRV %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"CGA\" COPY CGAS12.FON %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b'IF "%1"=="CGA" COPY CHCGA12.FNT %2\\SYSTEM > NUL',
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b'IF "%1"=="CGA" COPY CHCGA10.FNT %2\\SYSTEM > NUL',
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b'IF "%1"=="CGA" COPY CHCGA08.FNT %2\\SYSTEM > NUL',
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b'IF "%1"=="CGA" GBPATH CGAOK %2',
    b'IF "%1"=="CGA" IF NOT EXIST %2\\GBCGA.OK GOTO FAILED',
    *cga_menu_commands(),
    b"GBPATH PATCH %1 %2",
    b"IF NOT EXIST %2\\GBPCH.OK GOTO FAILED",
    b"COPY %2\\PHON.IME %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"GBPATH WIFE %2",
    b"IF NOT EXIST %2\\GBWIF.OK GOTO FAILED",
    b"IF \"%1\"==\"CGA\" GBPATH LAYOUT CGA %2",
    b"IF \"%1\"==\"CGA\" IF NOT EXIST %2\\GBLAY.OK GOTO FAILED",
    b"ECHO GB2312 finalization finished at %2.",
    b"GOTO END",
    b":INCOMPLETE",
    b"ECHO Original Windows Setup has not finished at the requested directory.",
    b"GOTO END",
    b":BADMEDIA",
    b"ECHO Change to the complete Setup medium and rerun FINALIZE.",
    b"GOTO END",
    b":FAILED",
    b"ECHO GB2312 finalization failed.",
    b":END",
    b"",
))


def main() -> None:
    if OUT.exists():
        resolved = OUT.resolve()
        if resolved.parent != (_LAYOUT_ROOT / "src/test/native-gb2312/work/build").resolve():
            raise ValueError("refusing to remove directory outside build")
        shutil.rmtree(resolved)
    OUT.mkdir(parents=True)
    for source in SOURCE.iterdir():
        if source.is_file():
            shutil.copy2(source, OUT / source.name)
    for name in REQUIRED_ENGLISH:
        source = ENGLISH / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, OUT / name)
    for name in MODULES:
        source = PATCHED / name
        if not source.is_file() or not (OUT / name).is_file():
            raise FileNotFoundError(name)
        shutil.copy2(source, OUT / name)
    shutil.copy2(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/ime/WINNLS.DLL", OUT / "WINNLS.DLL")
    for name in CGA_MENU_MODULES:
        variant = Path(name).stem + ".CGA"
        shutil.copy2(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/cga-menus" / variant, OUT / variant)
    # The converter must see the GB2312 ordinal code patch as its source.
    fod = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patches/CFFONT.FOD"
    report = patch(fod, OUT / "CFFONT.FOD")
    if report["skipped_non_big5_fields"]:
        raise ValueError("CFFONT.FOD has unconverted text fields")
    for name in ("CFSUNG.FON", "CFSUNG16.B5Q", "CFSUNG20.B5Q",
                 "CHCGA08.FNT", "CHCGA10.FNT", "CHCGA12.FNT", "CGAS12.FON"):
        shutil.copy2(FONTS / name, OUT / name)
    shutil.copy2(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/driver/CGA.DRV", OUT / "CGA.DRV")
    for name in ("PHON.IME", "GBPY.DAT", "IMEINFO.INI", "WIFEMAN.INI", "WIFERM.INI"):
        shutil.copy2(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/ime" / name, OUT / name)
    setup = (_LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup/SETUP.INF").read_bytes()
    setup = patch_setup(setup)
    # The source disks contain four fragments of the outline font.  Our
    # replacement is already a complete sfnt; Setup must not append FO1-FO3.
    font_begin = setup.index(b"[chinese.fon]\r\n")
    font_end = setup.index(b"\r\n[windows]\r\n", font_begin)
    font_section = b"\r\n".join((
        b"[chinese.fon]",
        b"   1:cfsung16.b5q,   cfsung16.b5q,    1",
        b"   1:cfsung.fon,     cfsung.fon,      1",
        b"   1:cfsung20.b5q,   cfsung20.b5q,    1",
        b"",
    ))
    setup = setup[:font_begin] + font_section + setup[font_end:]
    marker = b"[windows]\r\n"
    if setup.count(marker) != 1:
        raise ValueError("unexpected Setup [windows] section")
    setup = setup.replace(marker, marker + b"    1:gbpy.dat\r\n", 1)
    # Replace the Taiwan-only country profile carried over from the original
    # Traditional Chinese edition. Setup uses this table for WIN.INI defaults.
    country_marker = b"886!0!0!2!0!1!0!2!1!0!AM!PM!NT$"
    if setup.count(country_marker) != 1:
        raise ValueError("expected one original Taiwan country profile")
    country_at = setup.index(country_marker)
    country_begin = setup.rfind(b"\r\n", 0, country_at) + 2
    country_end = setup.index(b"\r\n", country_at)
    setup = (setup[:country_begin] + b'"' + "中国".encode("gb2312") +
             b'",            "86!0!0!2!0!1!0!2!1!0!AM!PM!RMB!,!.!/!:!,!M/d/yy!yyyy MMMM dd!ENG"' +
             setup[country_end:])
    setup.decode("gb2312")
    (OUT / "SETUP.INF").write_bytes(setup)
    for name in ("WIN.SRC", "README.TXT", "ETEN.TXT"):
        shutil.copy2(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup" / name, OUT / name)
    win_src = (OUT / "WIN.SRC").read_bytes()
    country_begin = win_src.index(b"sCountry=")
    country_end = win_src.index(b"\r\n", country_begin)
    win_src = (win_src[:country_begin] + b"sCountry=" +
               "中国".encode("gb2312") + win_src[country_end:])
    if win_src.count(b"iCountry=886") != 1 or win_src.count(b"sCurrency=NT$") != 1:
        raise ValueError("original WIN.SRC country defaults changed")
    win_src = win_src.replace(b"iCountry=886", b"iCountry=86")
    win_src = win_src.replace(b"sCurrency=NT$", b"sCurrency=RMB")
    win_src.decode("gb2312")
    (OUT / "WIN.SRC").write_bytes(win_src)
    shutil.copy2(_LAYOUT_ROOT / "src/test/install/work/build/windows/GBPATH.EXE", OUT / "GBPATH.EXE")
    (OUT / "INSTALL.BAT").write_bytes(INSTALL)
    (OUT / "FINALIZE.BAT").write_bytes(FINALIZE)
    (OUT / "INSTALL.TXT").write_bytes(b"\r\n".join((
        b"GB2312 Windows 3.0a Setup media - experimental build",
        b"Copy this entire directory to writable DOS media first.",
        b"DO NOT run SETUP.EXE directly: it skips path and UI finalization.",
        b"Run INSTALL CGA E:\\WIN30GB on HP 200LX, or",
        b"run INSTALL VGA E:\\WIN30GB on a VGA computer.",
        b"Choose the same destination in Windows Setup if prompted.",
        b"Original Setup performs hardware choices and creates program groups.",
        b"Run INSTALL or FINALIZE from the medium directory, not from WINDOWS.",
        b"Example repair: copy the complete new medium to C:\\WIN3A, then run",
        b"C: followed by CD \\WIN3A and FINALIZE VGA C:\\WINDOWS.",
        b"If an older install said 'File cannot be copied onto itself',",
        b"its final success message was false. Run this new FINALIZE.",
        b"If Setup leaves Windows before finishing, complete it and run",
        b"FINALIZE CGA E:\\WIN30GB or FINALIZE VGA E:\\WIN30GB.",
        b"If SETUP.EXE was run directly, exit Windows to DOS, copy this",
        b"updated medium to a writable DOS directory, then run FINALIZE",
        b"VGA C:\\WINDOWS (or CGA plus the actual installed path).",
        b"If an older FINALIZE caused a logo-then-DOS exit, rerun",
        b"FINALIZE from this complete updated medium before starting WIN.",
        b"After installation, change to the selected directory and run WIN /R.",
        b"Use a fresh copy of this media for another destination.",
        b"",
    )))
    files = {path.name: {"size": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in sorted(OUT.iterdir()) if path.is_file()}
    (OUT / "MANIFEST.TXT").write_text(json.dumps({"files": files}, indent=2) + "\n")
    print(f"{OUT}: {len(files)} files, {sum(x['size'] for x in files.values())} bytes")


if __name__ == "__main__":
    main()
