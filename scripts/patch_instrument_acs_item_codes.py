#!/usr/bin/env python3
"""Prefix Instrument ACS JSON item lines with IH. codes (matches Private PH. format)."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ACS_PATH = REPO / "extracted-data/faa/FAA-S-ACS-14_Instrument_Helicopter_ACS.json"
VALID = re.compile(r"^IH\.[IVXLC]+\.[A-Z]+\.(K|R|S)\d+\s")


def int_to_roman(n: int) -> str:
    vals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    out: list[str] = []
    for v, sym in vals:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def task_letter(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return f"A{index}"


def patch_acs(data: dict) -> int:
    patched = 0
    for ai, area in enumerate(data.get("areas_of_operation") or []):
        roman = int_to_roman(ai + 1)
        for ti, task in enumerate(area.get("tasks") or []):
            letter = task_letter(ti)
            for cat_key, cat_letter in (
                ("knowledge", "K"),
                ("risk_management", "R"),
                ("skills", "S"),
            ):
                items = task.get(cat_key) or []
                new_items: list[str] = []
                for n, raw in enumerate(items, start=1):
                    line = str(raw).strip()
                    if VALID.match(line + " "):
                        new_items.append(line)
                        continue
                    code = f"IH.{roman}.{letter}.{cat_letter}{n}"
                    new_items.append(f"{code} {line}")
                    patched += 1
                task[cat_key] = new_items
    return patched


def main() -> None:
    data = json.loads(ACS_PATH.read_text(encoding="utf-8"))
    count = patch_acs(data)
    ACS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {count} ACS item lines in {ACS_PATH}")


if __name__ == "__main__":
    main()
