"""Build a separate Windows 3.0 Setup medium with mainland UI terminology.

The existing full Setup medium is copied and never modified. Changed Win16
resources are appended at NE sector boundaries, then their table entries are
updated; resource IDs, menu commands and dialog control IDs remain unchanged.
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
import os
import re
import shutil
import struct
import subprocess
from pathlib import Path

from build_setup_media import OUT as SOURCE
from build_resources import MODULES
from paginate_cga_menus import MODULES as CGA_MODULES, commands, read_items, table_entry
from patch_resources import dialog_spans, menu_spans, resources, string_spans, word

HERE = Path(__file__).resolve().parent
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/terminology/GB2312-SETUP"
ROOT_APPS = tuple(name for name in MODULES if name.endswith(".EXE") and
                  name not in {"KERNEL.EXE", "GDI.EXE", "USER.EXE",
                               "SETUP.EXE", "SWAPFILE.EXE", "SYSEDIT.EXE"})

# Only names tied to actual executable functions are replaced globally. The
# Clipboard palette format and the clipboard object are not application names.
NAMES = {
    "小作家": "写字板", "小算盘": "计算器", "控制台": "控制面板",
    "打印管理员": "打印管理器", "终端机": "终端",
    "制作人": "宏录制器", "名片盒": "卡片盒", "小时钟": "时钟",
    "接龙": "纸牌",
}
TERMS = {
    "滑鼠": "鼠标", "记忆体": "内存", "磁盘机": "驱动器",
    "磁片": "软盘", "网路": "网络", "连线": "连接",
    "档名": "文件名", "字元": "字符", "预设": "默认",
    "萤幕": "屏幕", "解像度": "分辨率", "驱动档": "驱动程序",
    "硬体": "硬件", "软体": "软件", "另存新档": "另存为",
    "打开旧档": "打开", "开新文件": "新建", "更名保存": "另存为",
    "打印格式": "页面设置", "边界空白": "页边距",
    "巨集": "宏", "国别设置": "区域设置", "连接埠": "端口",
    "帮助说明": "帮助", "编修": "编辑", "影像": "图像",
}
STRING_FALLBACK = {
    "档名": "名称", "控制台": "控制板", "制作人": "录制器",
    "驱动档": "驱动库",
}
GROUP_LABELS = {
    "附属应用程序": "附件", "游乐场": "游戏",
    "控制台": "控制面板", "打印管理员": "打印管理器",
    "剪贴板": "剪贴板查看器", "DOS 模式": "MS-DOS 提示符",
    "系统设置": "Windows 安装程序", "小作家": "写字板",
    "调色盘": "画图", "终端机": "终端",
    "制作人": "宏录制器", "名片盒": "卡片盒",
    "小算盘": "计算器", "小时钟": "时钟",
    "PIF 编辑": "PIF 编辑器", "接龙": "纸牌",
}


def translate(text: str, module: str, short_labels: bool = False,
              string_fallback: bool = False) -> str:
    result = text
    if string_fallback:
        for old, new in STRING_FALLBACK.items():
            result = result.replace(old, new)
    if module == "PBRUSH.EXE":
        result = result.replace("调色盘", "画图")
    elif module == "CLIPBRD.EXE":
        result = result.replace("调色盘", "调色板")
        if not string_fallback and result in ("剪贴板", "关于剪贴板"):
            result = result.replace("剪贴板", "剪贴板查看器")
    elif module == "SETUP.EXE":
        if result == "退出系统设置":
            result = "退出安装程序"  # Keep the original 55-DLU button readable.
        elif result in ("系统设置", "关于系统设置"):
            result = result.replace("系统设置", "安装程序")
    elif module == "PIFEDIT.EXE":
        if not string_fallback:
            result = re.sub(r"PIF 编辑(?!器)", "PIF 编辑器", result)
    for old, new in NAMES.items():
        result = result.replace(old, new)
    for old, new in TERMS.items():
        result = result.replace(old, new)
    if short_labels:
        if module == "CONTROL.EXE" and result == "字形文件名称(&N):":
            result = "文件名(&N):"
        elif module == "PIFEDIT.EXE" and result == "程序文件名(&P):":
            result = "程序名(&P):"
        elif module == "USERFONT.EXE" and result in ("文件名(&F)：", "文件名(&L)："):
            result = result.replace("文件名", "名称")
    return result


def replace_payload(payload: bytes, kind: int, module: str,
                    same_width_only: bool = False,
                    short_labels: bool = False,
                    string_fallback: bool = False) -> tuple[bytes, int]:
    spans = {4: menu_spans, 5: dialog_spans, 6: string_spans}[kind](payload)
    changed = []
    for start, end in spans:
        original = payload[start:end]
        try:
            text = original.decode("gb2312")
        except UnicodeDecodeError:
            continue  # The base medium has a few pre-existing legacy fields.
        translated = translate(text, module, short_labels=short_labels,
                               string_fallback=string_fallback)
        if translated != text:
            encoded = translated.encode("gb2312")
            if same_width_only and len(encoded) != len(original):
                if kind == 6 and len(encoded) < len(original):
                    encoded += b" " * (len(original) - len(encoded))
                else:
                    continue
            if kind == 6 and len(encoded) > 255:
                raise ValueError(f"{module}: string-table entry exceeds 255 bytes")
            changed.append((start, end, encoded))
    if not changed:
        return payload, 0
    data = bytearray(payload)
    for start, end, encoded in reversed(changed):
        data[start:end] = encoded
        if kind == 6:
            data[start - 1] = len(encoded)
    result = bytes(data)
    parsed = {4: menu_spans, 5: dialog_spans, 6: string_spans}[kind](result)
    if len(parsed) != len(spans):
        raise AssertionError(f"{module}: resource field count changed")
    if kind == 4:
        before, _ = read_items(payload, 4 + word(payload, 2))
        after, _ = read_items(result, 4 + word(result, 2))
        if commands(before) != commands(after):
            raise AssertionError(f"{module}: menu command IDs changed")
    return result, len(changed)


def patch_ne(path: Path, name: str, same_width_only: bool = False,
             short_labels: bool = False) -> dict:
    original = path.read_bytes()
    data = bytearray(original)
    report = {"resources": {}, "fields": 0}
    for entry in resources(original):
        if entry.kind not in (4, 5, 6):
            continue
        payload = original[entry.offset:entry.offset + entry.length]
        updated, fields = replace_payload(payload, entry.kind, name,
                                          same_width_only=same_width_only,
                                          short_labels=short_labels)
        if entry.kind == 6 and len(updated) > len(payload):
            updated, fields = replace_payload(payload, entry.kind, name,
                                              short_labels=short_labels,
                                              string_fallback=True)
        if entry.kind == 6 and len(updated) > len(payload):
            raise ValueError(f"{name}: string block {entry.number} exceeds its original sector")
        if not fields:
            continue
        # Win16 LoadString cannot load a block appended after the original NE
        # image. Keep each string block in its original allocated sector.
        if entry.kind == 6 or same_width_only or len(updated) == len(payload):
            if len(updated) > len(payload):
                raise AssertionError(f"{name}: in-place patch grew resource")
            data[entry.offset:entry.offset + entry.length] = (
                updated + bytes(len(payload) - len(updated)))
            report["resources"][f"{entry.kind}:{entry.number}"] = fields
            report["fields"] += fields
            continue
        table, shift = table_entry(data, entry.kind, entry.number)
        alignment = 1 << shift
        data.extend(bytes(-len(data) % alignment))
        start = len(data)
        sectors = (len(updated) + alignment - 1) // alignment
        if start // alignment > 0xFFFF or sectors > 0xFFFF:
            raise OverflowError(f"{name}: NE resource sector overflow")
        data.extend(updated + bytes(sectors * alignment - len(updated)))
        struct.pack_into("<HH", data, table, start // alignment, sectors)
        report["resources"][f"{entry.kind}:{entry.number}"] = fields
        report["fields"] += fields
    if data[2:6] != original[2:6]:
        raise AssertionError(f"{name}: DOS stub length changed")
    path.write_bytes(data)
    report["original_sha256"] = hashlib.sha256(original).hexdigest()
    report["sha256"] = hashlib.sha256(data).hexdigest()
    report["growth_bytes"] = len(data) - len(original)
    return report


def patch_setup_inf(path: Path) -> None:
    text = path.read_bytes().decode("gb2312")
    for old, new in GROUP_LABELS.items():
        if old not in text:
            raise ValueError(f"SETUP.INF lacks {old}")
        text = text.replace(old, new)
    if "[progman.groups]\r\n" not in text or "[附件]\r\n" not in text or "[游戏]\r\n" not in text:
        raise AssertionError("Setup group declarations became invalid")
    path.write_bytes(text.encode("gb2312"))


def build_layout_tool() -> Path:
    tool_dir = OUT.parent / "layout-tool"
    tool_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "GBPATH.C", tool_dir / "GBPATH.C")
    watcom = _LAYOUT_ROOT / "external/open-watcom"
    compiler = watcom / "binnt64/wcc.exe"
    linker = watcom / "binnt64/wlink.exe"
    environment = os.environ.copy()
    environment.update({"WATCOM": str(watcom), "INCLUDE": str(watcom / "h"),
                        "LIB": str(watcom / "lib286"),
                        "PATH": str(watcom / "binnt64") + os.pathsep +
                        environment.get("PATH", "")})
    subprocess.run((str(compiler), "-0", "-bt=dos", "GBPATH.C"),
                   cwd=tool_dir, env=environment, check=True,
                   stdout=subprocess.DEVNULL)
    binary = tool_dir / "GBPATH.EXE"
    subprocess.run((str(linker), "system", "dos", "name", str(binary),
                    "option", "stack=8192", "file", "GBPATH.obj"),
                   cwd=tool_dir, env=environment,
                   check=True, stdout=subprocess.DEVNULL)
    if binary.read_bytes()[:2] != b"MZ":
        raise ValueError("terminology layout tool is not an MZ executable")
    return binary


def main() -> None:
    if not (SOURCE / "SETUP.INF").is_file():
        raise FileNotFoundError("build the original GB2312-SETUP medium first")
    if OUT.exists():
        if OUT.resolve().parent != (_LAYOUT_ROOT / "src/test/native-gb2312/work/build/terminology").resolve():
            raise ValueError("unexpected terminology output path")
        shutil.rmtree(OUT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, OUT)
    report = {"base": str(SOURCE), "modules": {}, "post_setup_overlays": {}}
    targets = [OUT / name for name in MODULES if (OUT / name).is_file()]
    targets += [OUT / (Path(name).stem + ".CGA") for name in CGA_MODULES]
    for module in targets:
        if module.name.upper() == "SETUP.EXE":
            # The original two-stage installer depends on its binary layout.
            # Even a parseable in-place resource edit stopped GUI completion.
            continue
        if module.suffix.upper() == ".CGA":
            name = module.stem.upper() + (".DLL" if module.stem.upper() in
                    {Path(item).stem for item in CGA_MODULES if item.endswith(".DLL")}
                    else ".EXE")
        else:
            name = module.name.upper()
        try:
            resources(module.read_bytes())
        except ValueError:
            continue
        result = patch_ne(module, name, same_width_only=name == "SETUP.EXE")
        if result["fields"]:
            report["modules"][module.name] = result
    patch_setup_inf(OUT / "SETUP.INF")
    # Keep the Setup-readable originals on the medium. These replacement
    # modules are copied only after the original two-stage Setup has finished.
    # CGA already uses its .CGA variants at that point.
    for name in ("CONTROL.EXE", "PIFEDIT.EXE", "USERFONT.EXE"):
        sidecar = OUT / (Path(name).stem + ".TRM")
        shutil.copy2(OUT / name, sidecar)
        report["post_setup_overlays"][sidecar.name] = patch_ne(
            sidecar, name, short_labels=True)
        variant = OUT / (Path(name).stem + ".CGA")
        if variant.is_file():
            report["post_setup_overlays"][variant.name] = patch_ne(
                variant, name, short_labels=True)
    shutil.copy2(build_layout_tool(), OUT / "GBPATH.EXE")
    old = b'IF "%1"=="CGA" GBPATH LAYOUT CGA %2'
    new = b'GBPATH LAYOUT %1 %2'
    guarded_marker = b'IF "%1"=="CGA" IF NOT EXIST %2\\GBLAY.OK GOTO FAILED'
    for name in ("INSTALL.BAT", "FINALIZE.BAT"):
        path = OUT / name
        data = path.read_bytes()
        required = sorted(set(ROOT_APPS) | {"SYSEDIT.EXE", "CONTROL.TRM",
                                          "PIFEDIT.TRM", "USERFONT.TRM"} |
                          {Path(item).stem + ".CGA" for item in CGA_MODULES})
        preflight = b"\r\n".join(
            b"IF NOT EXIST " + item.encode("ascii") + b" GOTO BADMEDIA"
            for item in required) + b"\r\n"
        marker = (b"GBPATH CHECK %2" if name == "INSTALL.BAT"
                  else b"GBPATH SOURCE %2")
        if data.count(marker) != 1:
            raise ValueError(f"{name}: expected one source preflight marker")
        data = data.replace(marker, preflight + marker, 1)
        if data.count(old) != 1:
            raise ValueError(f"{name}: expected one layout command")
        data = data.replace(old, new)
        if data.count(guarded_marker) != 1:
            raise ValueError(f"{name}: expected one layout result check")
        data = data.replace(guarded_marker,
                            b'IF NOT EXIST %2\\GBLAY.OK GOTO FAILED', 1)
        # Setup can leave an existing app in place. Force the selected medium's
        # application resources into the completed installation, while keeping
        # SHELL.DLL's registration block written by Setup intact.
        application_copies = []
        cga_variants = set(CGA_MODULES)
        for app in ROOT_APPS:
            mode = b'IF "%1"=="VGA" ' if app in cga_variants else b''
            application_copies.extend((mode + b'COPY ' + app.encode("ascii") +
                                       b' %2\\' + app.encode("ascii") + b' > NUL',
                                       b'IF ERRORLEVEL 1 GOTO FAILED'))
        application_copies.extend((b'COPY SYSEDIT.EXE %2\\SYSTEM > NUL',
                                   b'IF ERRORLEVEL 1 GOTO FAILED'))
        additions = b"\r\n".join((*application_copies,
            b'IF "%1"=="VGA" COPY CONTROL.TRM %2\\CONTROL.EXE > NUL',
            b'IF ERRORLEVEL 1 GOTO FAILED',
            b'COPY PIFEDIT.TRM %2\\PIFEDIT.EXE > NUL',
            b'IF ERRORLEVEL 1 GOTO FAILED',
            b'IF "%1"=="VGA" COPY USERFONT.TRM %2\\USERFONT.EXE > NUL',
            b'IF ERRORLEVEL 1 GOTO FAILED',
            b'',
        ))
        if data.count(new) != 1:
            raise ValueError(f"{name}: layout command count changed")
        path.write_bytes(data.replace(new, additions + new, 1))
    for name in ("README.TXT", "ETEN.TXT"):
        path = OUT / name
        text = path.read_bytes().decode("gb2312")
        for old, new in GROUP_LABELS.items():
            text = text.replace(old, new)
        path.write_bytes(text.encode("gb2312"))
    files = {path.name: {"size": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in sorted(OUT.iterdir()) if path.is_file()
             and path.name not in ("MANIFEST.TXT", "TERMINOLOGY-MANIFEST.json")}
    (OUT / "MANIFEST.TXT").write_text(json.dumps({"files": files}, indent=2) + "\n")
    (OUT / "TERMINOLOGY-MANIFEST.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(report['modules'])} modules, "
          f"{sum(x['fields'] for x in report['modules'].values())} text fields, "
          f"{sum(x['fields'] for x in report['post_setup_overlays'].values())} "
          "post-Setup label fixes")


if __name__ == "__main__":
    main()
