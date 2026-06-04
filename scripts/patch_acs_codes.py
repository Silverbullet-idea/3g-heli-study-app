#!/usr/bin/env python3
"""Patch truncated acs_code values in qbank_rewritten_rejects.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REJECTS_PATH = REPO_ROOT / "question-bank" / "qbank_rewritten_rejects.json"

VALID_ACS_PATTERN = re.compile(r"^[PC]H\.")

MANUAL_OVERRIDES: dict[str, str] = {
    "Night.006": "PH.XII.A",
    "Windshear.008": "PH.VIII.C",
    "Power.003": "CH.X.L",
    "Helicopter.007": "PH.I.H",
    "Spatial.008": "PH.I.H",
    "Control.008": "CH.X.L",
    "CH.XIII.B.001": "CH.XIII.B",
    "Roll.001": "PH.VIII.C",
    "Dynamic.RM.008": "PH.X.H",
}


def extract_questions(source: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for area in source.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            questions.extend(task.get("questions", []))
    return questions


def derive_acs_from_id(question_id: str) -> str | None:
    if not (question_id.startswith("PH.") or question_id.startswith("CH.")):
        return None
    parts = question_id.split(".")
    if len(parts) < 3:
        return None
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def patch_acs_codes(source: dict[str, Any]) -> tuple[int, int, int]:
    rule_a_count = 0
    rule_b_count = 0
    skipped_count = 0

    for q in extract_questions(source):
        acs_code = str(q.get("acs_code", ""))
        if VALID_ACS_PATTERN.match(acs_code):
            skipped_count += 1
            continue

        question_id = str(q.get("id", ""))
        new_code: str | None = None

        if question_id in MANUAL_OVERRIDES:
            new_code = MANUAL_OVERRIDES[question_id]
            rule_b_count += 1
        else:
            derived = derive_acs_from_id(question_id)
            if derived is not None:
                new_code = derived
                rule_a_count += 1

        if new_code is None:
            print(
                f"ERROR: cannot patch question {question_id!r} (acs_code={acs_code!r})",
                file=sys.stderr,
            )
            raise SystemExit(1)

        q["acs_code"] = new_code

    return rule_a_count, rule_b_count, skipped_count


def validate_all(source: dict[str, Any]) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    for q in extract_questions(source):
        acs_code = str(q.get("acs_code", ""))
        if not VALID_ACS_PATTERN.match(acs_code):
            failures.append((str(q.get("id", "")), acs_code))
    return failures


def main() -> None:
    if not REJECTS_PATH.is_file():
        print(f"ERROR: file not found: {REJECTS_PATH}", file=sys.stderr)
        raise SystemExit(1)

    with REJECTS_PATH.open("r", encoding="utf-8") as f:
        source = json.load(f)

    rule_a_count, rule_b_count, skipped_count = patch_acs_codes(source)

    print(f"Patched via Rule A (auto-derive): {rule_a_count}")
    print(f"Patched via Rule B (manual override): {rule_b_count}")
    print(f"Already had correct ACS codes (skipped): {skipped_count}")

    with REJECTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(source, f, ensure_ascii=False, indent=2)
        f.write("\n")

    failures = validate_all(source)
    if failures:
        print("Validation failed — truncated ACS codes remain:", file=sys.stderr)
        for question_id, acs_code in failures:
            print(f"  {question_id}: {acs_code!r}", file=sys.stderr)
        raise SystemExit(1)

    print("Validation passed — all ACS codes are standard.")


if __name__ == "__main__":
    main()
