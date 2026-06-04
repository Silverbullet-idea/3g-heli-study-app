#!/usr/bin/env python3
"""Re-attempt API rewrites for question IDs that failed in rewrite_rejected_questions.py."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
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

from rewrite_rejected_questions import (
    ERRORS_LOG_PATH,
    MODEL_ID,
    OUTPUT_PATH,
    REVIEW_LOG_PATH,
    SYSTEM_PROMPT_BLOCKS,
    build_question_record,
    build_user_message,
    load_original_questions_by_id,
    parse_rejected_blocks,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
API_MAX_ATTEMPTS = 5
RETRY_SLEEP_SEC = 3
SUCCESS_SLEEP_SEC = 1


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


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object from API text, including preamble + markdown fences."""
    text = raw.strip()
    if "```" in text and not text.startswith("```"):
        text = text[text.find("```") :]
    cleaned = strip_json_fence(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        obj_start = cleaned.find("{")
        obj_end = cleaned.rfind("}")
        if obj_start >= 0 and obj_end > obj_start:
            data = json.loads(cleaned[obj_start : obj_end + 1])
        else:
            arr_start = cleaned.find("[")
            arr_end = cleaned.rfind("]")
            if arr_start >= 0 and arr_end > arr_start:
                data = json.loads(cleaned[arr_start : arr_end + 1])
            else:
                raise
    if not isinstance(data, dict):
        raise ValueError("response JSON is not an object")
    return data


def parse_failed_ids(log_path: Path) -> list[str]:
    if not log_path.is_file():
        return []
    ids: list[str] = []
    seen: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("RETRY_"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        question_id = parts[1].strip()
        if question_id and question_id not in seen:
            seen.add(question_id)
            ids.append(question_id)
    return ids


def load_existing_questions(path: Path) -> tuple[dict[str, Any], set[tuple[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Output bank not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    existing_keys: set[tuple[str, str]] = set()
    for q in data["areas_of_operation"][0]["tasks"][0]["questions"]:
        existing_keys.add((str(q["id"]), str(q.get("question", ""))))
    return data, existing_keys


def log_error(question_id: str, message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ERRORS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ERRORS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp}\t{question_id}\t{message}\n")


def log_retry_raw(question_id: str, raw_text: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    compact = raw_text.replace("\n", "\\n")
    ERRORS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ERRORS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp}\t{question_id}\tRETRY_RAW:{compact}\n")


def call_rewrite_api(client: anthropic.Anthropic, item: dict[str, str]) -> dict[str, Any] | None:
    last_error: Exception | None = None
    last_raw: str = ""
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
            last_raw = raw_text
            payload = extract_json_object(raw_text)
            for key in ("id", "question", "answer", "rewrite_note"):
                if key not in payload or not str(payload[key]).strip():
                    raise ValueError(f"API response missing required field: {key}")
            return payload
        except json.JSONDecodeError as e:
            last_error = e
            log_retry_raw(item["id"], last_raw or str(e))
            if attempt < API_MAX_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SEC)
        except Exception as e:
            last_error = e
            if attempt < API_MAX_ATTEMPTS:
                time.sleep(RETRY_SLEEP_SEC)
    if last_error:
        log_error(item["id"], str(last_error))
    return None


def save_output(data: dict[str, Any], path: Path) -> None:
    data["total_questions"] = len(data["areas_of_operation"][0]["tasks"][0]["questions"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> None:
    failed_ids = parse_failed_ids(ERRORS_LOG_PATH)
    if not failed_ids:
        print("No failed question IDs found in rewrite_errors.log", file=sys.stderr)
        raise SystemExit(1)

    print(f"Retrying {len(failed_ids)} failed IDs: {', '.join(failed_ids)}")

    if not REVIEW_LOG_PATH.is_file():
        print(f"ERROR: review log not found: {REVIEW_LOG_PATH}", file=sys.stderr)
        raise SystemExit(2)

    log_text = REVIEW_LOG_PATH.read_text(encoding="utf-8")
    all_rejected = parse_rejected_blocks(log_text)
    rejected_by_id: dict[str, list[dict[str, str]]] = {}
    for item in all_rejected:
        rejected_by_id.setdefault(item["id"], []).append(item)

    output, existing_keys = load_existing_questions(OUTPUT_PATH)
    questions_out: list[dict[str, Any]] = output["areas_of_operation"][0]["tasks"][0]["questions"]

    to_retry: list[dict[str, str]] = []
    for qid in failed_ids:
        blocks = rejected_by_id.get(qid, [])
        if not blocks:
            print(f"WARNING: no REJECTED block found for {qid}", file=sys.stderr)
            continue
        for block in blocks:
            key = (block["id"], block["question"])
            if key not in existing_keys:
                to_retry.append(block)

    if not to_retry:
        print("All failed IDs already present in qbank_rewritten_rejects.json")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with ERRORS_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"RETRY_COMPLETE\t{timestamp}\trecovered=0\tstill_failed=0\n")
        return

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT.parent / ".env", override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not str(api_key).strip():
        print("ERROR: ANTHROPIC_API_KEY is not set (check repo .env).", file=sys.stderr)
        raise SystemExit(3)

    originals = load_original_questions_by_id()
    client = anthropic.Anthropic(api_key=api_key.strip())

    recovered: list[str] = []
    still_failed: list[str] = []

    for n, item in enumerate(to_retry, start=1):
        print(f"Retrying {n}/{len(to_retry)}: {item['id']}", flush=True)
        api_result = call_rewrite_api(client, item)
        if api_result is None:
            still_failed.append(item["id"])
            continue
        record = build_question_record(item, api_result, originals)
        questions_out.append(record)
        existing_keys.add((item["id"], item["question"]))
        recovered.append(item["id"])
        q_preview = str(record["question"])[:80].replace("\n", " ")
        print(f"  Recovered {item['id']}: {q_preview}", flush=True)
        time.sleep(SUCCESS_SLEEP_SEC)

    save_output(output, OUTPUT_PATH)
    actual_count = len(questions_out)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with ERRORS_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(
            f"RETRY_COMPLETE\t{timestamp}\trecovered={len(recovered)}\tstill_failed={len(still_failed)}\n"
        )

    print(f"Recovered: {recovered if recovered else '(none)'}")
    print(f"Still failed: {still_failed if still_failed else '(none)'}")
    print(f"total_questions field: {output['total_questions']}  actual count: {actual_count}")
    if output["total_questions"] != actual_count:
        print("WARNING: total_questions does not match actual question count", file=sys.stderr)


if __name__ == "__main__":
    main()
