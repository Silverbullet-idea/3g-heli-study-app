#!/usr/bin/env python3
"""Generate checkride study sheet content specs from extracted aircraft POH JSON."""

from __future__ import annotations

import argparse
import json
import os
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

MODEL_ID = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

REQUIRED_SECTION_IDS = (
    "limitations",
    "instrument_markings",
    "emergency_procedures",
    "systems",
)

AIRCRAFT_REGISTRY: dict[str, str] = {
    "r22": "Robinson R22 Beta II",
    "r44": "Robinson R44 Raven II",
    "r66": "Robinson R66",
    "b505": "Bell 505 Jet Ranger X",
    "b206": "Bell 206B3 JetRanger",
    "b407": "Bell 407",
    "sw269c1": "Schweizer 269C-1 (S300CB/CBi)",
    "sw269c": "Schweizer 269C (S300C)",
}

SYSTEM_PROMPT_BLOCKS: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": """You are an expert helicopter flight instructor and FAA examiner. Your task is to extract and organize the specific values, limits, and procedures that a student pilot must memorize for a checkride oral exam.

You will receive raw extracted data from a helicopter POH (limitations, emergency procedures, and systems sections). Your output must be a JSON object matching the provided schema exactly — no markdown, no explanation, only the JSON object.

Rules:
- Include ONLY values that a student would need to recite from memory during an oral exam
- Use exact numeric values from the POH — never approximate
- Keep labels concise (under 8 words)
- Keep values concise — include units always
- For emergency procedures: condense to the critical action sequence only (3–6 steps max per procedure)
- Include the 5–8 most important emergency procedures only
- Flag any value that appears to be a chart/table (not extractable as a single value) with "See POH Figure X"
- Do not invent values. If a value is not in the source data, omit it.

Output schema (exact keys):
{
  "aircraft_id": "<slug>",
  "aircraft_name": "<display name>",
  "rating": "private",
  "generated_date": "YYYY-MM-DD",
  "sections": [
    {
      "section_id": "limitations",
      "section_title": "Limitations & V-Speeds",
      "items": [{"label": "...", "value": "...", "note": "..."}]
    },
    {
      "section_id": "instrument_markings",
      "section_title": "Instrument Markings",
      "items": [{"label": "...", "value": "..."}]
    },
    {
      "section_id": "emergency_procedures",
      "section_title": "Emergency Procedures (Condensed)",
      "items": [{"label": "...", "value": "..."}]
    },
    {
      "section_id": "systems",
      "section_title": "Key Systems Values",
      "items": [{"label": "...", "value": "..."}]
    }
  ]
}

Each section must have section_id, section_title, and items array. Items require label and value; note is optional.""".strip(),
        "cache_control": {"type": "ephemeral"},
    }
]


def load_env() -> None:
    if not load_dotenv(REPO_ROOT / ".env"):
        load_dotenv(REPO_ROOT.parent / ".env")
    else:
        load_dotenv(REPO_ROOT.parent / ".env", override=True)


def resolve_aircraft_data_dir() -> Path:
    for rel in ("data/aircraft", "extracted-data/aircraft"):
        candidate = REPO_ROOT / rel
        if candidate.is_dir() and any(candidate.glob("*_limitations.json")):
            return candidate
    return REPO_ROOT / "data" / "aircraft"


def output_dir() -> Path:
    return REPO_ROOT / "data" / "study_sheet_specs"


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    start = text.find("{")
    if start > 0:
        text = text[start:]
    return text.strip()


def load_aircraft_json(data_dir: Path, aircraft_id: str, suffix: str) -> dict[str, Any] | None:
    path = data_dir / f"{aircraft_id}_{suffix}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def source_files_present(data_dir: Path, aircraft_id: str) -> bool:
    for suffix in ("limitations", "emergency_procedures", "systems"):
        if not (data_dir / f"{aircraft_id}_{suffix}.json").is_file():
            print(
                f"WARNING: Skipping {aircraft_id} — missing {aircraft_id}_{suffix}.json",
                file=sys.stderr,
            )
            return False
    return True


def build_user_prompt(
    aircraft_id: str,
    aircraft_name: str,
    limitations: dict[str, Any],
    emergency: dict[str, Any],
    systems: dict[str, Any],
) -> str:
    return (
        f"Aircraft: {aircraft_name}\n"
        f"Aircraft ID: {aircraft_id}\n\n"
        f"LIMITATIONS DATA:\n{json.dumps(limitations, ensure_ascii=False)}\n\n"
        f"EMERGENCY PROCEDURES DATA:\n{json.dumps(emergency, ensure_ascii=False)}\n\n"
        f"SYSTEMS DATA:\n{json.dumps(systems, ensure_ascii=False)}\n\n"
        "Generate the study sheet spec JSON for this aircraft. "
        "Output only the JSON object, no markdown fences."
    )


def validate_spec(spec: dict[str, Any], aircraft_id: str) -> None:
    if spec.get("aircraft_id") != aircraft_id:
        spec["aircraft_id"] = aircraft_id
    if not spec.get("rating"):
        spec["rating"] = "private"
    if not spec.get("generated_date"):
        spec["generated_date"] = date.today().isoformat()
    sections = spec.get("sections")
    if not isinstance(sections, list):
        raise ValueError("sections must be an array")
    section_ids = [s.get("section_id") for s in sections if isinstance(s, dict)]
    for required in REQUIRED_SECTION_IDS:
        if required not in section_ids:
            raise ValueError(f"missing required section_id: {required}")
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("each section must be an object")
        items = section.get("items")
        if not isinstance(items, list):
            raise ValueError(f"section {section.get('section_id')} items must be an array")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("each item must be an object")
            if not item.get("label") or not item.get("value"):
                raise ValueError("each item requires label and value")


def generate_spec_for_aircraft(
    client: anthropic.Anthropic,
    data_dir: Path,
    aircraft_id: str,
) -> Path | None:
    if not source_files_present(data_dir, aircraft_id):
        return None

    aircraft_name = AIRCRAFT_REGISTRY.get(aircraft_id, aircraft_id)
    limitations = load_aircraft_json(data_dir, aircraft_id, "limitations")
    emergency = load_aircraft_json(data_dir, aircraft_id, "emergency_procedures")
    systems = load_aircraft_json(data_dir, aircraft_id, "systems")
    assert limitations and emergency and systems

    user_prompt = build_user_prompt(aircraft_id, aircraft_name, limitations, emergency, systems)

    try:
        msg = client.messages.create(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT_BLOCKS,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        print(f"ERROR: API call failed for {aircraft_id}: {e}", file=sys.stderr)
        return None

    if getattr(msg, "usage", None) is not None:
        print(f"[usage {aircraft_id}] {msg.usage}", flush=True)

    block = msg.content[0]
    raw_text = block.text if hasattr(block, "text") else str(block)

    try:
        spec = json.loads(strip_json_fence(raw_text))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON for {aircraft_id}: {e}", file=sys.stderr)
        print(raw_text[:1500], file=sys.stderr)
        return None

    if not isinstance(spec, dict):
        print(f"ERROR: Expected JSON object for {aircraft_id}", file=sys.stderr)
        return None

    spec.setdefault("aircraft_name", aircraft_name)
    spec.setdefault("rating", "private")
    spec.setdefault("generated_date", date.today().isoformat())

    try:
        validate_spec(spec, aircraft_id)
    except ValueError as e:
        print(f"ERROR: Validation failed for {aircraft_id}: {e}", file=sys.stderr)
        return None

    out_dir = output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{aircraft_id}_private_study_sheet.json"
    out_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Generated study sheet spec for {aircraft_name} -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate checkride study sheet spec JSONs from extracted aircraft POH data."
    )
    parser.add_argument(
        "--aircraft",
        default=None,
        help="Single aircraft slug (e.g. r22). Default: all aircraft with complete source JSON.",
    )
    args = parser.parse_args()

    load_env()
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is missing or empty. Set it in repo .env", file=sys.stderr)
        raise SystemExit(2)

    data_dir = resolve_aircraft_data_dir()
    if not data_dir.is_dir():
        print(f"ERROR: Aircraft data directory not found: {data_dir}", file=sys.stderr)
        raise SystemExit(3)

    aircraft_ids = [args.aircraft] if args.aircraft else list(AIRCRAFT_REGISTRY.keys())
    if args.aircraft and args.aircraft not in AIRCRAFT_REGISTRY:
        print(f"ERROR: Unknown aircraft {args.aircraft!r}", file=sys.stderr)
        raise SystemExit(2)

    client = anthropic.Anthropic(api_key=api_key)
    generated = 0
    for aircraft_id in aircraft_ids:
        result = generate_spec_for_aircraft(client, data_dir, aircraft_id)
        if result:
            generated += 1

    print(f"Done: {generated}/{len(aircraft_ids)} study sheet specs written to {output_dir()}")
    if generated == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
