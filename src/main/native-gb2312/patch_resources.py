"""Convert parsed Win16 NE menu, dialog and string resources from Big5 to GB2312.

Every replacement retains the exact byte length of its original field. Module
headers, resource offsets, code and non-text payloads are left untouched.
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


import argparse
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = _LAYOUT_ROOT
sys.path.insert(0, str(ROOT / "src/main/public-tools"))
from build_big5_simplified_fonts import DICTIONARY, read_mapping  # noqa: E402

TERMS = {
    "程式管理員": "程序管理器",
    "檔案管理員": "文件管理器",
    "剪貼簿": "剪贴板",
    "印表機": "打印机",
    "輔助說明": "帮助说明",
    "檔案": "文件",
    "視窗": "窗口",
    "程式": "程序",
    "開啟": "打开",
    "儲存": "保存",
    "列印": "打印",
    "結束": "退出",
    "磁碟": "磁盘",
    "搜尋": "搜索",
    "設定": "设置",
}

# Big5 presentation forms that GB2312 does not encode directly. These are
# single-cell approximations so Win16 resource offsets remain unchanged.
SYMBOLS = {
    "‧": "。", "︰": "：", "‥": "…", "﹐": "，", "﹑": "、",
    "﹒": "。", "·": "。", "﹔": "；", "﹕": "：", "﹖": "？",
    "﹗": "！", "﹚": "）", "﹜": "〕", "﹞": "〕", "〞": "”",
    "吋": "寸", "︱": "―",
}

# Same-width module-specific text also keeps messages inside CGA dialog and
# status-bar clips. Menu IDs and resource offsets remain unchanged.
RESOURCE_CONTEXT = {
    ("WRITE.EXE", 4, 1, "文件(&D)"): "文档(&D)",
    ("PBRUSH.EXE", 4, 1, "字形(&N)"): "字体(&N)",
    ("WINHELP.EXE", 4, 1, "編修(&E)"): "编辑(&E)",
    ("REVERSI.EXE", 4, 1, "技巧(&S)"): "难度(&S)",
    ("CARDFILE.EXE", 4, 1, "使用輔助說明(&P)"): "使用帮助说明(&U)",
    ("CONTROL.EXE", 4, 1, "字形(&F)..."): "字体(&F)...",
    ("CONTROL.EXE", 4, 1, "輸入法(&I)..."): "输入法(&E)...",
    ("TERMINAL.EXE", 4, 1, "顯示功能鍵(&K)"): "显示功能键(&V)",
    ("USERFONT.EXE", 4, 798, "清除全部(&Y)\t^Y"): "清除全部(&D)\t^Y",
    ("WRITE.EXE", 6, 514, "%% 已更改.  儲存新值?"):
        "文档已修改,是否保存? ",
    ("WINFILE.EXE", 6, 12, "磁碟機 %c:%s 尚有 %ld 位元組可用."):
        "驱动器 %c:%s 可用 %ld 字节.      ",
    ("WINFILE.EXE", 6, 12,
     "已指定 %d 個檔案( %ld 位元組),此目錄共有 %d 個檔案. "):
        "选中 %d 个文件(%ld 字节),本目录共 %d 个文件.        ",
}

# Two damaged original PIF Editor strings contain an orphan Big5 lead byte.
# Their mode names and resource IDs identify the intended messages. Keep the
# exact resource field widths rather than trying to decode the broken prefix.
RAW_CONTEXT = {
    ("PIFEDIT.EXE", 6, 3,
     bytes.fromhex("a4a3afe0c1b4aba6dc2033383620bc57b16abcd2a6a12e")):
        "不能运行于386 增强模式.",
    ("PIFEDIT.EXE", 6, 3,
     bytes.fromhex("a4a3afe0c1b4aba6dcbcd0b7c7bcd2a6a12e")):
        "不能运行标准模式。",
}


def word(data: bytes, at: int) -> int:
    return struct.unpack_from("<H", data, at)[0]


@dataclass(frozen=True)
class Resource:
    kind: int
    number: int
    offset: int
    length: int


def resources(data: bytes) -> list[Resource]:
    if data[:2] != b"MZ":
        raise ValueError("missing MZ signature")
    ne = struct.unpack_from("<I", data, 0x3C)[0]
    if data[ne:ne + 2] != b"NE":
        raise ValueError("missing NE signature")
    table_offset = word(data, ne + 0x24)
    if table_offset == word(data, ne + 0x26):
        return []
    table = ne + table_offset
    shift = word(data, table)
    at = table + 2
    found = []
    while kind := word(data, at):
        count = word(data, at + 2)
        at += 8
        for _ in range(count):
            sector, size, _, identifier, _, _ = struct.unpack_from("<6H", data, at)
            at += 12
            if kind & 0x8000 and identifier & 0x8000:
                offset = sector << shift
                length = size << shift
                if offset + length > len(data):
                    raise ValueError("resource crosses module boundary")
                found.append(Resource(kind & 0x7FFF, identifier & 0x7FFF,
                                      offset, length))
    return found


def cstring(data: bytes, at: int, *, class_field: bool = False) -> tuple[int, tuple[int, int] | None]:
    if at >= len(data):
        raise ValueError("string outside resource")
    if data[at] == 0:
        return at + 1, None
    if data[at] == 0xFF:
        if at + 3 > len(data):
            raise ValueError("truncated ordinal")
        return at + 3, None
    if class_field and data[at] >= 0x80:
        return at + 1, None
    end = data.find(b"\0", at)
    if end < 0:
        raise ValueError("unterminated resource string")
    return end + 1, (at, end)


def menu_spans(data: bytes) -> list[tuple[int, int]]:
    if len(data) < 6 or word(data, 0) != 0:
        raise ValueError("unexpected Win16 menu header")
    spans = []

    def items(at: int, depth: int) -> int:
        if depth > 12:
            raise ValueError("menu nesting too deep")
        while True:
            flags = word(data, at)
            at += 2
            popup = bool(flags & 0x0010)
            if not popup:
                at += 2  # item ID
            at, span = cstring(data, at)
            if span:
                spans.append(span)
            if popup:
                at = items(at, depth + 1)
            if flags & 0x0080:
                return at

    end = items(4 + word(data, 2), 0)
    if end > len(data) or any(data[end:]):
        raise ValueError("menu payload has unexpected trailing data")
    return spans


def dialog_spans(data: bytes) -> list[tuple[int, int]]:
    if len(data) < 16:
        raise ValueError("short dialog")
    style = struct.unpack_from("<I", data, 0)[0]
    count = data[4]
    at = 13
    spans = []
    at, _ = cstring(data, at)  # menu name, leave identifiers unchanged
    at, _ = cstring(data, at, class_field=True)  # dialog class
    at, span = cstring(data, at)
    if span:
        spans.append(span)
    if style & 0x40:  # DS_SETFONT
        at += 2
        at, _ = cstring(data, at)  # font family
    for _ in range(count):
        at += 14  # x, y, cx, cy, id, style
        at, _ = cstring(data, at, class_field=True)
        at, span = cstring(data, at)
        if span:
            spans.append(span)
        if at >= len(data):
            raise ValueError("missing control data length")
        size = data[at]
        at += 1 + size
        if at > len(data):
            raise ValueError("control data crosses dialog boundary")
    if any(data[at:]):
        raise ValueError("dialog payload has unexpected trailing data")
    return spans


def string_spans(data: bytes) -> list[tuple[int, int]]:
    spans = []
    at = 0
    for _ in range(16):
        if at >= len(data):
            raise ValueError("short string-table block")
        length = data[at]
        at += 1
        if at + length > len(data):
            raise ValueError("string crosses block boundary")
        if length:
            spans.append((at, at + length))
        at += length
    if any(data[at:]):
        raise ValueError("string-table block has unexpected trailing data")
    return spans


def simplify(raw: bytes, mappings: dict) -> tuple[bytes, list[str]]:
    original = raw.decode("cp950")
    localized = original
    for traditional, simplified in TERMS.items():
        if len(traditional) != len(simplified):
            raise ValueError("locale term changes character count")
        localized = localized.replace(traditional, simplified)
    result = bytearray()
    substitutions = []
    for char in localized:
        if ord(char) < 128:
            result.extend(char.encode("ascii"))
            continue
        choices = (SYMBOLS[char],) if char in SYMBOLS else mappings.get(char, (char,))
        encoded = None
        selected = None
        for candidate in (*choices, char):
            try:
                test = candidate.encode("gb2312")
            except UnicodeEncodeError:
                continue
            if len(test) == 2:
                encoded, selected = test, candidate
                break
        if encoded is None:
            encoded, selected = "？".encode("gb2312"), "？"
        result.extend(encoded)
        if selected != char:
            substitutions.append(f"{char}->{selected}")
    if len(result) != len(raw):
        raise ValueError("translation changed resource field length")
    return bytes(result), substitutions


def patch(source: Path, destination: Path) -> dict:
    if source.resolve() == destination.resolve():
        raise ValueError("refusing to overwrite original module")
    original = source.read_bytes()
    data = bytearray(original)
    mappings = read_mapping(DICTIONARY)
    report = {"source": str(source), "source_sha256": hashlib.sha256(original).hexdigest(),
              "resources": {}, "fields": 0, "changed_fields": 0,
              "unconvertible": [], "skipped_non_big5_fields": [],
              "context_overrides": [], "repaired_non_big5_fields": []}
    for resource in resources(original):
        if resource.kind not in (4, 5, 6):
            continue
        payload = original[resource.offset:resource.offset + resource.length]
        parser = {4: menu_spans, 5: dialog_spans, 6: string_spans}[resource.kind]
        spans = parser(payload)
        key = f"{resource.kind}:{resource.number}"
        report["resources"][key] = len(spans)
        for begin, end in spans:
            raw = payload[begin:end]
            if not any(byte >= 0x80 for byte in raw):
                continue
            raw_key = (source.name.upper(), resource.kind, resource.number, raw)
            if raw_key in RAW_CONTEXT:
                translated = RAW_CONTEXT[raw_key].encode("gb2312")
                substitutions = []
                report["repaired_non_big5_fields"].append(
                    {"resource": key, "span": [begin, end],
                     "text": RAW_CONTEXT[raw_key]})
            else:
                try:
                    translated, substitutions = simplify(raw, mappings)
                except UnicodeDecodeError:
                    report["skipped_non_big5_fields"].append(
                        {"resource": key, "span": [begin, end], "hex": raw.hex()})
                    continue
                original_text = raw.decode("cp950")
                context_key = (source.name.upper(), resource.kind,
                               resource.number, original_text)
                if context_key in RESOURCE_CONTEXT:
                    replacement = RESOURCE_CONTEXT[context_key].encode("gb2312")
                    if len(replacement) != len(raw):
                        raise ValueError("context label changed resource width")
                    translated = replacement
                    report["context_overrides"].append(
                        {"resource": key, "from": original_text,
                         "to": RESOURCE_CONTEXT[context_key]})
            if len(translated) != len(raw):
                raise ValueError("context resource label changed field width")
            report["fields"] += 1
            if translated != raw:
                data[resource.offset + begin:resource.offset + end] = translated
                report["changed_fields"] += 1
            report["unconvertible"].extend(
                x for x in substitutions
                if x.endswith("->？") and x.split("->", 1)[0] not in SYMBOLS)
    # Parsing the result again detects accidental damage to the NE resource table.
    if resources(data) != resources(original):
        raise ValueError("resource layout changed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    report["output_sha256"] = hashlib.sha256(data).hexdigest()
    report["output_bytes"] = len(data)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("destination", type=Path)
    args = p.parse_args()
    print(json.dumps(patch(args.source, args.destination), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
