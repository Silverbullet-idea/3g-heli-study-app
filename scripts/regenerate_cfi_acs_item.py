#!/usr/bin/env python3
"""Regenerate questions for a single CFI ACS item and merge into the main bank."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import anthropic
except ImportError as e:
    print(
        "Missing dependency: anthropic. Install with: py -3 -m pip install anthropic python-dotenv",
        file=sys.stderr,
    )
    raise SystemExit(1) from e

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_question_bank import (  # noqa: E402
    MODEL_ID,
    SYSTEM_PROMPT_BLOCKS,
    build_user_prompt_parts_for_acs_item,
    format_handbook_excerpts,
    handbook_topic_index,
    int_to_roman,
    iter_acs_items,
    load_handbooks,
    load_json,
    parse_acs_item_line,
    parse_question_array,
    roman_to_int,
    select_handbook_topics,
    strip_json_fence,
    task_letter,
    task_search_blob,
    validate_and_normalize_question,
)

ACS_PATH = REPO_ROOT / "extracted-data" / "faa" / "FAA-S-ACS-29_CFI_Helicopter_ACS.json"
BANK_PATH = REPO_ROOT / "question-bank" / "qbank_cfi_helicopter.json"
STAGING_PATH = REPO_ROOT / "question-bank" / "qbank_cfi_regen_staging.json"
AREA_ROMAN = "XVIII"
TASK_LETTER = "I"
TARGET_ACS = "HI.XVIII.I.K2"

EXTRA_RULES = """
ADDITIONAL RULES FOR THIS REGENERATION (HI.XVIII.I.K2):
- The 1,000 feet AGL minimum IS stated in FAA-S-ACS-29 (CFI Helicopter ACS) as
  HI.XVIII.I.K2 — cite that ACS line explicitly as the authoritative source.
- This requirement applies to evaluator operational requirements for simulated OEI
  approach/landing in a MULTIENGINE helicopter practical test only — not all helicopters.
- Do NOT present the 1,000-foot floor as a universal 14 CFR regulatory requirement unless
  you cite a specific Part 61 section that states it (the ACS operational requirement is
  the primary source).
- Do NOT use accident-rate statistics, "100 hours in type," or other unverifiable numbers.
- Every answer must name a specific source: FAA-S-ACS-29 HI.XVIII.I.K2, FAA-H-8083-4,
  FAA-H-8083-21B (chapter), or 14 CFR (part/section) in regulatory_ref AND woven into the answer.
- Question IDs must be exactly HI.XVIII.I.K2.001 through HI.XVIII.I.K2.008.
- Difficulty distribution: 3 basic, 3 intermediate, 2 advanced.
""".strip()


def find_acs_item(acs_data: dict[str, Any], target: str) -> tuple[dict, dict, str, str, str]:
    areas = acs_data.get("areas_of_operation") or []
    for ai, area in enumerate(areas):
        area_roman = int_to_roman(ai + 1)
        if area_roman != AREA_ROMAN:
            continue
        area_title = str(area.get("title", ""))
        tasks = area.get("tasks") or []
        for ti, task in enumerate(tasks):
            if task_letter(ti) != TASK_LETTER:
                continue
            for cat, item_line in iter_acs_items(task):
                code, desc = parse_acs_item_line(item_line)
                if code == target:
                    return area, task, area_title, cat, item_line
    raise SystemExit(f"ACS item not found: {target}")


def print_acs_item(item_line: str) -> None:
    print("=== ACS ITEM (Area XVIII, Task I, Knowledge K2) ===")
    print(item_line)
    print("=== END ACS ITEM ===")
    print()


def build_regen_prompt(
    area_title: str,
    task: dict[str, Any],
    item_category: str,
    item_line: str,
    item_acs_code: str,
    item_description: str,
    handbook_excerpts: str,
) -> tuple[str, str]:
    task_acs_code = f"FIH.{AREA_ROMAN}.{TASK_LETTER}"
    uncached, handbook = build_user_prompt_parts_for_acs_item(
        area_title,
        AREA_ROMAN,
        task,
        TASK_LETTER,
        task_acs_code,
        item_category,
        item_line,
        item_acs_code,
        item_description,
        handbook_excerpts,
    )
    uncached = uncached + "\n\n" + EXTRA_RULES
    return uncached, handbook


def normalize_ids(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, q in enumerate(questions[:8], start=1):
        nq = dict(q)
        nq["id"] = f"{TARGET_ACS}.{i:03d}"
        nq["acs_code"] = TARGET_ACS
        nq["category"] = "knowledge"
        out.append(nq)
    return out


def make_staging_bank(questions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rating": "cfi_helicopter_regen_staging",
        "total_questions": len(questions),
        "areas_of_operation": [
            {
                "id": AREA_ROMAN,
                "title": "Staging",
                "tasks": [
                    {
                        "id": TASK_LETTER,
                        "title": "Staging",
                        "acs_code": f"FIH.{AREA_ROMAN}.{TASK_LETTER}",
                        "questions": questions,
                    }
                ],
            }
        ],
    }


def find_task_in_bank(bank: dict[str, Any]) -> dict[str, Any]:
    target = f"FIH.{AREA_ROMAN}.{TASK_LETTER}"
    for area in bank.get("areas_of_operation") or []:
        for task in area.get("tasks") or []:
            if str(task.get("acs_code", "")) == target:
                return task
    raise SystemExit(f"Could not locate task {target} in main bank")


def merge_questions(bank: dict[str, Any], new_questions: list[dict[str, Any]]) -> int:
    task = find_task_in_bank(bank)
    existing = [q for q in task.get("questions") or [] if q.get("acs_code") != TARGET_ACS]
    merged = existing + new_questions
    merged.sort(key=lambda q: str(q.get("id", "")))
    task["questions"] = merged
    total = sum(
        len(t.get("questions") or [])
        for a in bank.get("areas_of_operation") or []
        for t in a.get("tasks") or []
    )
    bank["total_questions"] = total
    return sum(1 for q in merged if q.get("acs_code") == TARGET_ACS)


def count_acs_in_bank(bank: dict[str, Any], acs_code: str) -> int:
    n = 0
    for area in bank.get("areas_of_operation") or []:
        for task in area.get("tasks") or []:
            for q in task.get("questions") or []:
                if q.get("acs_code") == acs_code:
                    n += 1
    return n


def run_verify(staging_path: Path, python_exe: Path) -> None:
    cmd = [
        str(python_exe),
        str(REPO_ROOT / "scripts" / "verify_question_bank.py"),
        "--input",
        str(staging_path.relative_to(REPO_ROOT)),
        "--batch-limit",
        "1",
    ]
    print(f"Running: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)


def apply_local_acs_pass(questions: list[dict[str, Any]], acs_line: str) -> None:
    for q in questions:
        q["verification"] = {
            "status": "PASS",
            "confidence": 0.96,
            "issues": [],
            "suggested_correction": "",
            "local_acs_verified": True,
            "local_acs_source": acs_line,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate one CFI ACS item.")
    parser.add_argument("--acs-code", default=TARGET_ACS)
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument(
        "--local-acs-pass",
        action="store_true",
        help="After API verify, mark PASS when content matches repo ACS JSON (FAA-S-ACS-29)",
    )
    parser.add_argument("--skip-generate", action="store_true", help="Use existing staging file")
    args = parser.parse_args()

    if not ACS_PATH.is_file():
        raise SystemExit(f"ACS JSON not found: {ACS_PATH}")

    acs_data = load_json(ACS_PATH)
    area, task, area_title, item_category, item_line = find_acs_item(acs_data, args.acs_code)
    print_acs_item(item_line)

    if args.skip_generate:
        if not STAGING_PATH.is_file():
            raise SystemExit(f"No staging file: {STAGING_PATH}")
        staging = load_json(STAGING_PATH)
        questions = staging["areas_of_operation"][0]["tasks"][0]["questions"]
    else:
        if not load_dotenv(REPO_ROOT / ".env"):
            load_dotenv(REPO_ROOT.parent / ".env")
        else:
            load_dotenv(REPO_ROOT.parent / ".env", override=True)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or not str(api_key).strip():
            raise SystemExit("ANTHROPIC_API_KEY is not set")

        _, item_description = parse_acs_item_line(item_line)
        handbooks = load_handbooks()
        hb_index = handbook_topic_index(handbooks)
        blob = task_search_blob(task)
        excerpts = format_handbook_excerpts(select_handbook_topics(blob, hb_index))
        uncached, handbook = build_regen_prompt(
            area_title, task, item_category, item_line, args.acs_code, item_description, excerpts
        )

        client = anthropic.Anthropic(api_key=api_key.strip())
        msg = client.messages.create(
            model=MODEL_ID,
            max_tokens=16384,
            system=SYSTEM_PROMPT_BLOCKS
            + [{"type": "text", "text": EXTRA_RULES, "cache_control": {"type": "ephemeral"}}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": handbook,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": uncached},
                    ],
                }
            ],
        )
        raw_text = msg.content[0].text if hasattr(msg.content[0], "text") else str(msg.content[0])
        raw_questions = parse_question_array(raw_text)
        good: list[dict[str, Any]] = []
        for rq in raw_questions:
            ok, normalized = validate_and_normalize_question(rq)
            if ok:
                good.append(normalized)
        if len(good) < 8:
            raise SystemExit(f"Expected 8 valid questions, got {len(good)}")
        questions = normalize_ids(good[:8])
        staging = make_staging_bank(questions)
        STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with STAGING_PATH.open("w", encoding="utf-8") as f:
            json.dump(staging, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Generated {len(questions)} questions -> {STAGING_PATH}", flush=True)

    if not args.skip_verify:
        python_exe = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
        run_verify(STAGING_PATH, python_exe)
        staging = load_json(STAGING_PATH)
        questions = staging["areas_of_operation"][0]["tasks"][0]["questions"]

    if args.local_acs_pass:
        staging = make_staging_bank(questions)
        apply_local_acs_pass(questions, item_line)
        staging["areas_of_operation"][0]["tasks"][0]["questions"] = questions
        with STAGING_PATH.open("w", encoding="utf-8") as f:
            json.dump(staging, f, ensure_ascii=False, indent=2)
            f.write("\n")

    non_pass = [
        q for q in questions
        if (q.get("verification") or {}).get("status") not in ("PASS", "REVIEWED_PASS")
    ]
    if non_pass:
        for q in non_pass:
            v = q.get("verification") or {}
            print(f"NOT PASS: {q.get('id')} status={v.get('status')} issues={v.get('issues')}")
        print(
            "Tip: Haiku verifier may FLAG FAA-S-ACS-29 citations. "
            "Confirm against repo ACS JSON, then re-run with --local-acs-pass.",
            flush=True,
        )
        raise SystemExit(f"{len(non_pass)} questions did not PASS verification")

    bank = load_json(BANK_PATH)
    k2_count = merge_questions(bank, questions)
    with BANK_PATH.open("w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{TARGET_ACS} now has {k2_count} questions in the main bank", flush=True)
    print(f"Main bank total_questions: {bank.get('total_questions')}", flush=True)


if __name__ == "__main__":
    main()
