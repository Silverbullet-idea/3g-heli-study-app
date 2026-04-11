#!/usr/bin/env python3
"""
Extract structured POH data from Robinson PDFs via pdfplumber + Anthropic API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import pdfplumber

try:
    import anthropic
except ImportError as e:
    print("Missing dependency: anthropic. Install with: pip install anthropic", file=sys.stderr)
    raise SystemExit(1) from e

EXTRACTION_SCRIPT_VERSION = "1.0.0"

SECTION_TO_PROMPT: dict[str, str] = {
    "limitations": """You are extracting helicopter performance and limitation data from a Robinson R22 Pilot's Operating Handbook, Section 2 (Limitations).

Extract ALL limits and return ONLY valid JSON matching this exact schema. No explanation, no markdown, no preamble — raw JSON only.

For every numeric value, include:
  "value": <number>,
  "unit": "<string>",
  "notes": "<any conditions or qualifiers from the POH>",
  "confidence": "<extracted|inferred|verify>"

Use "extracted" when the value is clearly stated in plain text.
Use "inferred" when the value appears in a table caption, figure, or requires interpretation.
Use "verify" when you cannot read the value confidently from the text provided.

Required schema:
{
  "airspeed_limits": {
    "vne_powered": { "value": null, "unit": "KIAS", "notes": "", "confidence": "" },
    "vne_autorotation": { "value": null, "unit": "KIAS", "notes": "", "confidence": "" },
    "max_sideward": { "value": null, "unit": "KIAS", "notes": "", "confidence": "" },
    "max_rearward": { "value": null, "unit": "KIAS", "notes": "", "confidence": "" }
  },
  "weight_limits": {
    "max_gross_weight": { "value": null, "unit": "lbs", "notes": "", "confidence": "" },
    "max_fuel_usable": { "value": null, "unit": "gal", "notes": "", "confidence": "" }
  },
  "altitude_limits": {
    "max_operating": { "value": null, "unit": "ft DA", "notes": "", "confidence": "" }
  },
  "rotor_limits": {
    "nr_normal_min": { "value": null, "unit": "%", "notes": "", "confidence": "" },
    "nr_normal_max": { "value": null, "unit": "%", "notes": "", "confidence": "" },
    "low_rotor_warning": { "value": null, "unit": "%", "notes": "", "confidence": "" }
  },
  "engine_limits": {
    "oil_temp_max": { "value": null, "unit": "°C", "notes": "", "confidence": "" },
    "oil_press_min": { "value": null, "unit": "PSI", "notes": "", "confidence": "" },
    "oil_press_max": { "value": null, "unit": "PSI", "notes": "", "confidence": "" },
    "cht_max": { "value": null, "unit": "°F", "notes": "", "confidence": "" },
    "fuel_pressure_min": { "value": null, "unit": "PSI", "notes": "", "confidence": "" },
    "fuel_pressure_max": { "value": null, "unit": "PSI", "notes": "", "confidence": "" }
  },
  "temperature_limits": {
    "oat_min": { "value": null, "unit": "°C", "notes": "", "confidence": "" },
    "oat_max": { "value": null, "unit": "°C", "notes": "", "confidence": "" }
  },
  "restrictions": [
    { "item": "", "status": "PROHIBITED|REQUIRED|PERMITTED", "notes": "" }
  ]
}
""",
    "emergency_procedures": """You are extracting emergency procedure checklists from a Robinson R22 Pilot's Operating Handbook, Section 3 (Emergency Procedures).

Extract ALL procedures and return ONLY valid JSON. No explanation, no markdown, no preamble — raw JSON only.

For each procedure, preserve the EXACT step sequence from the POH. Do not summarize or paraphrase steps — verbatim accuracy is critical for flight training use.

{
  "procedures": [
    {
      "id": "<snake_case identifier>",
      "title": "<exact POH title>",
      "conditions": "<any entry conditions stated in the POH>",
      "steps": ["<step 1 verbatim>", "<step 2 verbatim>"],
      "confidence": "<extracted|inferred|verify>"
    }
  ]
}
""",
    "systems": """You are extracting aircraft systems descriptions from a Robinson R22 Pilot's Operating Handbook, Section 7 (Aircraft and Systems Description).

Extract each system subsection and return ONLY valid JSON. No explanation, no markdown, no preamble — raw JSON only.

{
  "systems": {
    "<system_name>": {
      "description": "<concise summary of how the system works>",
      "key_points": ["<important fact 1>", "<important fact 2>"],
      "components": ["<named component 1>", "<named component 2>"],
      "confidence": "<extracted|inferred|verify>"
    }
  }
}
""",
}

SECTION_TO_FILENAME = {
    "limitations": "r22_limitations.json",
    "emergency_procedures": "r22_emergency_procedures.json",
    "systems": "r22_systems.json",
}

MODEL = "claude-opus-4-20250514"
# Section 7 (systems) needs a higher ceiling; 4096 truncates mid-JSON.
MAX_TOKENS_BY_SECTION = {
    "limitations": 4096,
    "emergency_procedures": 4096,
    "systems": 16384,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_dotenv_files() -> None:
    """Load ANTHROPIC_API_KEY from .env in repo root, then workspace parent.

    Uses override=True so values in .env win over a stale ANTHROPIC_API_KEY in the
    machine/user environment (common cause of 401 when the key in .env is correct).
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = repo_root()
    for env_path in (root / ".env", root.parent / ".env"):
        if env_path.is_file():
            load_dotenv(env_path, override=True)


def extract_pdf_text(pdf_path: Path) -> tuple[str, int]:
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            t = page.extract_text() or ""
            parts.append(f"\n--- PAGE {i} ---\n")
            parts.append(t)
    return "".join(parts), n_pages


def strip_code_fence(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?", text)
    if m:
        text = text[m.end() :]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text.strip()


def parse_model_json(text: str) -> dict:
    cleaned = strip_code_fence(text)
    return json.loads(cleaned)


def count_verify_flags(obj: object) -> int:
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "confidence" and v == "verify":
                n += 1
            else:
                n += count_verify_flags(v)
    elif isinstance(obj, list):
        for item in obj:
            n += count_verify_flags(item)
    return n


def merge_metadata(
    data: dict,
    aircraft: str,
    poh_section: str,
    source_file: str,
) -> dict:
    meta = {
        "aircraft": aircraft,
        "poh_source": poh_section,
        "source_file": source_file,
        "extracted_date": date.today().isoformat(),
        "extraction_script_version": EXTRACTION_SCRIPT_VERSION,
    }
    if not isinstance(data, dict):
        return {"metadata": meta, "data": data}
    out: dict = {"metadata": meta}
    for k, v in data.items():
        out[k] = v
    return out


def call_anthropic(system_prompt: str, user_content: str, max_tokens: int) -> str:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)
    texts: list[str] = []
    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            for chunk in stream.text_stream:
                texts.append(chunk)
    except anthropic.AuthenticationError as e:
        print(
            "Anthropic API rejected the key (401). "
            "Confirm ANTHROPIC_API_KEY in .env (repo or parent folder), "
            "or remove a stale key from Windows user environment variables.",
            file=sys.stderr,
        )
        raise e
    if not texts:
        raise RuntimeError("No text content in API response")
    return "".join(texts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract POH data from PDF via Anthropic.")
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF relative to repo root (e.g. raw-pdfs/robinson/foo.pdf)",
    )
    parser.add_argument(
        "--section",
        required=True,
        choices=("limitations", "emergency_procedures", "systems"),
        help="POH section type",
    )
    args = parser.parse_args()

    load_dotenv_files()

    root = repo_root()
    pdf_rel = Path(args.pdf)
    pdf_path = (root / pdf_rel).resolve()
    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        raise SystemExit(1)

    system_prompt = SECTION_TO_PROMPT[args.section]
    max_tokens = MAX_TOKENS_BY_SECTION[args.section]
    full_text, page_count = extract_pdf_text(pdf_path)
    raw_response = call_anthropic(system_prompt, full_text, max_tokens)

    try:
        parsed = parse_model_json(raw_response)
    except json.JSONDecodeError as e:
        print("Failed to parse model output as JSON:", e, file=sys.stderr)
        print("--- model output (first 2000 chars) ---", file=sys.stderr)
        print(raw_response[:2000], file=sys.stderr)
        raise SystemExit(1) from e

    source_name = pdf_path.name
    final = merge_metadata(parsed, "R22", args.section, source_name)
    verify_count = count_verify_flags(final)

    out_dir = root / "extracted-data" / "aircraft"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = SECTION_TO_FILENAME[args.section]
    out_path = out_dir / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Pages processed: {page_count}")
    print(f"Output written: {out_path.relative_to(root)}")
    print(f'"verify" confidence flags: {verify_count}')


if __name__ == "__main__":
    main()
