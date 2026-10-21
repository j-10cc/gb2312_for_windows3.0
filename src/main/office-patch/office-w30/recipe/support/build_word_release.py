"""Fixed UI link step used by the final Word build.

Retains the original fixed_ui implementation and data, without old stage orchestration.
"""
from fixed_ui_data import FIXED_TEXT,SIMPLE_COUNTS,SEARCH_FIELDS,DIALOG_BLOCKS

def positions(data: bytes, token: bytes) -> list[int]:
    found = []
    at = 0
    while (at := data.find(token, at)) >= 0:
        found.append(at)
        at += len(token)
    return found

def fixed_ui(data: bytes) -> tuple[bytes, list[dict]]:
    original = data
    patched = bytearray(data)
    changes: list[dict] = []
    translations = {old: chinese.encode("gb2312") for _, old, chinese in FIXED_TEXT}
    # The ribbon's Pts field names the font-size selector, so the Chinese UI
    # term is 字号. It fits the original four-byte field without shifting data.
    translations[b"Pts:"] = "字号".encode("gb2312")

    def replace(at: int, old: bytes) -> None:
        new = translations[old]
        if len(new) > len(old) or original[at:at + len(old)] != old:
            raise ValueError(f"Word fixed UI drift at {at:#x}: {old!r}")
        if any(at < item["offset"] + item["length"] and
               item["offset"] < at + len(old) for item in changes):
            raise ValueError("overlapping Word fixed UI fields")
        patched[at:at + len(old)] = new.ljust(len(old), b" ")
        changes.append({"offset": at, "length": len(old),
                        "original": old.decode("ascii"),
                        "localized": new.decode("gb2312")})

    for old, count in SIMPLE_COUNTS.items():
        found = positions(original, old)
        if len(found) != count:
            raise ValueError(f"Word fixed field {old!r}: {len(found)} != {count}")
        for at in found:
            replace(at, old)
    for old, count, chinese in SEARCH_FIELDS:
        found = positions(original, old + b"\0")
        if len(found) != count:
            raise ValueError(f"Word search dialog field drift: {old!r}, {len(found)}")
        translations[old] = chinese.encode("gb2312")
        for at in found:
            replace(at, old)
    for anchor, span, fields in DIALOG_BLOCKS:
        starts = positions(original, anchor)
        if len(starts) != 1:
            raise ValueError(f"Word SDM dialog anchor drift: {anchor!r}")
        start = starts[0]
        block = original[start:start + span]
        for old, chinese in fields:
            token = old + b"\0"
            hits = [at for at in positions(block, token)
                    if at == 0 or block[at - 1] == 0]
            if len(hits) != 1:
                raise ValueError(f"Word SDM dialog field drift: {old!r}, {hits}")
            translations[old] = chinese.encode("gb2312")
            replace(start + hits[0], old)
    prompt = positions(original, b"Please enter your name and initials.")
    names = [at for at in positions(original, b"&Name:")
             if prompt[0] < at < prompt[0] + 128]
    if len(names) != 1:
        raise ValueError("Word first-run name label is not unique")
    replace(names[0], b"&Name:")
    status = positions(original, b" Pg ")
    if len(status) != 1:
        raise ValueError("Word status block is not unique")
    for old in (b" Pg ", b"Sec ", b"At ", b"Ln ", b"Col "):
        found = [at for at in positions(original, old)
                 if status[0] <= at < status[0] + 48]
        if len(found) != 1:
            raise ValueError(f"Word status label {old!r} drift")
        replace(found[0], old)
    restored = bytearray(patched)
    for item in changes:
        at = item["offset"]
        restored[at:at + item["length"]] = original[at:at + item["length"]]
    if restored != original:
        raise ValueError("Word fixed UI patch changed bytes outside strings")
    return bytes(patched), changes
