#!/usr/bin/env python3
"""Pre-triage FLAG questions via Anthropic API — APPROVE / EDIT / ESCALATE."""

from __future__ import annotations

import argparse
import json
import os
import signal
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

REPO_ROOT = Path(__file__).resolve().parent.parent
BATCH_SIZE = 3
API_MAX_ATTEMPTS = 4
RETRY_SLEEP_SEC = 5
SUCCESS_SLEEP_SEC = 2
SAVE_EVERY_N_BATCHES = 10

SYSTEM_PROMPT = """
You are an expert helicopter Certified Flight Instructor (CFI) and Designated Pilot Examiner (DPE) with deep knowledge of FAA ACS standards, 14 CFR, and FAA helicopter handbooks.

You will receive a batch of questions from a helicopter oral exam question bank. Each item was previously marked FLAG by an automated verifier — meaning it needs a second look, not necessarily that it is wrong.

For each question, choose exactly one triage outcome:

- APPROVE — The question text and the stated correct answer are factually sound and clear enough to ship as-is. The original verifier was overly cautious.
- EDIT — The intent and answer are directionally correct, but the question text and/or answer wording should be tightened for clarity, precision, or regulatory accuracy. Provide corrected text only where it needs fixing.
- ESCALATE — The item is genuinely ambiguous, may be wrong, contradicts reliable sources, or requires human domain judgment. Do not guess on anything aviation-safety-critical.

Rules:
- Prefer ESCALATE over guessing when safety, regulatory limits, or aircraft-specific facts are uncertain.
- BasicMed (14 CFR Part 68 / 61.113(i)): max certificated takeoff weight 12,500 lb; no distance limit; no turbine restriction (common generation errors used wrong legacy numbers).
- ADS-B Out has been required since January 1, 2020 (for applicable airspace/aircraft per 14 CFR).

Return ONLY a JSON array (no markdown fences, no commentary), one object per question, in this shape:
[
  {
    "id": "<question id>",
    "triage": "APPROVE" | "EDIT" | "ESCALATE",
    "confidence": "high" | "medium" | "low",
    "reason": "<one sentence>",
    "corrected_question": "<only if triage is EDIT and the question needs fixing>",
    "corrected_answer": "<only if triage is EDIT and the answer needs fixing>"
  }
]
""".strip()

CHANGE_LOG_PATH = REPO_ROOT / "question-bank" / "review_changes.log"
TRIAGE_ERRORS_LOG = REPO_ROOT / "question-bank" / "triage_errors.log"
SUMMARY_PATH = REPO_ROOT / "question-bank" / "triage_summary.txt"


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


def extract_json_array(raw: str) -> list[Any]:
    cleaned = strip_json_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            data = json.loads(cleaned[start : end + 1])
        else:
            raise
    if not isinstance(data, list):
        raise ValueError("response JSON is not an array")
    return data


def confidence_to_float(label: str) -> float:
    m = (label or "").strip().lower()
    if m == "high":
        return 0.9
    if m == "medium":
        return 0.75
    if m == "low":
        return 0.55
    return 0.7


def collect_flat_questions(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if isinstance(q, dict) and q.get("id"):
                    out.append(q)
    return out


def question_payload(q: dict[str, Any]) -> dict[str, Any]:
    """Fields sent to the triage model (FLAG context)."""
    out: dict[str, Any] = {
        "id": q.get("id"),
        "acs_code": q.get("acs_code"),
        "category": q.get("category"),
        "difficulty": q.get("difficulty"),
        "question": q.get("question"),
        "answer": q.get("answer"),
        "regulatory_ref": q.get("regulatory_ref"),
    }
    v = q.get("verification")
    if isinstance(v, dict):
        out["verifier_status"] = v.get("status")
        out["verifier_confidence"] = v.get("confidence")
        out["verifier_issues"] = v.get("issues")
        out["verifier_suggested_correction"] = v.get("suggested_correction")
    if q.get("follow_up") not in (None, ""):
        out["follow_up"] = q.get("follow_up")
    if q.get("follow_up_answer") not in (None, ""):
        out["follow_up_answer"] = q.get("follow_up_answer")
    if isinstance(q.get("tags"), list):
        out["tags"] = q.get("tags")
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


def append_review_changes_line(line: str) -> None:
    CHANGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHANGE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
        if not line.endswith("\n"):
            f.write("\n")


def append_triage_error_log(batch_index: int, raw_response: str) -> None:
    TRIAGE_ERRORS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe = raw_response.replace("\r", " ")
    block = f"{ts}\tbatch={batch_index}\n{safe}\n---\n"
    with TRIAGE_ERRORS_LOG.open("a", encoding="utf-8") as f:
        f.write(block)


def call_triage_api(client: anthropic.Anthropic, user_msg: str) -> tuple[bool, str]:
    for attempt in range(API_MAX_ATTEMPTS):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8192,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_msg}],
            )
            block = msg.content[0]
            raw_text = block.text if hasattr(block, "text") else str(block)
            _preview = raw_text[:500]
            print(
                "[TRIAGE RAW RESPONSE] "
                + _preview.encode("ascii", "backslashreplace").decode("ascii"),
                flush=True,
            )
            time.sleep(SUCCESS_SLEEP_SEC)
            return True, raw_text
        except BaseException as e:
            print(f"[TRIAGE ERROR] attempt {attempt + 1}: {e!r}", flush=True)
        if attempt < API_MAX_ATTEMPTS - 1:
            time.sleep(RETRY_SLEEP_SEC)
    return False, ""


def build_result_map(parsed_list: list[Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in parsed_list:
        if not isinstance(item, dict):
            continue
        qid = item.get("id")
        if not qid or not isinstance(qid, str):
            continue
        triage = str(item.get("triage", "")).strip().upper()
        if triage not in ("APPROVE", "EDIT", "ESCALATE"):
            continue
        out[qid.strip()] = {
            "triage": triage,
            "confidence": str(item.get("confidence", "medium")),
            "reason": str(item.get("reason", "")).strip(),
            "corrected_question": item.get("corrected_question"),
            "corrected_answer": item.get("corrected_answer"),
        }
    return out


def apply_triage_to_question(
    q: dict[str, Any],
    info: dict[str, Any],
    stats: dict[str, int],
) -> None:
    triage = info["triage"]
    conf_f = confidence_to_float(info["confidence"])
    reason = info["reason"] or "(no reason given)"
    qid = str(q.get("id") or "")
    orig_answer = str(q.get("answer") or "")

    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    v = dict(v)

    if triage == "APPROVE":
        v["status"] = "PASS"
        v["confidence"] = conf_f
        v["issues"] = []
        v["suggested_correction"] = ""
        v["triage"] = "AUTO_APPROVE"
        v.pop("triage_note", None)
        q["verification"] = v
        stats["approve"] += 1
        append_review_changes_line(f"AUTO_APPROVE\t{qid}\t{reason}")
        return

    if triage == "EDIT":
        cq = info.get("corrected_question")
        ca = info.get("corrected_answer")
        changed_parts: list[str] = []
        if cq is not None and str(cq).strip():
            q["question"] = str(cq).strip()
            changed_parts.append("question")
        answer_updated = False
        if ca is not None and str(ca).strip():
            q["answer"] = str(ca).strip()
            changed_parts.append("answer")
            answer_updated = True
        new_answer = str(q.get("answer") or "")
        note = (
            "Applied AI edits: " + ", ".join(changed_parts)
            if changed_parts
            else "AI_EDIT (no text fields returned — check model output)"
        )
        v["status"] = "PASS"
        v["confidence"] = conf_f
        v["issues"] = []
        v["suggested_correction"] = ""
        v["triage"] = "AI_EDIT"
        v["triage_note"] = note
        q["verification"] = v
        stats["edit"] += 1
        if answer_updated:
            corrected_display = new_answer
        else:
            corrected_display = "question text changed"
        append_review_changes_line(
            f"AI_EDIT\t{qid}\t{orig_answer}\t->\t{corrected_display}"
        )
        return

    # ESCALATE
    v["status"] = "FLAG"
    v["confidence"] = conf_f
    v["triage"] = "ESCALATE"
    v["triage_note"] = reason
    q["verification"] = v
    stats["escalate"] += 1
    append_review_changes_line(f"ESCALATE\t{qid}\t{reason}")


def write_summary(
    path: Path,
    run_ts: str,
    stats: dict[str, int],
    initial_flag_pending: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    processed = stats["approve"] + stats["edit"] + stats["escalate"]
    resolved = stats["approve"] + stats["edit"]
    pct = (100.0 * resolved / initial_flag_pending) if initial_flag_pending else 0.0
    lines = [
        f"run_timestamp_utc: {run_ts}",
        f"total_flags_processed_this_run: {processed}",
        f"approve: {stats['approve']}",
        f"edit: {stats['edit']}",
        f"escalate_remaining_human_queue: {stats['escalate']}",
        f"estimated_manual_review_reduction_percent: {pct:.1f}",
        "",
        f"(Reduction = (approve + edit) / initial_pending_flags_at_run_start = {resolved} / {initial_flag_pending})",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-triage FLAG questions via Anthropic API.")
    parser.add_argument("--input", required=True, help="Path to question bank JSON")
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N batches (default: all).",
    )
    args = parser.parse_args()

    if not load_dotenv(REPO_ROOT / ".env"):
        load_dotenv(REPO_ROOT.parent / ".env")
    else:
        load_dotenv(REPO_ROOT.parent / ".env", override=True)
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
    pending: list[dict[str, Any]] = []
    for q in flat:
        v = q.get("verification")
        if not isinstance(v, dict):
            continue
        if v.get("status") != "FLAG":
            continue
        if v.get("triage"):
            continue
        pending.append(q)

    initial_flag_pending = len(pending)
    chunks = [pending[i : i + BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    if args.batch_limit is not None:
        chunks = chunks[: max(0, args.batch_limit)]
    total_batches = len(chunks)

    stats = {"approve": 0, "edit": 0, "escalate": 0}
    interrupted = False

    def save_json() -> None:
        data["total_questions"] = recompute_total_questions(data)
        with in_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    def on_sigint(_sig: int, _frame: Any) -> None:
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGINT, on_sigint)

    client = anthropic.Anthropic(api_key=api_key.strip())

    try:
        for batch_num, chunk in enumerate(chunks, start=1):
            if interrupted:
                break
            payload = {"questions": [question_payload(q) for q in chunk]}
            user_msg = json.dumps(payload, ensure_ascii=False)

            ok, raw_text = call_triage_api(client, user_msg)
            if not ok:
                append_triage_error_log(batch_num, raw_text or "(empty after failures)")
                continue

            try:
                arr = extract_json_array(raw_text)
            except (json.JSONDecodeError, ValueError) as e:
                append_triage_error_log(batch_num, f"{raw_text}\n(parse error: {e})")
                continue

            result_by_id = build_result_map(arr)
            for q in chunk:
                qid = str(q.get("id") or "").strip()
                if qid in result_by_id:
                    apply_triage_to_question(q, result_by_id[qid], stats)

            if batch_num % SAVE_EVERY_N_BATCHES == 0 or batch_num == total_batches:
                save_json()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        save_json()
        run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        write_summary(SUMMARY_PATH, run_ts, stats, initial_flag_pending)

    print(
        f"Done. batches={total_batches} APPROVE={stats['approve']} EDIT={stats['edit']} "
        f"ESCALATE={stats['escalate']} | summary: {SUMMARY_PATH}",
        flush=True,
    )
    print(f"Updated: {in_path}", flush=True)


if __name__ == "__main__":
    main()
