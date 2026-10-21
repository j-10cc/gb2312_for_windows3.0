"""Rebuild the GB2312 CGA driver and target its NE header to Windows 3.0."""

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
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = _LAYOUT_ROOT
DDK = ROOT / "external/win30ddk"
DOSBOX = ROOT / "external/dosbox-x/mingw-build/mingw-sdl2/dosbox-x.exe"
BUILT = DDK / "display/1plane/bw/cgaherc/cga/CGA.DRV"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/driver/CGA.DRV"
REPORT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patches/CGA-BUILD.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="store_true",
                        help="build a separate diagnostic driver with draw-call logging")
    args = parser.parse_args()
    probe = [sys.executable, str(ROOT / "src/main/cga-driver/build_chcga_probe.py"),
             str(DDK), str(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/fonts/CHCGA12.FNT"),
             "--medium-font", str(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/fonts/CHCGA10.FNT"),
             "--small-font", str(_LAYOUT_ROOT / "src/test/native-gb2312/work/build/fonts/CHCGA08.FNT"),
             "--gb2312"]
    if args.trace:
        probe.append("--trace")
    subprocess.run(probe, cwd=ROOT, check=True)
    before = BUILT.stat().st_mtime_ns if BUILT.exists() else 0
    command = (str(DOSBOX), "-noconsole", "-set", "dosbox machine=svga_s3",
               "-set", "cpu cycles=max", "-c", "mount c .\\external\\win30ddk",
               "-c", "c:", "-c", "BUILDCH.BAT", "-c", "exit")
    subprocess.run(command, cwd=ROOT, check=True, timeout=60,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not BUILT.exists() or BUILT.stat().st_mtime_ns <= before:
        raise RuntimeError("DDK did not produce a new CGA.DRV")
    asm_log = (DDK / "PROBEASM.LOG").read_text(encoding="ascii", errors="replace")
    if "0 Warning Errors" not in asm_log or "0 Severe  Errors" not in asm_log:
        raise RuntimeError("CGA MASM build did not complete cleanly")
    data = bytearray(BUILT.read_bytes())
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[:2] != b"MZ" or data[ne:ne + 2] != b"NE" or data[ne + 0x3E:ne + 0x40] != b"\x0A\x03":
        raise RuntimeError("unexpected CGA driver NE header")
    # The DDK resource compiler targets Windows 3.10; Windows 3.0 rejects it.
    data[ne + 0x3E] = 0
    output = OUT.with_name("CGA-TRACE.DRV") if args.trace else OUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    if args.trace:
        print(f"{output}: {len(data)} bytes, diagnostic Windows 3.00 driver")
        return
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "driver_sha256": hashlib.sha256(data).hexdigest(),
        "driver_bytes": len(data),
        "expected_windows_version": "3.00",
        "gb2312_pair_decoder": True,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"{output}: {len(data)} bytes, Windows 3.00 NE target")


if __name__ == "__main__":
    main()
