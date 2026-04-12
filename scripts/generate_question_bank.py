#!/usr/bin/env python3
"""Generate oral-exam question banks from ACS + FAA handbook JSON via Anthropic API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    import anthropic
except ImportError as e:
    print("Missing dependency: anthropic. Install with: py -3 -m pip install anthropic python-dotenv", file=sys.stderr)
    raise SystemExit(1) from e

REPO_ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = """
You are an expert helicopter flight instructor and FAA examiner
with 20+ years of experience. You are generating original oral
exam questions for helicopter pilot checkride preparation.

You will be given an ACS (Airman Certification Standards) task
with its knowledge, risk management, and skills requirements,
plus relevant FAA handbook content as source material.

Generate exactly 8 original questions for this ACS task:
  - 3 basic (definition or recall level)
  - 3 intermediate (application or scenario level)
  - 2 advanced (examiner follow-up or edge case level)

Rules:
- Questions must be completely original — do not copy from any
  published oral exam guide
- Answers must be accurate and traceable to FAA source material
- Include regulatory reference (FAR part/section) wherever applicable
- For advanced questions, include a follow_up and follow_up_answer
  that goes one level deeper — this is how real examiners dig in
- Write in plain, direct language as a real examiner would ask
- Focus on helicopter-specific application, not generic aviation
- Never invent regulations or aircraft specifications

CRITICAL REGULATORY UPDATES — use these exact values,
they supersede any conflicting information:

BasicMed (14 CFR Part 68 / 14 CFR 61.113(i)):
- Maximum certificated takeoff weight: 12,500 lbs
  (NOT 6,000 lbs — that was the original limit,
  since updated by the FAA)
- Maximum occupants: 6 (pilot + 5 passengers)
- Maximum altitude: 18,000 ft MSL
- Maximum airspeed: 250 KIAS
- Must remain within United States
- No distance limitation
- No restriction on turbine-powered aircraft
- Prohibited for compensation or hire operations
- Pilot must have held a valid medical at some point
  after July 14, 2006
- Medical education course required every 24 months
- Physical exam from state-licensed physician every
  48 months

Return ONLY valid JSON — no explanation, no markdown, no preamble.

Schema for each question:
{
  "id": "<ACS_CODE.001>",
  "acs_code": "<e.g. PH.I.A.K1>",
  "category": "<knowledge|risk_management|skills>",
  "difficulty": "<basic|intermediate|advanced>",
  "question": "<the question text>",
  "answer": "<complete accurate answer>",
  "follow_up": "<optional — only for advanced questions>",
  "follow_up_answer": "<optional — only for advanced questions>",
  "regulatory_ref": "<FAR section or FAA handbook reference>",
  "tags": ["<topic tag>"],
  "ryan_verified": false,
  "ryan_notes": ""
}

Return a JSON array of exactly 8 question objects.
""".strip()

ACS_FILES: dict[str, str] = {
    "private": "extracted-data/faa/FAA-S-ACS-15_Private_Helicopter_ACS.json",
    "commercial": "extracted-data/faa/FAA-S-ACS-16_Commercial_Helicopter_ACS.json",
    "instrument": "extracted-data/faa/FAA-S-ACS-14_Instrument_Helicopter_ACS.json",
    "cfi": "extracted-data/faa/FAA-S-ACS-29_CFI_Helicopter_ACS.json",
    "atp": "extracted-data/faa/FAA-S-ACS-ATP_Helicopter_ACS.json",
}

RATING_META: dict[str, tuple[str, str, str]] = {
    "private": ("private_helicopter", "PH", "FAA-S-ACS-15"),
    "commercial": ("commercial_helicopter", "CH", "FAA-S-ACS-16"),
    "instrument": ("instrument_helicopter", "IH", "FAA-S-ACS-14"),
    "cfi": ("cfi_helicopter", "FIH", "FAA-S-ACS-29"),
    "atp": ("atp_helicopter", "AH", "FAA-S-ACS-ATP"),
}

HANDBOOK_FILES = [
    "extracted-data/faa/FAA-H-8083-21B_Helicopter_Flying_Handbook.json",
    "extracted-data/faa/FAA-H-8083-1B_Weight_Balance_Handbook.json",
    "extracted-data/faa/FAA-H-8083-15B_Instrument_Flying_Handbook.json",
]

MODEL_ID = "claude-sonnet-4-6"


def int_to_roman(n: int) -> str:
    if n < 1:
        raise ValueError("roman numeral requires positive integer")
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


def roman_to_int(s: str) -> int:
    s = s.strip().upper()
    if not s:
        raise ValueError("empty area designation")
    romans = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for c in reversed(s):
        if c not in romans:
            raise ValueError(f"invalid Roman numeral character: {c!r}")
        v = romans[c]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_handbooks() -> list[tuple[str, dict[str, Any]]]:
    loaded: list[tuple[str, dict[str, Any]]] = []
    for rel in HANDBOOK_FILES:
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        try:
            data = load_json(p)
            if isinstance(data, dict) and "topics" in data:
                loaded.append((rel, data))
        except (OSError, json.JSONDecodeError):
            continue
    return loaded


def handbook_topic_index(
    handbooks: list[tuple[str, dict[str, Any]]],
) -> list[tuple[str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for rel, data in handbooks:
        hb_title = str(data.get("handbook_title", rel))
        for topic in data.get("topics") or []:
            if isinstance(topic, dict):
                rows.append((rel, hb_title, topic))
    return rows


def task_search_blob(task: dict[str, Any]) -> str:
    parts: list[str] = [str(task.get("title", ""))]
    for key in ("knowledge", "risk_management", "skills"):
        for item in task.get(key) or []:
            parts.append(str(item))
    return "\n".join(parts)


def topic_blob(hb_title: str, topic: dict[str, Any]) -> str:
    chunks = [
        str(topic.get("title", "")),
        str(topic.get("summary", "")),
    ]
    for kt in topic.get("key_terms") or []:
        if isinstance(kt, dict):
            chunks.append(str(kt.get("term", "")))
            chunks.append(str(kt.get("definition", "")))
    return f"{hb_title} " + " ".join(chunks)


def select_handbook_topics(
    task_blob: str,
    index: list[tuple[str, str, dict[str, Any]]],
    top_k: int = 6,
) -> list[tuple[str, str, dict[str, Any]]]:
    words = set(re.findall(r"[a-zA-Z]{4,}", task_blob.lower()))
    scored: list[tuple[int, tuple[str, str, dict[str, Any]]]] = []
    for rel, hb_title, topic in index:
        blob = topic_blob(hb_title, topic).lower()
        score = sum(1 for w in words if w in blob)
        scored.append((score, (rel, hb_title, topic)))
    scored.sort(key=lambda x: (-x[0], x[1][1], x[1][2].get("title", "")))
    positive = [t for s, t in scored if s > 0]
    if len(positive) >= top_k:
        return positive[:top_k]
    return [t for _, t in scored[:top_k]]


def format_handbook_excerpts(
    selections: list[tuple[str, str, dict[str, Any]]],
) -> str:
    blocks: list[str] = []
    for rel, hb_title, topic in selections:
        title = topic.get("title", "")
        summary = topic.get("summary", "")
        kp = topic.get("key_points") or []
        kp_txt = ""
        if isinstance(kp, list) and kp:
            kp_txt = "\nKey points: " + "; ".join(str(x) for x in kp[:5])
        blocks.append(
            f"---\nSource: {hb_title} ({rel})\nTopic: {title}\nSummary: {summary}{kp_txt}\n"
        )
    return "\n".join(blocks) if blocks else "(No handbook topics matched — use FAA PTS/ACS and general helicopter knowledge.)"


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


def parse_question_array(raw: str) -> list[dict[str, Any]]:
    cleaned = strip_json_fence(raw)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("response JSON is not an array")
    return [x for x in data if isinstance(x, dict)]


REQUIRED_Q_KEYS = frozenset({"id", "acs_code", "category", "difficulty", "question", "answer"})


def validate_and_normalize_question(q: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    missing = REQUIRED_Q_KEYS - set(q.keys())
    if missing:
        return False, q
    cat = q.get("category")
    diff = q.get("difficulty")
    if cat not in ("knowledge", "risk_management", "skills"):
        return False, q
    if diff not in ("basic", "intermediate", "advanced"):
        return False, q
    out = dict(q)
    out.setdefault("follow_up", "")
    out.setdefault("follow_up_answer", "")
    out.setdefault("regulatory_ref", "")
    out.setdefault("tags", [])
    if not isinstance(out["tags"], list):
        out["tags"] = []
    out.setdefault("ryan_verified", False)
    out.setdefault("ryan_notes", "")
    return True, out


def task_letter(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return f"A{index}"


def build_user_prompt(
    area_title: str,
    area_roman: str,
    task: dict[str, Any],
    task_letter: str,
    task_acs_code: str,
    handbook_excerpts: str,
) -> str:
    k_lines = "\n".join(f"- {x}" for x in (task.get("knowledge") or []))
    r_lines = "\n".join(f"- {x}" for x in (task.get("risk_management") or []))
    s_lines = "\n".join(f"- {x}" for x in (task.get("skills") or []))
    return f"""Area of Operation: {area_title} (Area {area_roman})
Task title: {task.get("title", "")}
Task ACS code (use as prefix for question acs_code values): {task_acs_code}

Knowledge:
{k_lines}

Risk management:
{r_lines}

Skills:
{s_lines}

Relevant FAA handbook excerpts (summaries for context):
{handbook_excerpts}
"""


def load_existing_lookup(path: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for area in data.get("areas_of_operation") or []:
        aid = str(area.get("id", ""))
        for task in area.get("tasks") or []:
            tid = str(task.get("id", ""))
            qs = task.get("questions") or []
            if isinstance(qs, list):
                out[(aid, tid)] = [x for x in qs if isinstance(x, dict)]
    return out


def count_questions(lookup: dict[tuple[str, str], list[dict[str, Any]]]) -> int:
    return sum(len(v) for v in lookup.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate helicopter oral exam question bank from ACS + handbooks.")
    parser.add_argument(
        "--rating",
        required=True,
        choices=["private", "commercial", "instrument", "cfi", "atp"],
        help="Certificate / rating ACS set",
    )
    parser.add_argument(
        "--area",
        default=None,
        help='Optional Area of Operation Roman numeral (e.g. "I", "II"). Omit to process all areas.',
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        print("ERROR: ANTHROPIC_API_KEY is missing or empty. Set it in repo .env", file=sys.stderr)
        raise SystemExit(2)

    rating = args.rating
    if rating not in RATING_META:
        print(f"ERROR: unknown rating {rating!r}", file=sys.stderr)
        raise SystemExit(2)

    rating_label, prefix, acs_ref = RATING_META[rating]
    acs_rel = ACS_FILES[rating]
    acs_path = REPO_ROOT / acs_rel
    if not acs_path.is_file():
        print(
            f"ERROR: ACS JSON not found for rating {rating!r}: {acs_path}\n"
            "Extract or add the file before running.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    acs_data = load_json(acs_path)
    areas_raw = acs_data.get("areas_of_operation") or []
    if not isinstance(areas_raw, list):
        print("ERROR: ACS JSON has no areas_of_operation array", file=sys.stderr)
        raise SystemExit(3)

    area_filter: int | None = None
    if args.area is not None:
        try:
            area_filter = roman_to_int(args.area)
        except ValueError as e:
            print(f"ERROR: invalid --area {args.area!r}: {e}", file=sys.stderr)
            raise SystemExit(2)

    handbooks = load_handbooks()
    hb_index = handbook_topic_index(handbooks)

    output_path = REPO_ROOT / "question-bank" / f"qbank_{rating}_helicopter.json"
    existing_lookup = load_existing_lookup(output_path)

    client = anthropic.Anthropic(api_key=api_key)

    areas_processed = 0
    tasks_processed = 0
    questions_generated = 0
    failed_tasks: list[str] = []
    new_lookup = dict(existing_lookup)

    for ai, area in enumerate(areas_raw):
        if not isinstance(area, dict):
            continue
        area_idx_1 = ai + 1
        area_roman = int_to_roman(area_idx_1)
        if area_filter is not None and area_idx_1 != area_filter:
            continue

        areas_processed += 1
        area_title = str(area.get("title", ""))
        tasks = area.get("tasks") or []

        for ti, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            tletter = task_letter(ti)
            task_acs_code = f"{prefix}.{area_roman}.{tletter}"
            key = (area_roman, tletter)
            prior = new_lookup.get(key, [])
            if len(prior) > 0:
                continue

            tasks_processed += 1
            blob = task_search_blob(task)
            picks = select_handbook_topics(blob, hb_index)
            excerpts = format_handbook_excerpts(picks)
            user_msg = build_user_prompt(
                area_title,
                area_roman,
                task,
                tletter,
                task_acs_code,
                excerpts,
            )

            try:
                msg = client.messages.create(
                    model=MODEL_ID,
                    max_tokens=16384,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                )
            except Exception as e:
                failed_tasks.append(f"{area_title} / {task.get('title', '')}: API error: {e}")
                new_lookup[key] = []
                continue

            block = msg.content[0]
            raw_text = block.text if hasattr(block, "text") else str(block)
            try:
                raw_questions = parse_question_array(raw_text)
            except (json.JSONDecodeError, ValueError) as e:
                failed_tasks.append(f"{area_title} / {task.get('title', '')}: invalid JSON: {e}")
                new_lookup[key] = []
                continue

            good: list[dict[str, Any]] = []
            for rq in raw_questions:
                ok, normalized = validate_and_normalize_question(rq)
                if ok:
                    good.append(normalized)
            if not good:
                failed_tasks.append(
                    f"{area_title} / {task.get('title', '')}: no valid questions after validation"
                )
            new_lookup[key] = good
            questions_generated += len(good)

    # Build output structure from ACS + merged questions
    areas_out: list[dict[str, Any]] = []
    total_q = 0
    verified = 0

    for ai, area in enumerate(areas_raw):
        if not isinstance(area, dict):
            continue
        area_idx_1 = ai + 1
        area_roman = int_to_roman(area_idx_1)

        area_title = str(area.get("title", ""))
        tasks_out: list[dict[str, Any]] = []
        tasks = area.get("tasks") or []

        for ti, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue
            tletter = task_letter(ti)
            task_acs_code = f"{prefix}.{area_roman}.{tletter}"
            key = (area_roman, tletter)
            qs = new_lookup.get(key, [])
            for q in qs:
                total_q += 1
                if q.get("ryan_verified"):
                    verified += 1
            tasks_out.append(
                {
                    "id": tletter,
                    "title": str(task.get("title", "")),
                    "acs_code": task_acs_code,
                    "questions": qs,
                }
            )

        areas_out.append(
            {
                "id": area_roman,
                "title": area_title,
                "tasks": tasks_out,
            }
        )

    out_doc = {
        "rating": rating_label,
        "acs_reference": acs_ref,
        "generated_date": date.today().isoformat(),
        "generation_model": MODEL_ID,
        "total_questions": total_q,
        "ryan_verified_count": verified,
        "areas_of_operation": areas_out,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        f"Rating: {rating}\n"
        f"Areas processed: {areas_processed}\n"
        f"Tasks processed: {tasks_processed}\n"
        f"Questions generated: {questions_generated}\n"
        f"Output: {output_path}"
    )
    if failed_tasks:
        print("\nTasks with errors:", file=sys.stderr)
        for ft in failed_tasks:
            print(f"  - {ft}", file=sys.stderr)


if __name__ == "__main__":
    main()
