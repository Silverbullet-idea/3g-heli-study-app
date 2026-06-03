#!/usr/bin/env python3
"""Rewrite rejected oral-exam questions from review_changes.log via Anthropic API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
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
REVIEW_LOG_PATH = REPO_ROOT / "question-bank" / "review_changes.log"
OUTPUT_PATH = REPO_ROOT / "question-bank" / "qbank_rewritten_rejects.json"
ERRORS_LOG_PATH = REPO_ROOT / "question-bank" / "rewrite_errors.log"
CHECKPOINT_EVERY = 25
API_MAX_ATTEMPTS = 4  # initial try + up to 3 retries
RETRY_SLEEP_SEC = 5
SUCCESS_SLEEP_SEC = 1
MODEL_ID = "claude-sonnet-4-6"

SYSTEM_PROMPT = """
You are an expert helicopter CFI and FAA oral exam question writer with deep knowledge
of FAA-H-8083-21B (Helicopter Flying Handbook), FAA-H-8083-4 (Helicopter Instructor's
Handbook), FAA-H-8083-15B (Instrument Flying Handbook), 14 CFR Parts 61 and 91,
and all FAA ACS standards for helicopter ratings.

You will receive a rejected oral exam question, its original answer, and the specific
reason it was rejected. Your job is to rewrite the answer (and question if needed)
to fix exactly the identified problem — nothing more.

Rules:
- Fix only what the rejection reason identifies. Do not rewrite what was correct.
- Every factual claim must be supportable from FAA-H-8083-21B, FAA-H-8083-4,
  FAA-H-8083-15B, 14 CFR, or the applicable ACS standard.
- Do not invent specific numeric values, tolerances, or regulatory citations
  that are not clearly established in FAA publications.
- If the rejection was about overclaiming specificity, rewrite to say what the
  FAA handbook does say, without adding unsupported precision.
- Keep the question at the same difficulty level (basic / intermediate / advanced).
- Return ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
  {
    "id": "<question id>",
    "question": "<rewritten question or original if unchanged>",
    "answer": "<rewritten answer>",
    "rewrite_note": "<one sentence describing what was fixed>"
  }
""".strip()

SYSTEM_PROMPT_BLOCKS: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]

SOURCE_BANKS = [
    REPO_ROOT / "question-bank" / "qbank_private_helicopter.json",
    REPO_ROOT / "question-bank" / "qbank_commercial_helicopter.json",
]

REJECTED_BLOCK_RE = re.compile(
    r"--- REJECTED ---\n(.*?)\n----------------------------------------",
    re.DOTALL,
)


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def parse_section(block: str, label: str, next_label: str | None = None) -> str:
    start_marker = f"{label}\n"
    start = block.find(start_marker)
    if start == -1:
        return ""
    content_start = start + len(start_marker)
    if next_label:
        end = block.find(f"\n{next_label}\n", content_start)
        if end == -1:
            end = block.find(f"\n{next_label}", content_start)
        if end == -1:
            end = len(block)
    else:
        end = len(block)
    return block[content_start:end].strip()


def parse_rejected_block(block: str) -> dict[str, str] | None:
    question_id = ""
    for line in block.splitlines():
        if line.startswith("Question ID:"):
            question_id = line.split(":", 1)[1].strip()
            break
    if not question_id:
        return None

    acs_code = ""
    difficulty = ""
    for line in block.splitlines():
        if line.startswith("ACS Code:"):
            acs_code = line.split(":", 1)[1].strip()
        elif line.startswith("Difficulty:"):
            difficulty = line.split(":", 1)[1].strip()

    question = parse_section(block, "Question:", "Answer (at time of rejection):")
    answer = parse_section(block, "Answer (at time of rejection):", "Reason for rejection (verifier notes):")
    rejection_reason = parse_section(block, "Reason for rejection (verifier notes):", "Reviewed:")

    if not question or not answer:
        return None

    return {
        "id": question_id,
        "acs_code": acs_code,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "rejection_reason": rejection_reason,
    }


def parse_rejected_blocks(log_text: str) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for match in REJECTED_BLOCK_RE.finditer(log_text):
        item = parse_rejected_block(match.group(1))
        if item:
            parsed.append(item)
    return parsed


def load_original_questions_by_id() -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for bank_path in SOURCE_BANKS:
        if not bank_path.is_file():
            continue
        with bank_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for area in data.get("areas_of_operation", []):
            for task in area.get("tasks", []):
                for q in task.get("questions", []):
                    qid = q.get("id")
                    if qid:
                        by_id[str(qid)] = q
    return by_id


def build_user_message(item: dict[str, str]) -> str:
    return f"""Question ID: {item["id"]}
ACS Code: {item["acs_code"]}
Difficulty: {item["difficulty"]}

Original Question:
{item["question"]}

Original Answer:
{item["answer"]}

Rejection Reason:
{item["rejection_reason"]}

Rewrite the answer (and question if needed) to fix the identified problem.
Stay grounded in FAA publications. Return JSON only.
"""


def call_rewrite_api(client: anthropic.Anthropic, item: dict[str, str]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, API_MAX_ATTEMPTS + 1):
        try:
            msg = client.messages.create(
                model=MODEL_ID,
                max_tokens=1024,
                system=SYSTEM_PROMPT_BLOCKS,
                messages=[{"role": "user", "content": build_user_message(item)}],
            )
            block = msg.content[0]
            raw_text = block.text if hasattr(block, "text") else str(block)
            payload = json.loads(strip_json_fence(raw_text))
            if not isinstance(payload, dict):
                raise ValueError("API response is not a JSON object")
            for key in ("id", "question", "answer", "rewrite_note"):
                if key not in payload or not str(payload[key]).strip():
                    raise ValueError(f"API response missing required field: {key}")
            return payload
        except Exception as e:
            last_error = e
            if attempt < API_MAX_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SEC)
    raise RuntimeError(str(last_error) if last_error else "Unknown API error")


def build_question_record(
    item: dict[str, str],
    api_result: dict[str, Any],
    originals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    original = originals.get(item["id"], {})
    return {
        "id": str(api_result.get("id", item["id"])),
        "acs_code": item["acs_code"] or str(original.get("acs_code", "")),
        "category": str(original.get("category", "knowledge")),
        "difficulty": item["difficulty"] or str(original.get("difficulty", "basic")),
        "question": str(api_result["question"]),
        "answer": str(api_result["answer"]),
        "regulatory_ref": str(original.get("regulatory_ref", "")),
        "tags": [],
        "ryan_verified": False,
        "ryan_notes": "",
        "follow_up": "",
        "follow_up_answer": "",
        "verification": {
            "status": "UNVERIFIED",
            "confidence": 0,
            "issues": [],
            "suggested_correction": "",
        },
        "rewrite_note": str(api_result["rewrite_note"]),
    }


def build_output_skeleton(question_count: int) -> dict[str, Any]:
    return {
        "rating": "mixed",
        "source": "rewritten_rejects",
        "generated_date": date.today().isoformat(),
        "generation_model": MODEL_ID,
        "total_questions": question_count,
        "areas_of_operation": [
            {
                "id": "REWRITTEN",
                "title": "Rewritten Rejected Questions",
                "tasks": [
                    {
                        "id": "REWRITTEN.001",
                        "title": "Rewritten Rejects",
                        "acs_code": "REWRITTEN",
                        "questions": [],
                    }
                ],
            }
        ],
    }


def save_output(data: dict[str, Any], path: Path) -> None:
    data["total_questions"] = len(data["areas_of_operation"][0]["tasks"][0]["questions"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def log_error(question_id: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ERRORS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ERRORS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp}\t{question_id}\t{message}\n")


def run_dry_run(rejected: list[dict[str, str]], limit: int = 5) -> None:
    print(f"Parsed {len(rejected)} REJECTED blocks from {REVIEW_LOG_PATH}")
    print(f"Showing first {min(limit, len(rejected))} blocks:\n")
    for i, item in enumerate(rejected[:limit], start=1):
        q_preview = item["question"][:80].replace("\n", " ")
        if len(item["question"]) > 80:
            q_preview += "..."
        r_preview = item["rejection_reason"][:80].replace("\n", " ")
        if len(item["rejection_reason"]) > 80:
            r_preview += "..."
        print(f"--- Block {i} ---")
        print(f"  Question ID: {item['id']}")
        print(f"  ACS Code:    {item['acs_code']}")
        print(f"  Difficulty:  {item['difficulty']}")
        print(f"  Question:    {q_preview}")
        print(f"  Reason:      {r_preview}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite rejected questions from review_changes.log.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the first 5 REJECTED blocks without calling the API.",
    )
    args = parser.parse_args()

    if not REVIEW_LOG_PATH.is_file():
        print(f"ERROR: review log not found: {REVIEW_LOG_PATH}", file=sys.stderr)
        raise SystemExit(1)

    log_text = REVIEW_LOG_PATH.read_text(encoding="utf-8")
    rejected = parse_rejected_blocks(log_text)
    if not rejected:
        print("ERROR: no REJECTED blocks parsed from review_changes.log", file=sys.stderr)
        raise SystemExit(2)

    if args.dry_run:
        run_dry_run(rejected)
        return

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT.parent / ".env", override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not str(api_key).strip():
        print("ERROR: ANTHROPIC_API_KEY is not set (check repo .env).", file=sys.stderr)
        raise SystemExit(3)

    originals = load_original_questions_by_id()
    client = anthropic.Anthropic(api_key=api_key.strip())

    output = build_output_skeleton(len(rejected))
    questions_out: list[dict[str, Any]] = output["areas_of_operation"][0]["tasks"][0]["questions"]

    success = 0
    failed = 0
    total = len(rejected)

    for n, item in enumerate(rejected, start=1):
        print(f"Rewriting {n}/{total}: {item['id']}", flush=True)
        try:
            api_result = call_rewrite_api(client, item)
            questions_out.append(build_question_record(item, api_result, originals))
            success += 1
            if success % CHECKPOINT_EVERY == 0:
                save_output(output, OUTPUT_PATH)
            time.sleep(SUCCESS_SLEEP_SEC)
        except Exception as e:
            failed += 1
            log_error(item["id"], str(e))

    save_output(output, OUTPUT_PATH)
    print(f"Done. {success} rewritten, {failed} failed.")


if __name__ == "__main__":
    main()
