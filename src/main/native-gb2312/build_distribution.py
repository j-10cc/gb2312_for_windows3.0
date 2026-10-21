"""Assemble an independent, directly installable GB2312 Windows 3.0a tree.

Source media and the existing Windows installation are never modified. The
generated DOS installer accepts CGA or VGA and an absolute DOS destination.
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
import struct
from pathlib import Path

from build_resources import MODULES
from paginate_cga_menus import MODULES as CGA_MENU_MODULES
from patch_resources import patch, simplify
from test_display import BASE, FONTS, HERE, ROOT, configure_system_ini

sys_path = ROOT / "src/main/public-tools"
from sys import path as python_path
python_path.insert(0, str(sys_path))
from build_big5_simplified_fonts import DICTIONARY, read_mapping  # noqa: E402

OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/GB2312-INSTALL"
PATCHED = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patched"
IME = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/ime"
RUNTIME_PATHS = {
    "PHON.IME": (b"C:\\WINDOWS\\GBPY.DAT",
                 b"C:\\WINDOWS\\SYSTEM\\CFSUNG16.B5Q"),
    "CGA.DRV": (b"C:\\WINDOWS\\SYSTEM\\CHCGA12.FNT",
                b"C:\\WINDOWS\\SYSTEM\\CHCGA10.FNT",
                b"C:\\WINDOWS\\SYSTEM\\CHCGA08.FNT"),
}


def check_runtime_slots(data: bytes, name: str) -> None:
    for marker in RUNTIME_PATHS[name]:
        if data.count(marker) != 1:
            raise ValueError(f"expected exactly one relocatable path in {name}: {marker!r}")
        at = data.index(marker) + len(marker)
        if data[at:at + 80 - len(marker)] != bytes(80 - len(marker)):
            raise ValueError(f"relocatable path slot is not 80 bytes in {name}")
REMOVE_ROOT = {
    "CHAJEI.IME", "QUICK.IME", "A15.TBL", "A234.TBL", "ACODE.TBL",
    "PHON.TBL", "PHONPTR.TBL", "PHONCODE.TBL",
    "CFSUNG.FO1", "CFSUNG.FO2", "CFSUNG.FO3",
}
REMOVE_SYSTEM = {"CGA.DRV", "CHCGA.DRV", "CFSUNG.FON", "CFSUNG16.B5Q",
                 "CFSUNG20.B5Q", "DISPATCH-S1.BIN"}
BAT = b"\r\n".join((
    b"@ECHO OFF",
    b"IF \"%1\"==\"CGA\" GOTO MODEOK",
    b"IF \"%1\"==\"VGA\" GOTO MODEOK",
    b"ECHO Usage: INSTALL CGA D:\\WIN30GB  or  INSTALL VGA D:\\WIN30GB",
    b"GOTO END",
    b":MODEOK",
    b"IF \"%2\"==\"\" GOTO USAGE",
    b"IF NOT EXIST GBPATH.EXE GOTO NOSOURCE",
    b"GBPATH CHECK %2",
    b"IF ERRORLEVEL 1 GOTO BADTARGET",
    b"IF NOT EXIST PAYLOAD\\WIN\\WIN.COM GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\WIN\\PHON.IME GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\WIN\\GBPY.DAT GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\WIN\\B5PART.TBL GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\KERNEL.EXE GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\GDI.EXE GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\USER.EXE GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\SHELL.DLL GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\SYSTEM.DRV GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\CFFONT.FOD GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\CFSUNG.FON GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\CFSUNG16.B5Q GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\CFSUNG20.B5Q GOTO NOSOURCE",
    b"IF NOT EXIST PAYLOAD\\SYS\\CVGA.DRV GOTO NOSOURCE",
    b"IF NOT EXIST %1\\SYS.INI GOTO NOSOURCE",
    b"IF NOT EXIST CGA\\SYS\\CGA.DRV GOTO NOSOURCE",
    b"IF NOT EXIST CGA\\SYS\\CHCGA08.FNT GOTO NOSOURCE",
    b"IF NOT EXIST CGA\\SYS\\CHCGA10.FNT GOTO NOSOURCE",
    b"IF NOT EXIST CGA\\SYS\\CHCGA12.FNT GOTO NOSOURCE",
    b"IF NOT EXIST CGA\\SYS\\CGAS12.FON GOTO NOSOURCE",
    b"IF NOT EXIST VGA\\SYS\\CVGA.GR3 GOTO NOSOURCE",
    b"IF NOT EXIST VGA\\SYS\\CVDDCVGA.386 GOTO NOSOURCE",
    b"IF EXIST %2\\NUL GOTO EXISTS",
    b"MD %2",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"MD %2\\SYSTEM",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY PAYLOAD\\WIN\\*.* %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY PAYLOAD\\SYS\\*.* %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"IF \"%1\"==\"CGA\" COPY CGA\\WIN\\*.* %2 > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY %1\\SYS\\*.* %2\\SYSTEM > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"COPY %1\\SYS.INI %2\\SYSTEM.INI > NUL",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"GBPATH PATCH %1 %2",
    b"IF ERRORLEVEL 1 GOTO FAILED",
    b"ECHO GB2312 Windows installed to %2.",
    b"ECHO Change to that drive and directory, then run WIN /R.",
    b"GOTO END",
    b":EXISTS",
    b"ECHO Destination already exists. Installation stopped.",
    b"GOTO END",
    b":FAILED",
    b"ECHO Install incomplete. Check disk space and destination before retry.",
    b"GOTO END",
    b":NOSOURCE",
    b"ECHO Install source is incomplete. No files copied.",
    b"GOTO END",
    b":BADTARGET",
    b"ECHO Destination must be a new absolute DOS 8.3 directory.",
    b"GOTO END",
    b":USAGE",
    b"ECHO Specify a writable drive and new directory, for example D:\\WIN30GB.",
    b":END",
    b"",
))


def main() -> None:
    if OUT.exists():
        resolved = OUT.resolve()
        if resolved.parent != (_LAYOUT_ROOT / "src/test/native-gb2312/work/build").resolve():
            raise ValueError("refusing to remove a directory outside native-gb2312/build")
        shutil.rmtree(resolved)
    payload_win = OUT / "PAYLOAD/WIN"
    payload_sys = OUT / "PAYLOAD/SYS"
    payload_win.mkdir(parents=True)
    payload_sys.mkdir(parents=True)
    source_win = BASE / "WINDOWS"
    source_sys = source_win / "SYSTEM"
    for source in source_win.iterdir():
        if source.is_file() and source.name.upper() not in REMOVE_ROOT | {"SYSTEM.INI"}:
            shutil.copy2(source, payload_win / source.name)
    for source in source_sys.iterdir():
        if source.is_file() and source.name.upper() not in REMOVE_SYSTEM:
            shutil.copy2(source, payload_sys / source.name)
    setup_report = json.loads((_LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup/SETUP-MANIFEST.json").read_text(encoding="utf-8"))
    if set(setup_report) != {"SETUP.INF", "WIN.SRC", "README.TXT", "ETEN.TXT"}:
        raise ValueError("setup text conversion is incomplete")
    for name, entry in setup_report.items():
        if hashlib.sha256((source_win / name).read_bytes()).hexdigest() != entry["source_sha256"]:
            raise ValueError(f"setup source changed: {name}")
        converted = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/setup" / name
        if hashlib.sha256(converted.read_bytes()).hexdigest() != entry["output_sha256"]:
            raise ValueError(f"setup conversion changed: {name}")
        shutil.copy2(converted, payload_win / name)
    cffont_report = patch(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/patches/CFFONT.FOD", payload_sys / "CFFONT.FOD")
    if cffont_report["skipped_non_big5_fields"]:
        raise ValueError("CFFONT.FOD has unconverted text resources")

    patch_report = json.loads((PATCHED / "RESOURCE-MANIFEST.json").read_text(encoding="utf-8"))
    if set(patch_report) != set(MODULES) or any(
            value["status"] != "patched" for value in patch_report.values()):
        raise ValueError("the resource patch set is incomplete")
    unexpected_modules = {path.name.upper() for path in PATCHED.iterdir()
                          if path.suffix.upper() in (".EXE", ".DLL", ".IME", ".DRV")}
    if unexpected_modules != set(MODULES):
        raise ValueError("unexpected or missing patched resource modules")
    for name in MODULES:
        source = PATCHED / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != patch_report[name]["output_sha256"]:
            raise ValueError(f"patched resource changed after manifest: {name}")
        if source.suffix.upper() in (".EXE", ".DLL", ".DRV"):
            shutil.copy2(source, payload_sys / name)
        elif name == "WINIME.IME":
            shutil.copy2(source, payload_win / name)
    shutil.copy2(IME / "WINNLS.DLL", payload_sys / "WINNLS.DLL")
    for name in ("PHON.IME", "GBPY.DAT", "IMEINFO.INI",
                 "WIFEMAN.INI", "WIFERM.INI"):
        if name in RUNTIME_PATHS:
            check_runtime_slots((IME / name).read_bytes(), name)
        shutil.copy2(IME / name, payload_win / name)
    mapping = read_mapping(DICTIONARY)
    for name in ("CONTROL.INI", "WIN.INI"):
        raw, _ = simplify((source_win / name).read_bytes(), mapping)
        if name == "WIN.INI":
            start = raw.index(b"sCountry=")
            end = raw.index(b"\r\n", start)
            raw = raw[:start] + b"sCountry=" + "中国".encode("gb2312") + raw[end:]
            raw = raw.replace(b"iCountry=886", b"iCountry=86")
            raw = raw.replace(b"sCurrency=NT$", b"sCurrency=RMB")
        (payload_win / name).write_bytes(raw)

    (OUT / "CGA/SYS").mkdir(parents=True)
    (OUT / "CGA/WIN").mkdir(parents=True)
    (OUT / "VGA/SYS").mkdir(parents=True)
    cga_driver = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/driver/CGA.DRV"
    driver_data = cga_driver.read_bytes()
    driver_report = json.loads((_LAYOUT_ROOT / "src/test/native-gb2312/work/build/patches/CGA-BUILD.json").read_text(encoding="utf-8"))
    driver_ne = struct.unpack_from("<I", driver_data, 0x3C)[0]
    if (hashlib.sha256(driver_data).hexdigest() != driver_report["driver_sha256"]
            or driver_data[driver_ne + 0x3E:driver_ne + 0x40] != b"\x00\x03"
            or not driver_report["gb2312_pair_decoder"]):
        raise ValueError("CGA driver differs from the reviewed Windows 3.0 build")
    check_runtime_slots(driver_data, "CGA.DRV")
    shutil.copy2(cga_driver, OUT / "CGA/SYS/CGA.DRV")
    for size in (8, 10, 12):
        name = f"CHCGA{size:02d}.FNT"
        shutil.copy2(FONTS / name, OUT / "CGA/SYS" / name)
    shutil.copy2(FONTS / "CGAS12.FON", OUT / "CGA/SYS/CGAS12.FON")
    for name in CGA_MENU_MODULES:
        source = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/cga-menus" / (Path(name).stem + ".CGA")
        shutil.copy2(source, OUT / "CGA/WIN" / name)
        shutil.copy2(source, OUT / "CGA/SYS" / name)
    for name in ("CFSUNG.FON", "CFSUNG16.B5Q", "CFSUNG20.B5Q"):
        shutil.copy2(FONTS / name, payload_sys / name)
    for name in ("CVGA.GR3", "CVDDCVGA.386"):
        shutil.copy2(ROOT / "src/test/native-gb2312/work/build/expanded/chinese" / name, OUT / "VGA/SYS" / name)
    original_ini = (source_win / "SYSTEM.INI").read_bytes()
    for video in ("cga", "vga"):
        ini = configure_system_ini(original_ini, video, "progman.exe")
        if video == "cga":
            if ini.count(b"fonts.fon=cgasys.fon") != 1:
                raise ValueError("CGA system font setting changed")
            ini = ini.replace(b"fonts.fon=cgasys.fon", b"fonts.fon=cgas12.fon")
        (OUT / video.upper() / "SYS.INI").write_bytes(ini)
    (OUT / "INSTALL.BAT").write_bytes(BAT)
    shutil.copy2(_LAYOUT_ROOT / "src/test/install/work/build/windows/GBPATH.EXE", OUT / "GBPATH.EXE")
    (OUT / "README.TXT").write_bytes(b"\r\n".join((
        b"GB2312 Simplified Chinese Windows 3.0a - experimental build",
        b"Choose a new absolute DOS 8.3 directory; its parent must exist.",
        b"Run INSTALL CGA D:\\WIN30GB for HP 200LX, or",
        b"INSTALL VGA D:\\WIN30GB for VGA computers.",
        b"CGA uses WIN /R. VGA has been tested with /R, /S and /3.",
        b"Source media and existing Windows directories are not modified.",
        b"Change to the chosen drive and directory before running WIN.",
        b"IME: native Pinyin PHON.IME with GBPY.DAT; Ctrl+Space toggles input.",
        b"Type pinyin, choose 1-9, Space or Enter; minus/equal changes page.",
        b"Candidate glyphs are read from CFSUNG16.B5Q when needed.",
        b"VGA: all 7445 defined GB2312 double-byte codes have glyphs.",
        b"",
    )))
    files = {str(path.relative_to(OUT)).replace("/", "\\"):
             {"size": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in sorted(OUT.rglob("*")) if path.is_file()}
    manifest = {"source": "src/test/native-gb2312/work/build/setup-test/C32", "files": files,
                "total_bytes": sum(x["size"] for x in files.values())}
    (OUT / "MANIFEST.TXT").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(files)} files, {manifest['total_bytes']} bytes")


if __name__ == "__main__":
    main()
