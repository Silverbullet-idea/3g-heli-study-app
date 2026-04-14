#!/usr/bin/env python3
"""Batch-verify oral-exam question bank entries via Anthropic API (claude-sonnet-4-6)."""

from __future__ import annotations

import argparse
import json
import os
import sys
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

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = "claude-sonnet-4-6"
BATCH_SIZE = 10

SYSTEM_PROMPT = """
You are an FAA helicopter knowledge examiner and regulatory expert. You will be given a batch of questions and answers from a Private Pilot helicopter oral exam question bank.

For each question, evaluate:
1. Is the answer factually correct based on FAA handbooks and current regulations?
2. Are all regulatory references accurate and current?
3. Is the difficulty level appropriate for the stated level (basic/intermediate/advanced)?

CRITICAL REGULATORY UPDATES — these are known corrections, flag any question that contradicts them:
- BasicMed max gross weight is 12,500 lbs (NOT 6,000 lbs)
- BasicMed has no distance limitation and no turbine aircraft restriction
- ADS-B Out has been required since January 1, 2020

Return ONLY a valid JSON object with this exact structure, no preamble:
{
  "results": [
    {
      "id": "<question id>",
      "status": "PASS" | "FLAG" | "FAIL",
      "confidence": <0.0-1.0>,
      "issues": ["<issue description>"] or [],
      "suggested_correction": "<correction text>" or ""
    }
  ]
}

PASS = factually correct, references accurate, no issues.
FLAG = minor issue, outdated reference, or low confidence — needs human review.
FAIL = factually incorrect answer that could harm a student or create a safety issue.
""".strip()

FLAG_API_ISSUE = "Verifier API call failed — manual review required"
FLAG_MISSING_ID = "Verifier returned no result for this question id"


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
    cleaned = strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(cleaned[start : end + 1])
        else:
            raise
    if not isinstance(data, dict):
        raise ValueError("response JSON is not an object")
    return data


def collect_flat_questions(data: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return (question, task) pairs in traversal order."""
    out: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if isinstance(q, dict) and q.get("id"):
                    out.append((q, task))
    return out


def question_payload(q: dict[str, Any]) -> dict[str, Any]:
    """Fields sent to the verifier."""
    out: dict[str, Any] = {
        "id": q.get("id"),
        "acs_code": q.get("acs_code"),
        "category": q.get("category"),
        "difficulty": q.get("difficulty"),
        "question": q.get("question"),
        "answer": q.get("answer"),
        "regulatory_ref": q.get("regulatory_ref"),
    }
    if q.get("follow_up") not in (None, ""):
        out["follow_up"] = q.get("follow_up")
    if q.get("follow_up_answer") not in (None, ""):
        out["follow_up_answer"] = q.get("follow_up_answer")
    if isinstance(q.get("tags"), list):
        out["tags"] = q.get("tags")
    return out


def parse_confidence(raw: dict[str, Any]) -> float:
    conf = raw.get("confidence", 0.0)
    try:
        c = float(conf)
    except (TypeError, ValueError):
        c = 0.0
    return max(0.0, min(1.0, c))


def normalize_issues_and_suggestion(raw: dict[str, Any]) -> tuple[list[str], str]:
    issues_raw = raw.get("issues", [])
    if issues_raw is None:
        issues = []
    elif isinstance(issues_raw, str):
        issues = [issues_raw] if issues_raw.strip() else []
    elif isinstance(issues_raw, list):
        issues = [str(x) for x in issues_raw if str(x).strip()]
    else:
        issues = [str(issues_raw)]
    sugg = raw.get("suggested_correction", "")
    suggested = "" if sugg is None else str(sugg)
    return issues, suggested


def build_result_map(parsed: dict[str, Any]) -> dict[str, tuple[str, float, list[str], str]]:
    """Map question id -> (status, confidence, issues, suggested_correction)."""
    out: dict[str, tuple[str, float, list[str], str]] = {}
    for item in parsed.get("results") or []:
        if not isinstance(item, dict):
            continue
        qid = item.get("id")
        if not qid or not isinstance(qid, str):
            continue
        status = str(item.get("status", "")).strip().upper()
        if status not in ("PASS", "FLAG", "FAIL"):
            continue
        conf = parse_confidence(item)
        issues, suggested = normalize_issues_and_suggestion(item)
        out[qid.strip()] = (status, conf, issues, suggested)
    return out


def recompute_total_questions(data: dict[str, Any]) -> int:
    n = 0
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            qs = task.get("questions") or []
            if isinstance(qs, list):
                n += len(qs)
    return n


def remove_question_from_task(task: dict[str, Any], qid: str) -> bool:
    qs = task.get("questions")
    if not isinstance(qs, list):
        return False
    new_qs = [q for q in qs if not (isinstance(q, dict) and q.get("id") == qid)]
    if len(new_qs) == len(qs):
        return False
    task["questions"] = new_qs
    return True


def append_fail_log(path: Path, qid: str, reason: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe = reason.replace("\n", " ").replace("\r", "")
    line = f"{ts}\t{qid}\t{safe}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def write_summary(path: Path, stats: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"verification_run_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"total_processed: {stats['total_processed']}",
        f"pass: {stats['pass']}",
        f"flag: {stats['flag']}",
        f"fail_removed: {stats['fail']}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify question bank entries in batches via Anthropic API.")
    parser.add_argument(
        "--input",
        default="question-bank/qbank_private_helicopter.json",
        help="Path to question bank JSON (relative to repo root unless absolute)",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not str(api_key).strip():
        print("ERROR: ANTHROPIC_API_KEY is not set (check repo .env).", file=sys.stderr)
        raise SystemExit(2)

    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = REPO_ROOT / in_path
    if not in_path.is_file():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        raise SystemExit(3)

    with in_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    flat = collect_flat_questions(data)
    client = anthropic.Anthropic(api_key=api_key.strip())

    stats = {"total_processed": 0, "pass": 0, "flag": 0, "fail": 0}
    fails_log = REPO_ROOT / "question-bank" / "verification_fails.log"
    summary_path = REPO_ROOT / "question-bank" / "verification_summary.txt"

    for i in range(0, len(flat), BATCH_SIZE):
        chunk = flat[i : i + BATCH_SIZE]
        payload = {"questions": [question_payload(q) for q, _ in chunk]}
        user_msg = json.dumps(payload, ensure_ascii=False)

        parse_ok = False
        result_by_id: dict[str, tuple[str, float, list[str], str]] = {}

        try:
            msg = client.messages.create(
                model=MODEL_ID,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            block = msg.content[0]
            raw_text = block.text if hasattr(block, "text") else str(block)
            parsed = extract_json_object(raw_text)
            if isinstance(parsed.get("results"), list):
                result_by_id = build_result_map(parsed)
                parse_ok = True
        except Exception:
            parse_ok = False
            result_by_id = {}

        for q, task in chunk:
            stats["total_processed"] += 1
            qid = str(q["id"])

            if not parse_ok:
                q["verification"] = {
                    "status": "FLAG",
                    "confidence": 0.0,
                    "issues": [FLAG_API_ISSUE],
                    "suggested_correction": "",
                }
                stats["flag"] += 1
                continue

            if qid not in result_by_id:
                q["verification"] = {
                    "status": "FLAG",
                    "confidence": 0.0,
                    "issues": [FLAG_MISSING_ID],
                    "suggested_correction": "",
                }
                stats["flag"] += 1
                continue

            status, confidence, issues, suggested = result_by_id[qid]

            if status == "PASS":
                q["verification"] = {
                    "status": "PASS",
                    "confidence": confidence,
                    "issues": [],
                    "suggested_correction": "",
                }
                stats["pass"] += 1
            elif status == "FLAG":
                q["verification"] = {
                    "status": "FLAG",
                    "confidence": confidence,
                    "issues": issues,
                    "suggested_correction": suggested,
                }
                stats["flag"] += 1
            else:
                reason_parts = list(issues)
                if suggested:
                    reason_parts.append(suggested)
                reason = "; ".join(reason_parts) if reason_parts else "FAIL (no details from verifier)"
                append_fail_log(fails_log, qid, reason)
                remove_question_from_task(task, qid)
                stats["fail"] += 1

    data["total_questions"] = recompute_total_questions(data)

    write_summary(summary_path, stats)

    with in_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"Done. processed={stats['total_processed']} PASS={stats['pass']} "
        f"FLAG={stats['flag']} FAIL_removed={stats['fail']}"
    )
    print(f"Updated: {in_path}")
    print(f"Summary: {summary_path}")
    if stats["fail"]:
        print(f"Failures log: {fails_log}")


if __name__ == "__main__":
    main()
