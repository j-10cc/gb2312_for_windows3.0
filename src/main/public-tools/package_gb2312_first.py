"""Assemble the reversible Windows 3.0 CGA/real-mode GB2312 first release."""

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
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from build_gb2312_cga import build


ROOT = _LAYOUT_ROOT
PACKAGE = ROOT / "src/test/native-gb2312/work/build/GB2312-CGA-FIRST"
ALL_PACKAGE = ROOT / "src/test/native-gb2312/work/build/GB2312-ALL-MODES"


def dos_file(path: Path, content: str) -> None:
    path.write_bytes(content.replace("\n", "\r\n").encode("ascii"))


def main() -> None:
    PACKAGE.mkdir(parents=True, exist_ok=True)
    for height, width in ((10, 12), (8, 10)):
        path = PACKAGE / f"CHCGA{height:02d}.FNT"
        valid, missing = build(path, height, width)
        if (valid, missing) != (7445, 0):
            raise ValueError(f"Incomplete GB2312 bank: {path}")
    for source, target in (
        (ROOT / "src/test/native-gb2312/work/build/GBCGA10.DRV", PACKAGE / "CGA.DRV"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBEDIT.EXE", PACKAGE / "GBEDIT.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBIME.EXE", PACKAGE / "GBIME.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBPBRUN.EXE", PACKAGE / "GBPBRUN.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBWRUN.EXE", PACKAGE / "GBWRUN.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBSHELL.EXE", PACKAGE / "GBSHELL.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBRUN.EXE", PACKAGE / "GBRUN.EXE"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBIMED.DLL", PACKAGE / "GBIMED.DLL"),
        (ROOT / "src/test/native-gb2312/gb2312_first/GBKBCFG.EXE", PACKAGE / "GBKBCFG.EXE"),
        (ROOT / "src/test/native-gb2312/work/build/GB2312-APP/GB10.FNT", PACKAGE / "GB10.FNT"),
        (ROOT / "src/test/native-gb2312/work/build/GB2312-APP/GB16.FNT", PACKAGE / "GB16.FNT"),
        (ROOT / "src/test/native-gb2312/work/build/GB2312-APP/GBPY.DAT", PACKAGE / "GBPY.DAT"),
        (ROOT / "external/licenses/OFL-1.1.txt", PACKAGE / "OFL.TXT"),
        (ROOT / "external/licenses/UNIFONT-COPYING.txt", PACKAGE / "FONTSRC.TXT"),
        (ROOT / "external/licenses/UNICODE-LICENSE.txt", PACKAGE / "UNICODE.TXT"),
    ):
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, target)
    dos_file(PACKAGE / "INSTALL.BAT", """@ECHO OFF
IF NOT EXIST C:\\WINDOWS\\SYSTEM.INI GOTO NOWINDOWS
IF NOT EXIST C:\\WINDOWS\\SYSTEM\\CGA.DRV GOTO NOWINDOWS
IF EXIST C:\\WINDOWS\\SYSTEM\\GB3ORG.DRV GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\CHCGA10.FNT GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\CHCGA08.FNT GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\GB10.FNT GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\GB16.FNT GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\GBPY.DAT GOTO CONFLICT
IF EXIST C:\\WINDOWS\\SYSTEM\\GBIMED.DLL GOTO CONFLICT
IF EXIST C:\\WINDOWS\\GBEDIT.EXE GOTO CONFLICT
IF EXIST C:\\WINDOWS\\GBIME.EXE GOTO CONFLICT
COPY /B C:\\WINDOWS\\SYSTEM\\CGA.DRV C:\\WINDOWS\\SYSTEM\\GB3ORG.DRV
IF ERRORLEVEL 1 GOTO FAILED
COPY /B CHCGA10.FNT C:\\WINDOWS\\SYSTEM\\CHCGA10.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B CHCGA08.FNT C:\\WINDOWS\\SYSTEM\\CHCGA08.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B CGA.DRV C:\\WINDOWS\\SYSTEM\\CGA.DRV
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GB10.FNT C:\\WINDOWS\\SYSTEM\\GB10.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GB16.FNT C:\\WINDOWS\\SYSTEM\\GB16.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBPY.DAT C:\\WINDOWS\\SYSTEM\\GBPY.DAT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBIMED.DLL C:\\WINDOWS\\SYSTEM\\GBIMED.DLL
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBEDIT.EXE C:\\WINDOWS\\GBEDIT.EXE
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBSHELL.EXE C:\\WINDOWS\\GBSHELL.EXE
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBRUN.EXE C:\\WINDOWS\\GBRUN.EXE
IF ERRORLEVEL 1 GOTO FAILED
ECHO GB2312 installed. Use WIN /R; run GBEDIT from Windows.
GOTO END
:NOWINDOWS
ECHO C:\\WINDOWS with an existing CGA.DRV is required.
GOTO END
:CONFLICT
ECHO Existing addon files found. No files changed.
GOTO END
:FAILED
ECHO Copy failed. Run REMOVE.BAT after checking copied files.
:END
""")
    dos_file(PACKAGE / "REMOVE.BAT", """@ECHO OFF
IF NOT EXIST C:\\WINDOWS\\SYSTEM\\GB3ORG.DRV GOTO NOBACKUP
COPY /B C:\\WINDOWS\\SYSTEM\\GB3ORG.DRV C:\\WINDOWS\\SYSTEM\\CGA.DRV
IF ERRORLEVEL 1 GOTO FAILED
DEL C:\\WINDOWS\\SYSTEM\\GB3ORG.DRV
DEL C:\\WINDOWS\\SYSTEM\\CHCGA10.FNT
DEL C:\\WINDOWS\\SYSTEM\\CHCGA08.FNT
DEL C:\\WINDOWS\\SYSTEM\\GB10.FNT
DEL C:\\WINDOWS\\SYSTEM\\GB16.FNT
DEL C:\\WINDOWS\\SYSTEM\\GBPY.DAT
DEL C:\\WINDOWS\\SYSTEM\\GBIMED.DLL
DEL C:\\WINDOWS\\GBEDIT.EXE
DEL C:\\WINDOWS\\GBSHELL.EXE
DEL C:\\WINDOWS\\GBRUN.EXE
ECHO Original CGA driver restored.
GOTO END
:NOBACKUP
ECHO No GB3ORG.DRV backup found. No files changed.
GOTO END
:FAILED
ECHO Restore failed; addon files left in place.
:END
""")
    dos_file(PACKAGE / "INSTALLA.BAT", """@ECHO OFF
IF "%1"=="" GOTO AUTO
SET GB3ROOT=%1
GOTO START
:AUTO
IF EXIST A:\\WINDOWS\\SYSTEM.INI GOTO AUTOCHECK
IF EXIST C:\\WINDOWS\\SYSTEM.INI GOTO USEC
GOTO NOWINDOWS
:AUTOCHECK
IF EXIST C:\\WINDOWS\\SYSTEM.INI GOTO CHOOSE
SET GB3ROOT=A:\\WINDOWS
GOTO START
:USEC
SET GB3ROOT=C:\\WINDOWS
:START
IF NOT EXIST %GB3ROOT%\\SYSTEM.INI GOTO NOWINDOWS
IF NOT EXIST %GB3ROOT%\\SYSTEM\\KEYBOARD.DRV GOTO NOWINDOWS
IF NOT EXIST %GB3ROOT%\\PBRUSH.EXE GOTO NOWINDOWS
IF NOT EXIST %GB3ROOT%\\WRITE.EXE GOTO NOWINDOWS
IF EXIST %GB3ROOT%\\PBRUSHO.EXE GOTO CONFLICT
IF EXIST %GB3ROOT%\\WRITEOR.EXE GOTO CONFLICT
IF EXIST %GB3ROOT%\\SYSTEM\\GBKBD.DRV GOTO CONFLICT
IF EXIST %GB3ROOT%\\GB3SYS.BAK GOTO BACKUPCONFLICT
IF EXIST %GB3ROOT%\\SYSTEM\\GB10.FNT GOTO CONFLICT
IF EXIST %GB3ROOT%\\SYSTEM\\GB16.FNT GOTO CONFLICT
IF EXIST %GB3ROOT%\\SYSTEM\\GBPY.DAT GOTO CONFLICT
IF EXIST %GB3ROOT%\\SYSTEM\\GBIMED.DLL GOTO CONFLICT
IF EXIST %GB3ROOT%\\GBEDIT.EXE GOTO CONFLICT
IF EXIST %GB3ROOT%\\GBIME.EXE GOTO CONFLICT
GBKBCFG.EXE /install %GB3ROOT%
IF ERRORLEVEL 1 GOTO CFGFAILED
COPY /B GB10.FNT %GB3ROOT%\\SYSTEM\\GB10.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GB16.FNT %GB3ROOT%\\SYSTEM\\GB16.FNT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBPY.DAT %GB3ROOT%\\SYSTEM\\GBPY.DAT
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBIMED.DLL %GB3ROOT%\\SYSTEM\\GBIMED.DLL
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBEDIT.EXE %GB3ROOT%\\GBEDIT.EXE
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBIME.EXE %GB3ROOT%\\GBIME.EXE
IF ERRORLEVEL 1 GOTO FAILED
REN %GB3ROOT%\\PBRUSH.EXE PBRUSHO.EXE
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBPBRUN.EXE %GB3ROOT%\\PBRUSH.EXE
IF ERRORLEVEL 1 GOTO FAILED
REN %GB3ROOT%\\WRITE.EXE WRITEOR.EXE
IF ERRORLEVEL 1 GOTO FAILED
COPY /B GBWRUN.EXE %GB3ROOT%\\WRITE.EXE
IF ERRORLEVEL 1 GOTO FAILED
ECHO GB2312 resident IME installed. Run GBIME.EXE in Windows.
GOTO END
:NOWINDOWS
ECHO Windows directory, KEYBOARD.DRV, PBRUSH.EXE and WRITE.EXE are required.
GOTO END
:CHOOSE
ECHO Both A:\\WINDOWS and C:\\WINDOWS exist. Specify INSTALLA A:\\WINDOWS or C:\\WINDOWS.
GOTO END
:CONFLICT
ECHO Existing addon files found. No files changed.
GOTO END
:BACKUPCONFLICT
ECHO GB3SYS.BAK exists. No files changed; keep this recovery copy.
ECHO Run GBKBCFG.EXE /status %GB3ROOT% and inspect SYSTEM.INI.
GOTO END
:CFGFAILED
ECHO Keyboard configuration failed. Read the GBKBCFG error above.
ECHO If GB3SYS.BAK exists, keep it for recovery.
GOTO END
:FAILED
IF EXIST %GB3ROOT%\\WRITEOR.EXE DEL %GB3ROOT%\\WRITE.EXE
IF EXIST %GB3ROOT%\\WRITEOR.EXE REN %GB3ROOT%\\WRITEOR.EXE WRITE.EXE
IF EXIST %GB3ROOT%\\PBRUSHO.EXE DEL %GB3ROOT%\\PBRUSH.EXE
IF EXIST %GB3ROOT%\\PBRUSHO.EXE REN %GB3ROOT%\\PBRUSHO.EXE PBRUSH.EXE
GBKBCFG.EXE /remove %GB3ROOT%
IF ERRORLEVEL 1 GOTO ROLLBACKCFGFAIL
DEL %GB3ROOT%\\GBEDIT.EXE
DEL %GB3ROOT%\\GBIME.EXE
DEL %GB3ROOT%\\SYSTEM\\GB10.FNT
DEL %GB3ROOT%\\SYSTEM\\GB16.FNT
DEL %GB3ROOT%\\SYSTEM\\GBPY.DAT
DEL %GB3ROOT%\\SYSTEM\\GBIMED.DLL
ECHO Copy failed. Installed files rolled back.
GOTO END
:ROLLBACKCFGFAIL
ECHO Keyboard rollback failed. Keep GB3SYS.BAK and review SYSTEM.INI.
:END
SET GB3ROOT=
""")
    dos_file(PACKAGE / "REMOVEA.BAT", """@ECHO OFF
IF "%1"=="" GOTO AUTO
SET GB3ROOT=%1
GOTO START
:AUTO
IF EXIST A:\\WINDOWS\\GBIME.EXE GOTO AUTOCHECK
IF EXIST C:\\WINDOWS\\GBIME.EXE GOTO USEC
GOTO MISSING
:AUTOCHECK
IF EXIST C:\\WINDOWS\\GBIME.EXE GOTO CHOOSE
SET GB3ROOT=A:\\WINDOWS
GOTO START
:USEC
SET GB3ROOT=C:\\WINDOWS
:START
IF NOT EXIST %GB3ROOT%\\GBIME.EXE GOTO MISSING
IF NOT EXIST %GB3ROOT%\\PBRUSHO.EXE GOTO FAILED
IF NOT EXIST %GB3ROOT%\\WRITEOR.EXE GOTO FAILED
GBKBCFG.EXE /remove %GB3ROOT%
IF ERRORLEVEL 1 GOTO FAILED
DEL %GB3ROOT%\\WRITE.EXE
REN %GB3ROOT%\\WRITEOR.EXE WRITE.EXE
IF ERRORLEVEL 1 GOTO FAILED
DEL %GB3ROOT%\\PBRUSH.EXE
REN %GB3ROOT%\\PBRUSHO.EXE PBRUSH.EXE
IF ERRORLEVEL 1 GOTO FAILED
DEL %GB3ROOT%\\GBEDIT.EXE
DEL %GB3ROOT%\\GBIME.EXE
DEL %GB3ROOT%\\SYSTEM\\GB10.FNT
DEL %GB3ROOT%\\SYSTEM\\GB16.FNT
DEL %GB3ROOT%\\SYSTEM\\GBPY.DAT
DEL %GB3ROOT%\\SYSTEM\\GBIMED.DLL
IF EXIST %GB3ROOT%\\GBFN.CCH DEL %GB3ROOT%\\GBFN.CCH
IF EXIST %GB3ROOT%\\GBSTATE.DAT DEL %GB3ROOT%\\GBSTATE.DAT
ECHO GB2312 apps removed.
GOTO END
:MISSING
ECHO GB2312 IME not found. No files changed.
GOTO END
:CHOOSE
ECHO Both A:\\WINDOWS and C:\\WINDOWS have GBIME.EXE. Specify REMOVEA A:\\WINDOWS or C:\\WINDOWS.
GOTO END
:FAILED
ECHO Keyboard configuration could not be removed.
:END
SET GB3ROOT=
""")
    manifest = []
    for path in sorted(PACKAGE.iterdir()):
        if path.is_file() and path.name != "SHA256.TXT":
            manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (PACKAGE / "SHA256.TXT").write_text("\n".join(manifest) + "\n", encoding="ascii")
    ALL_PACKAGE.mkdir(parents=True, exist_ok=True)
    for name in ("GB10.FNT", "GB16.FNT", "GBPY.DAT", "GBIMED.DLL", "GBEDIT.EXE",
                 "GBIME.EXE", "GBPBRUN.EXE", "GBWRUN.EXE", "GBKBCFG.EXE", "INSTALLA.BAT", "REMOVEA.BAT", "OFL.TXT",
                 "FONTSRC.TXT", "UNICODE.TXT"):
        shutil.copy2(PACKAGE / name, ALL_PACKAGE / name)
    for obsolete in ("GBSHELL.EXE", "GBRUN.EXE"):
        (ALL_PACKAGE / obsolete).unlink(missing_ok=True)
    dos_file(ALL_PACKAGE / "README.TXT", """Windows 3.0 GB2312 resident Chinese support addon.
Run INSTALLA.BAT A:\\WINDOWS or INSTALLA.BAT C:\\WINDOWS from DOS.
In Windows run GBIME.EXE from its Windows directory.
Run REMOVEA.BAT with the same Windows directory to uninstall.
The installer verifies one English 3.0a KEYBOARD.DRV image. If rejected,
keep the original driver and copy its size and CRC32 for diagnosis.
GBKBCFG.EXE /status A:\\WINDOWS reports the configuration without edits.
Standard EDIT controls support GB2312 pinyin input and display.
F1 toggles input; F2 enters quwei. GBEDIT.EXE is an optional editor.
Original app title, common menus and EDIT text are translated at runtime.
Standard file lists and File Manager GB2312 names are drawn by the addon.
GBKBCFG.EXE generates a GB2312 keyboard driver for DOS file paths.
The original Paintbrush is backed up as PBRUSHO.EXE and opened through
a transparent PBRUSH.EXE launcher in real mode. REMOVEA.BAT restores it.
The original Write is backed up as WRITEOR.EXE. The WRITE.EXE launcher
preloads native WRI text so Chinese can reappear without a GBX file.
In real mode it briefly suspends and restarts the IME while Write starts.
Real-mode Calendar offscreen windows are moved into view by the IME.
Write, Paintbrush and Terminal have application-specific input support.
On compact CGA screens, Chinese icon captions follow the native icon rows.
Menus are arranged once; narrow windows wrap into native menu rows.
File Manager refreshes Chinese names when its directory snapshot changes.
""")
    all_manifest = []
    for path in sorted(ALL_PACKAGE.iterdir()):
        if path.is_file() and path.name != "SHA256.TXT":
            all_manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (ALL_PACKAGE / "SHA256.TXT").write_text("\n".join(all_manifest) + "\n", encoding="ascii")
    archive = ROOT / "src/test/native-gb2312/work/build/GB2312-ALL-MODES.zip"
    with ZipFile(archive, "w") as zipped:
        for path in sorted(ALL_PACKAGE.iterdir()):
            if not path.is_file():
                continue
            entry = ZipInfo(path.name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            zipped.writestr(entry, path.read_bytes())
    print(PACKAGE)
    print(ALL_PACKAGE)
    print(archive)


if __name__ == "__main__":
    main()
