"""Record NE segment, resource, and relocation-trailer boundaries for stage 5.

Some accepted linker segments set the relocation flag but have no parseable
trailer before the next segment. Preserve their opaque trailer bytes and flag
the ambiguity instead of guessing a relocation count from the next segment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from inspect_ne import read_ne  # noqa: E402

BASE = HERE / "snapshot/handoff"
RECORD = HERE / "ne-baseline.json"
FILES = (
    "OFFICE/WORD/WINWORD.EXE",
    "OFFICE/CGA/EXCEL.EXE", "OFFICE/CGA/XLCORE.EXE",
    "OFFICE/VGA/EXCEL.EXE", "OFFICE/VGA/XLCORE.EXE",
    "SYSTEM/CGA.DRV", "SYSTEM/CEPSON.DRV",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def audit(path: Path) -> dict:
    data = path.read_bytes()
    at = struct.unpack_from("<I", data, 0x3C)[0]
    if data[at:at + 2] != b"NE":
        raise ValueError(f"missing NE header: {path}")
    resource_start = at + struct.unpack_from("<H", data, at + 0x24)[0]
    resident_start = at + struct.unpack_from("<H", data, at + 0x26)[0]
    if resource_start == resident_start:
        # The 4-KiB Excel adapter has no resource table. The existing generic
        # inspector expects a terminator and reads into its name table.
        table = at + struct.unpack_from("<H", data, at + 0x22)[0]
        segments = []
        for index in range(struct.unpack_from("<H", data, at + 0x1C)[0]):
            sector, length, flags, minimum = struct.unpack_from("<HHHH", data, table + 8 * index)
            segments.append({"index": index + 1, "file_offset_units": sector,
                             "file_length": length or 65536, "flags": flags,
                             "min_alloc": minimum or 65536})
        ne = {"ne_offset": at, "resource_shift": 0, "resource_kinds": [],
              "segments": segments, "module_imports": []}
    else:
        ne = read_ne(path)
    shift = struct.unpack_from("<H", data, at + 0x32)[0]
    resource_ranges = []
    kinds = []
    for kind in ne["resource_kinds"]:
        rows = []
        for resource in kind["resources"]:
            start = resource["sector"] << ne["resource_shift"]
            end = start + resource["bytes"]
            if start < at or end > len(data):
                raise ValueError(f"NE resource outside file: {path}")
            resource_ranges.append(start)
            rows.append({"id": resource["id"], "start": start, "end": end,
                         "flags": resource["flags"], "sha256": sha(data[start:end])})
        kinds.append({"type": kind["type"], "named_type": kind["named_type"],
                      "resources": rows})
    segment_starts = [s["file_offset_units"] << shift for s in ne["segments"]
                      if s["file_offset_units"]]
    limits = sorted(set(segment_starts + resource_ranges + [len(data)]))
    segments = []
    for source in ne["segments"]:
        start = source["file_offset_units"] << shift
        if not source["file_offset_units"]:
            segments.append({"index": source["index"], "file_backed": False,
                             "flags": source["flags"], "min_alloc": source["min_alloc"]})
            continue
        end = start + source["file_length"]
        limit = next((point for point in limits if point > start), len(data))
        if start < at or end > limit:
            raise ValueError(f"NE segment overlaps next region: {path}, {source['index']}")
        trailer = data[end:limit]
        detail = {"index": source["index"], "file_backed": True,
                  "start": start, "end": end, "next_region": limit,
                  "flags": source["flags"], "min_alloc": source["min_alloc"],
                  "payload_sha256": sha(data[start:end]),
                  "trailer_sha256": sha(trailer), "trailer_bytes": len(trailer),
                  "relocation_flag": bool(source["flags"] & 0x0100)}
        if detail["relocation_flag"]:
            if len(trailer) >= 2:
                count = struct.unpack_from("<H", trailer)[0]
                if 2 + 8 * count <= len(trailer):
                    detail["relocation_records"] = count
                    detail["relocation_table_sha256"] = sha(trailer[:2 + 8 * count])
                else:
                    detail["relocation_parse"] = "opaque_count_exceeds_region"
            else:
                detail["relocation_parse"] = "opaque_no_count_in_region"
        segments.append(detail)
    return {"sha256": sha(data), "bytes": len(data), "ne_offset": at,
            "segment_shift": shift, "segment_count": len(segments),
            "resource_table_start": at + struct.unpack_from("<H", data, at + 0x24)[0],
            "resident_name_table_start": at + struct.unpack_from("<H", data, at + 0x26)[0],
            "resource_shift": ne["resource_shift"], "segments": segments,
            "resource_kinds": kinds, "imports": ne["module_imports"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()
    current = {name: audit(BASE / name) for name in FILES}
    if args.write_baseline:
        if RECORD.exists():
            raise ValueError("NE baseline exists; do not overwrite")
        RECORD.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        if current != json.loads(RECORD.read_text(encoding="utf-8")):
            raise ValueError("NE baseline drift")
    print("PASS: NE modules", len(current), "segments",
          sum(item["segment_count"] for item in current.values()),
          "resources", sum(len(kind["resources"]) for item in current.values()
                           for kind in item["resource_kinds"]))


if __name__ == "__main__":
    main()
