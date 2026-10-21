"""Keep built-in menus and dialogs within the 200-pixel CGA desktop.

The CGA copies retain every command ID. Only menu resource trees are changed;
the original GB2312 program modules remain the VGA/standard-mode defaults.
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
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from patch_resources import cstring, dialog_spans, resources, word

HERE = Path(__file__).resolve().parent
SOURCE = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/patched"
OUT = _LAYOUT_ROOT / "src/test/native-gb2312/work/build/cga-menus"
MODULES = (
    "SHELL.DLL", "PROGMAN.EXE", "WINFILE.EXE", "NOTEPAD.EXE", "CALC.EXE",
    "CALENDAR.EXE", "CARDFILE.EXE", "PBRUSH.EXE", "WRITE.EXE",
    "CONTROL.EXE", "CLIPBRD.EXE", "PRINTMAN.EXE", "RECORDER.EXE",
    "TERMINAL.EXE", "WINHELP.EXE", "USERFONT.EXE", "MSDOS.EXE",
    "FINSTALL.DLL",
)
LIMIT = 11
MORE = "更多".encode("gb2312")
DIALOG_HEIGHT = 120  # 12-pixel system font: at most 180 physical pixels.


@dataclass
class Item:
    flags: int
    command: int | None
    label: bytes
    children: list["Item"]


def read_items(data: bytes, at: int) -> tuple[list[Item], int]:
    items = []
    while True:
        if at + 2 > len(data):
            raise ValueError("truncated Win16 menu flags")
        flags = word(data, at)
        at += 2
        command = None
        if not flags & 0x10:
            command = word(data, at)
            at += 2
        end = data.index(0, at)
        label = data[at:end]
        at = end + 1
        children = []
        if flags & 0x10:
            children, at = read_items(data, at)
        items.append(Item(flags, command, label, children))
        if flags & 0x80:
            return items, at


def write_items(items: list[Item]) -> bytes:
    if not items:
        raise ValueError("empty popup menu")
    data = bytearray()
    for index, item in enumerate(items):
        flags = (item.flags & ~0x80) | (0x80 if index == len(items) - 1 else 0)
        flags = (flags | 0x10) if item.children else (flags & ~0x10)
        data.extend(struct.pack("<H", flags))
        if not item.children:
            data.extend(struct.pack("<H", item.command or 0))
        data.extend(item.label + b"\0")
        if item.children:
            data.extend(write_items(item.children))
    return bytes(data)


def paginate(items: list[Item]) -> tuple[list[Item], int]:
    changed = 0
    for item in items:
        if item.children:
            item.children, nested = paginate(item.children)
            changed += nested
    if len(items) <= LIMIT:
        return items, changed
    cut = LIMIT - 1
    while cut > 1 and (not items[cut].label or not items[cut - 1].label):
        cut -= 1
    if cut <= 1:
        raise ValueError("cannot split menu at a useful boundary")
    head, tail = items[:cut], items[cut:]
    while tail and not tail[0].label:
        tail = tail[1:]
    if not tail:
        raise ValueError("menu continuation has no commands")
    tail, nested = paginate(tail)
    head.append(Item(0x10, None, MORE, tail))
    return head, changed + nested + 1


def commands(items: list[Item]) -> Counter[int]:
    result: Counter[int] = Counter()
    for item in items:
        if item.command:
            result[item.command] += 1
        result.update(commands(item.children))
    return result


def max_depth_count(items: list[Item]) -> int:
    return max([len(items)] + [max_depth_count(item.children)
                              for item in items if item.children])


def table_entry(data: bytes, kind: int, number: int) -> tuple[int, int]:
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    table = ne + word(data, ne + 0x24)
    shift = word(data, table)
    at = table + 2
    while type_id := word(data, at):
        count = word(data, at + 2)
        at += 8
        for _ in range(count):
            identifier = word(data, at + 6)
            if type_id == kind | 0x8000 and identifier == number | 0x8000:
                return at, shift
            at += 12
    raise ValueError(f"Win16 resource missing: {kind}:{number}")


def compact_dialog(payload: bytes, preserve_top: int = 0) -> tuple[bytes, dict | None]:
    original = bytearray(payload)
    if len(original) < 13:
        raise ValueError("short Win16 dialog")
    x, y, cx, height = struct.unpack_from("<4h", original, 5)
    if height <= DIALOG_HEIGHT:
        return payload, None
    if height > 170:
        raise ValueError("dialog requires a separate paged CGA design")
    # Win16 DLU vertical dimensions are based on the system font height.
    # Move every control with the dialog so command IDs and focus order stay
    # untouched. Keep text/button controls at least eight DLU high.
    if preserve_top < 0 or preserve_top >= DIALOG_HEIGHT:
        raise ValueError("invalid preserved dialog top")
    scale = DIALOG_HEIGHT / height

    def place_y(value: int) -> int:
        if preserve_top == 0:
            return round(value * scale)
        if value <= preserve_top:
            return value
        return preserve_top + round((value - preserve_top) *
                                    (DIALOG_HEIGHT - preserve_top) /
                                    (height - preserve_top))

    at = 13
    for _ in range(3):
        at, _ = cstring(original, at)
    if struct.unpack_from("<I", original, 0)[0] & 0x40:
        at += 2
        at, _ = cstring(original, at)
    count = original[4]
    for _ in range(count):
        old_y = struct.unpack_from("<h", original, at + 2)[0]
        old_h = struct.unpack_from("<h", original, at + 6)[0]
        new_y = place_y(old_y)
        new_h = (round(old_h * scale) if preserve_top == 0 else
                 place_y(old_y + old_h) - new_y)
        if old_h >= 8:
            new_h = max(8, new_h)
        new_h = min(new_h, max(1, DIALOG_HEIGHT - new_y))
        struct.pack_into("<h", original, at + 2, new_y)
        struct.pack_into("<h", original, at + 6, new_h)
        at += 14
        at, _ = cstring(original, at, class_field=True)
        at, _ = cstring(original, at)
        size = original[at]
        at += 1 + size
    struct.pack_into("<h", original, 7, min(max(y, 0), 6))
    struct.pack_into("<h", original, 11, DIALOG_HEIGHT)
    dialog_spans(original)  # Verify the modified template still parses.
    return bytes(original), {"original_height": height,
                             "cga_height": DIALOG_HEIGHT, "controls": count}


def patch_module(source: Path, target: Path) -> dict:
    data = bytearray(source.read_bytes())
    changed = {}
    for entry in resources(data):
        if entry.kind != 4:
            continue
        payload = bytes(data[entry.offset:entry.offset + entry.length])
        prefix = payload[:4 + word(payload, 2)]
        items, end = read_items(payload, len(prefix))
        if any(payload[end:]):
            raise ValueError(f"unexpected menu padding in {source.name}")
        original_commands = commands(items)
        items, wrappers = paginate(items)
        if not wrappers:
            continue
        if commands(items) != original_commands or max_depth_count(items) > LIMIT:
            raise AssertionError("CGA menu pagination lost a command")
        new_payload = prefix + write_items(items)
        table_at, shift = table_entry(data, 4, entry.number)
        alignment = 1 << shift
        data.extend(bytes(-len(data) % alignment))
        start = len(data)
        sectors = (len(new_payload) + alignment - 1) // alignment
        if start // alignment > 0xFFFF or sectors > 0xFFFF:
            raise OverflowError("CGA menu resource exceeds NE sector fields")
        data.extend(new_payload + bytes(sectors * alignment - len(new_payload)))
        struct.pack_into("<HH", data, table_at, start // alignment, sectors)
        changed[str(entry.number)] = {"continuations": wrappers,
                                      "original_bytes": end,
                                      "new_bytes": len(new_payload)}
    dialogs = {}
    for entry in resources(data):
        if entry.kind != 5:
            continue
        original = bytes(data[entry.offset:entry.offset + entry.length])
        compacted, report = compact_dialog(
            original, preserve_top=48 if source.name.upper() == "CONTROL.EXE"
            and entry.number == 100 else 0)
        if report is not None:
            if len(compacted) != len(original):
                raise AssertionError("dialog compaction changed resource size")
            data[entry.offset:entry.offset + entry.length] = compacted
            dialogs[str(entry.number)] = report
    if not changed and not dialogs:
        raise ValueError(f"no CGA UI adjustment in {source.name}")
    # The MZ length fields describe the DOS stub, not the entire NE image.
    # Windows uses the NE resource table for the appended MENU payloads.
    if data[2:6] != source.read_bytes()[2:6]:
        raise AssertionError("DOS stub length fields changed")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    for entry in resources(data):
        if entry.kind == 4 and str(entry.number) in changed:
            payload = data[entry.offset:entry.offset + entry.length]
            items, end = read_items(payload, 4 + word(payload, 2))
            if any(payload[end:]) or max_depth_count(items) > LIMIT:
                raise AssertionError(f"rewritten menu invalid: {source.name}:{entry.number}")
    return {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(data).hexdigest(),
            "resources": changed, "dialogs": dialogs}


def main() -> None:
    report = {}
    for name in MODULES:
        target = OUT / (Path(name).stem + ".CGA")
        report[target.name] = patch_module(SOURCE / name, target)
        print(f"{target.name}: {len(report[target.name]['resources'])} menus, "
              f"{len(report[target.name]['dialogs'])} dialogs")
    (OUT / "MANIFEST.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
