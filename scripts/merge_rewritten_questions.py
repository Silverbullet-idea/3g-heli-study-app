#!/usr/bin/env python3
"""Merge verified rewritten questions from qbank_rewritten_rejects.json into main banks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTION_BANK_DIR = REPO_ROOT / "question-bank"
PRIVATE_BANK_PATH = QUESTION_BANK_DIR / "qbank_private_helicopter.json"
COMMERCIAL_BANK_PATH = QUESTION_BANK_DIR / "qbank_commercial_helicopter.json"
UNMATCHED_LOG_PATH = QUESTION_BANK_DIR / "merge_unmatched.log"

ELIGIBLE_STATUSES = {"PASS", "REVIEWED_PASS"}


def load_source(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_questions(source: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for area in source.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            questions.extend(task.get("questions", []))
    return questions


def target_bank_for_id(question_id: str) -> Path | None:
    if question_id.startswith("PH."):
        return PRIVATE_BANK_PATH
    if question_id.startswith("CH."):
        return COMMERCIAL_BANK_PATH
    return None


def filter_eligible(questions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    eligible: list[dict[str, Any]] = []
    skip_counts: dict[str, int] = {
        "wrong_status": 0,
        "already_verified": 0,
        "unknown_prefix": 0,
    }
    for q in questions:
        qid = str(q.get("id", ""))
        status = str(q.get("verification", {}).get("status", ""))
        ryan_verified = bool(q.get("ryan_verified", False))

        if ryan_verified:
            skip_counts["already_verified"] += 1
            continue
        if status not in ELIGIBLE_STATUSES:
            skip_counts["wrong_status"] += 1
            continue
        if target_bank_for_id(qid) is None:
            skip_counts["unknown_prefix"] += 1
            continue
        eligible.append(q)
    return eligible, skip_counts


def build_task_index(bank: dict[str, Any]) -> dict[str, tuple[int, int]]:
    """Map task acs_code -> (area_index, task_index). Prefer longest prefix match key."""
    index: dict[str, tuple[int, int]] = {}
    for ai, area in enumerate(bank.get("areas_of_operation", [])):
        for ti, task in enumerate(area.get("tasks", [])):
            acs = str(task.get("acs_code", "")).strip()
            if acs:
                index[acs] = (ai, ti)
    return index


def find_task_location(bank: dict[str, Any], acs_code: str) -> tuple[int, int] | None:
    acs_code = str(acs_code).strip()
    if not acs_code:
        return None

    best: tuple[int, int] | None = None
    best_len = -1
    for ai, area in enumerate(bank.get("areas_of_operation", [])):
        for ti, task in enumerate(area.get("tasks", [])):
            task_acs = str(task.get("acs_code", "")).strip()
            if not task_acs:
                continue
            if acs_code == task_acs or acs_code.startswith(task_acs + "."):
                if len(task_acs) > best_len:
                    best = (ai, ti)
                    best_len = len(task_acs)
    return best


def count_questions(bank: dict[str, Any]) -> int:
    total = 0
    for area in bank.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            total += len(task.get("questions", []))
    return total


def log_unmatched(question_id: str, acs_code: str, reason: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    UNMATCHED_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with UNMATCHED_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp}\t{question_id}\t{acs_code}\t{reason}\n")


def plan_merge(eligible: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    banks: dict[str, dict[str, Any]] = {}
    bank_paths = {"private": PRIVATE_BANK_PATH, "commercial": COMMERCIAL_BANK_PATH}
    for key, path in bank_paths.items():
        if path.is_file():
            banks[key] = load_source(path)

    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for q in eligible:
        qid = str(q["id"])
        bank_key = "private" if qid.startswith("PH.") else "commercial"
        bank = banks.get(bank_key)
        if bank is None:
            unmatched.append({**q, "_reason": "target bank file missing"})
            continue
        loc = find_task_location(bank, str(q.get("acs_code", "")))
        if loc is None:
            unmatched.append({**q, "_reason": "no matching task for acs_code"})
        else:
            matched.append({**q, "_bank_key": bank_key, "_location": loc})

    return matched, unmatched, banks


def print_dry_run_table(eligible: list[dict[str, Any]], matched: list[dict[str, Any]], unmatched: list[dict[str, Any]]) -> None:
    matched_ids = {str(m["id"]) for m in matched}
    print(f"{'Question ID':<22} {'Target bank':<12} {'ACS code':<20} {'Match':<6}")
    print("-" * 64)
    for q in eligible:
        qid = str(q["id"])
        bank = "private" if qid.startswith("PH.") else "commercial"
        acs = str(q.get("acs_code", ""))[:20]
        found = "yes" if qid in matched_ids else "no"
        print(f"{qid:<22} {bank:<12} {acs:<20} {found:<6}")
    print()
    print(f"Eligible: {len(eligible)}  Matched: {len(matched)}  Unmatched: {len(unmatched)}")


def apply_merge(matched: list[dict[str, Any]], banks: dict[str, dict[str, Any]]) -> tuple[int, int]:
    private_count = 0
    commercial_count = 0
    for item in matched:
        bank_key = item["_bank_key"]
        ai, ti = item["_location"]
        bank = banks[bank_key]
        q_copy = {k: v for k, v in item.items() if not k.startswith("_")}
        bank["areas_of_operation"][ai]["tasks"][ti]["questions"].append(q_copy)
        if bank_key == "private":
            private_count += 1
        else:
            commercial_count += 1

    for bank_key, bank in banks.items():
        bank["total_questions"] = count_questions(bank)
        path = PRIVATE_BANK_PATH if bank_key == "private" else COMMERCIAL_BANK_PATH
        with path.open("w", encoding="utf-8") as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return private_count, commercial_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge verified rewritten questions into main banks.")
    parser.add_argument("--source", required=True, help="Path to qbank_rewritten_rejects.json")
    parser.add_argument("--dry-run", action="store_true", help="Print merge plan without modifying files")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.is_file():
        print(f"ERROR: source file not found: {source_path}", file=sys.stderr)
        raise SystemExit(1)

    source = load_source(source_path)
    all_questions = extract_questions(source)
    eligible, skip_counts = filter_eligible(all_questions)

    print(f"Source questions: {len(all_questions)}")
    print(
        f"Skipped — wrong status (FLAG/ESCALATE/UNVERIFIED/FAIL): {skip_counts['wrong_status']}, "
        f"already in main bank (ryan_verified): {skip_counts['already_verified']}, "
        f"unknown ID prefix: {skip_counts['unknown_prefix']}"
    )
    print()

    matched, unmatched, banks = plan_merge(eligible)
    print_dry_run_table(eligible, matched, unmatched)

    if args.dry_run:
        return

    private_matched = sum(1 for m in matched if m["_bank_key"] == "private")
    commercial_matched = sum(1 for m in matched if m["_bank_key"] == "commercial")
    prompt = (
        f"Merge {private_matched} questions into private bank and "
        f"{commercial_matched} into commercial bank.\n"
        f"Type YES to confirm: "
    )
    answer = input(prompt).strip()
    if answer != "YES":
        print("Aborted — confirmation not received.")
        raise SystemExit(0)

    for item in unmatched:
        log_unmatched(str(item["id"]), str(item.get("acs_code", "")), str(item.get("_reason", "unmatched")))

    private_count, commercial_count = apply_merge(matched, banks)
    print(
        f"Merged {private_count} into private, {commercial_count} into commercial, "
        f"{len(unmatched)} unmatched (see merge_unmatched.log)"
    )


if __name__ == "__main__":
    main()
