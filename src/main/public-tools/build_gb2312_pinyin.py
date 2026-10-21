"""Build a disk-backed GB2312 pinyin dictionary, optionally with phrases.

Source: Unicode 16.0 Unihan_Readings kMandarin and kHanyuPinyin. The local
archive is downloaded separately into external/unihan/Unihan.zip; only the
compact derived dictionary is put in the DOS install package.
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
import re
import struct
import unicodedata
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


ROOT = _LAYOUT_ROOT
ARCHIVE = ROOT / "external/unihan/Unihan.zip"
ARCHIVE_SHA256 = "b8f000df69de7828d21326a2ffea462b04bc7560022989f7cc704f10521ef3e0"
INDEX = struct.Struct("<8sIH")
HEADER = struct.Struct("<4sH")
PHRASE_HEADER = struct.Struct("<4sI")
PHRASE_RECORD = struct.Struct("<64sB16s")
PHRASES = ROOT / "src/main/public-tools/pinyin-phrases.tsv"
PINYIN_PRIORITY = {
    "jian": "简见建件间检减", "ti": "体题提替",
    "zhong": "中重种钟终众忠肿衷仲盅冢踵",
    "wen": "文问闻温", "ni": "你尼泥", "hao": "好号浩",
    "wo": "我握", "shi": "是时事市十试", "de": "的得德",
    "yi": "一以已意义医", "ge": "个各歌格", "ce": "测策",
    "han": "汉含寒", "zi": "字自子", "shu": "输书数树",
    "ru": "入如", "fa": "法发", "bao": "保报包",
    "cun": "存村", "shan": "删山", "chu": "除出初",
    "zuo": "左作坐", "you": "右有又友", "kong": "空孔",
    "pin": "拼品", "yin": "音因引", "guo": "国过果",
    # 乐 yue is also attested by Unihan kHanyuPinlu/kXHC1983 (music).
    "ren": "人认任", "ri": "日", "yue": "月越约乐", "nian": "年念",
    "cheng": "程成城", "xu": "序需许", "xi": "系西希",
    "tong": "统同通", "zhi": "支之知只", "chi": "持吃迟",
    "chuang": "窗创床", "kou": "口扣",
    "chang": "长常场厂",
}


def normalize(value: str) -> str | None:
    value = value.strip().lower().replace("u:", "v").replace("ü", "v")
    decomposed = unicodedata.normalize("NFD", value).replace("u\u0308", "v")
    result = "".join(c for c in decomposed
                     if unicodedata.category(c) != "Mn")
    return result if re.fullmatch(r"[a-zv]{1,7}", result) else None


def collect() -> tuple[dict[str, list[bytes]], int]:
    if not ARCHIVE.is_file():
        raise FileNotFoundError(f"Download official Unicode Unihan.zip to {ARCHIVE}")
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Unihan source differs from the reviewed dictionary build")
    raw: dict[int, list[str]] = defaultdict(list)
    frequencies: dict[tuple[int, str], int] = {}
    with ZipFile(ARCHIVE) as archive:
        for line in archive.read("Unihan_Readings.txt").decode("utf-8").splitlines():
            if line.startswith("#") or "\t" not in line:
                continue
            code, prop, value = line.split("\t", 2)
            if prop == "kHanyuPinlu":
                for reading, amount in re.findall(r"([^\s(]+)\((\d+)\)", value):
                    key = normalize(reading)
                    if key:
                        frequencies[(int(code[2:], 16), key)] = int(amount)
                continue
            if prop not in ("kMandarin", "kHanyuPinyin"):
                continue
            readings = value.split() if prop == "kMandarin" else [
                part for group in value.split() for part in group.split(":")[-1].split(",")
            ]
            if prop == "kMandarin":
                raw[int(code[2:], 16)][:0] = readings
            else:
                raw[int(code[2:], 16)].extend(readings)
    table: dict[str, list[bytes]] = defaultdict(list)
    coverage = 0
    for row in range(87):
        for col in range(94):
            pair = bytes((0xA1 + row, 0xA1 + col))
            try:
                char = pair.decode("gb2312")
            except UnicodeDecodeError:
                continue
            readings = raw.get(ord(char), ())
            if readings:
                coverage += 1
            for reading in readings:
                key = normalize(reading)
                if key and pair not in table[key]:
                    table[key].append(pair)
    for key, pairs in table.items():
        pairs.sort(key=lambda pair: -frequencies.get((ord(pair.decode("gb2312")), key), 0))
    for key, chars in PINYIN_PRIORITY.items():
        priority = [c.encode("gb2312") for c in chars]
        table[key] = list(dict.fromkeys(priority + table.get(key, [])))
    return table, coverage


def collect_phrases(table: dict[str, list[bytes]], source: Path = PHRASES
                    ) -> list[tuple[str, bytes]]:
    result = []
    seen = set()
    for number, line in enumerate(source.read_text("utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        reading, text = line.split("\t")
        syllables = reading.split()
        if not 2 <= len(text) <= 8 or len(syllables) != len(text):
            raise ValueError(f"{source}:{number}: phrase must have 2..8 syllables")
        for key, char in zip(syllables, text):
            if char.encode("gb2312") not in table.get(key, ()):
                raise ValueError(f"{source}:{number}: invalid reading {key}: {char}")
        key = "".join(syllables)
        if len(key) > 63 or not key.isascii() or not key.isalpha():
            raise ValueError(f"{source}:{number}: invalid full pinyin")
        pair = key, text.encode("gb2312")
        if pair in seen:
            raise ValueError(f"{source}:{number}: duplicate phrase")
        seen.add(pair)
        result.append(pair)
    if source == PHRASES:
        from pinyin_common import common_phrases
        imported, _ = common_phrases(table, normalize)
        result.extend(pair for pair in imported if pair not in seen)
    # Stable ordering keeps manual priorities before imported frequency order.
    totals = defaultdict(int)
    for key, _ in result:
        totals[key] += 1
        if totals[key] + len(table.get(key, ())) > 512:
            raise ValueError(f"Too many combined candidates for {key}")
    return sorted(result, key=lambda pair: pair[0])


def build(destination: Path, phrases: bool = False) -> tuple[int, int, int]:
    table, coverage = collect()
    keys = sorted(table)
    if len(keys) > 500:
        raise ValueError(f"Too many pinyin syllables for Win16 index: {len(keys)}")
    start = HEADER.size + len(keys) * INDEX.size
    entries = []
    data = bytearray()
    for key in keys:
        pairs = table[key]
        if len(pairs) > 0xFFFF:
            raise ValueError(key)
        entries.append(INDEX.pack(key.encode("ascii").ljust(8, b"\0"),
                                  start + len(data), len(pairs)))
        data.extend(b"".join(pairs))
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = HEADER.pack(b"PYI2" if phrases else b"PYI1", len(keys)) + b"".join(entries) + data
    if phrases:
        rows = collect_phrases(table)
        payload += PHRASE_HEADER.pack(b"PYP1", len(rows))
        payload += b"".join(PHRASE_RECORD.pack(key.encode("ascii"), len(text), text)
                            for key, text in rows)
    destination.write_bytes(payload)
    return len(keys), coverage, destination.stat().st_size


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print("pinyin syllables, GB2312 characters with readings, bytes:",
          build(a.output))
