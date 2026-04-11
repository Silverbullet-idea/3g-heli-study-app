#!/usr/bin/env python3
"""Extract POH PDF text and call Anthropic to produce structured JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import anthropic
import pdfplumber
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
# override=True: a stale/empty ANTHROPIC_API_KEY in the shell would otherwise
# block values from .env (python-dotenv defaults to override=False).
load_dotenv(REPO_ROOT / ".env", override=True)
if not (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
    load_dotenv(REPO_ROOT.parent / ".env", override=True)

EXTRACTION_SCRIPT_VERSION = "1.0.0"

SYSTEM_PROMPT_LIMITATIONS = """You are extracting helicopter performance and limitation data from a 
Robinson R22 Pilot's Operating Handbook, Section 2 (Limitations).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

For every numeric value include:
  "value": <number>,
  "unit": "<string>",
  "notes": "<any conditions or qualifiers from the POH>",
  "confidence": "<extracted|inferred|verify>"

Use "extracted" when the value is clearly stated in plain text.
Use "inferred" when found in a table caption, figure, or requires interpretation.
Use "verify" when you cannot read the value confidently from the text.

Required schema:
{
  "airspeed_limits": {
    "vne_powered_to_3000ft": {"value": null, "unit": "KIAS", "notes": "", "confidence": ""},
    "vne_above_3000ft": {"value": null, "unit": "KIAS", "notes": "", "confidence": ""},
    "airspeed_indicator_green_arc_min": {"value": null, "unit": "KIAS", "notes": "", "confidence": ""},
    "airspeed_indicator_red_line": {"value": null, "unit": "KIAS", "notes": "", "confidence": ""}
  },
  "rotor_speed_limits": {
    "power_on_max": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "power_on_min": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "power_on_min_o320_variant": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "power_off_max": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "power_off_min": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""}
  },
  "weight_limits": {
    "max_gross_standard_hp": {"value": null, "unit": "lbs", "kg": null, "notes": "", "confidence": ""},
    "max_gross_alpha_beta_beta_ii": {"value": null, "unit": "lbs", "kg": null, "notes": "", "confidence": ""},
    "min_gross": {"value": null, "unit": "lbs", "kg": null, "notes": "", "confidence": ""},
    "max_per_seat_including_baggage": {"value": null, "unit": "lbs", "kg": null, "notes": "", "confidence": ""},
    "max_per_baggage_compartment": {"value": null, "unit": "lbs", "kg": null, "notes": "", "confidence": ""},
    "min_solo_pilot_weight": {"value": null, "unit": "lbs", "notes": "", "confidence": ""}
  },
  "altitude_limits": {
    "max_operating_density_altitude": {"value": null, "unit": "ft DA", "notes": "", "confidence": ""}
  },
  "engine": {
    "approved_models": [],
    "speed_max_continuous": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "speed_max_transient": {"value": null, "unit": "%", "rpm": null, "notes": "", "confidence": ""},
    "cht_max": {"value": null, "unit": "°F", "celsius": null, "notes": "", "confidence": ""},
    "oil_temp_max": {"value": null, "unit": "°F", "celsius": null, "notes": "", "confidence": ""},
    "oil_pressure_min_idle": {"value": null, "unit": "PSI", "notes": "", "confidence": ""},
    "oil_pressure_min_flight": {"value": null, "unit": "PSI", "notes": "", "confidence": ""},
    "oil_pressure_max_flight": {"value": null, "unit": "PSI", "notes": "", "confidence": ""},
    "oil_pressure_max_start_warmup": {"value": null, "unit": "PSI", "notes": "", "confidence": ""},
    "oil_quantity_min_takeoff": {"value": null, "unit": "qt", "liters": null, "notes": "", "confidence": ""},
    "carb_air_temp_caution_range_min": {"value": null, "unit": "°C", "notes": "", "confidence": ""},
    "carb_air_temp_caution_range_max": {"value": null, "unit": "°C", "notes": "", "confidence": ""}
  },
  "fuel": {
    "approved_grades": [],
    "capacity_bladder_tanks": {
      "main_total": {"value": null, "unit": "gal US", "liters": null},
      "main_usable": {"value": null, "unit": "gal US", "liters": null},
      "aux_total": {"value": null, "unit": "gal US", "liters": null},
      "aux_usable": {"value": null, "unit": "gal US", "liters": null},
      "combined_total": {"value": null, "unit": "gal US", "liters": null},
      "combined_usable": {"value": null, "unit": "gal US", "liters": null},
      "confidence": ""
    }
  },
  "required_equipment_for_dispatch": [],
  "flight_restrictions": [
    {"item": "", "status": "PROHIBITED|REQUIRED|PERMITTED", "notes": "", "confidence": ""}
  ],
  "faa_ad_95_26_04": {
    "note": "",
    "limitations": [
      {"item": "", "status": "", "notes": "", "confidence": ""}
    ]
  }
}
"""

SYSTEM_PROMPT_EMERGENCY = """You are extracting emergency procedure checklists from a Robinson R22 
Pilot's Operating Handbook, Section 3 (Emergency Procedures).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

Preserve EXACT step sequence from the POH. Do not summarize or paraphrase 
steps — verbatim accuracy is critical for flight training use.

For confidence:
  "extracted" = complete procedure clearly readable in text
  "inferred" = procedure found but some steps unclear from text formatting
  "verify" = procedure incomplete or unreadable — needs human review against PDF

{
  "procedures": [
    {
      "id": "<snake_case identifier>",
      "title": "<exact POH title>",
      "conditions": "<any entry conditions stated in POH, or empty string>",
      "steps": ["<step 1 verbatim>", "<step 2 verbatim>"],
      "warnings": ["<any WARNING or CAUTION notes associated with this procedure>"],
      "confidence": "<extracted|inferred|verify>"
    }
  ]
}
"""

SYSTEM_PROMPT_SYSTEMS = """You are extracting aircraft systems descriptions from a Robinson R22 
Pilot's Operating Handbook, Section 7 (Aircraft and Systems Description).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

{
  "systems": {
    "<system_name_snake_case>": {
      "title": "<exact POH section title>",
      "description": "<concise summary of how the system works>",
      "key_points": ["<important fact 1>", "<important fact 2>"],
      "components": ["<named component 1>", "<named component 2>"],
      "specifications": [
        {"item": "", "value": null, "unit": "", "notes": ""}
      ],
      "confidence": "<extracted|inferred|verify>"
    }
  }
}
"""

SECTION_CONFIG: dict[str, dict[str, str]] = {
    "limitations": {
        "system_prompt": SYSTEM_PROMPT_LIMITATIONS,
        "out_suffix": "limitations",
    },
    "emergency_procedures": {
        "system_prompt": SYSTEM_PROMPT_EMERGENCY,
        "out_suffix": "emergency_procedures",
    },
    "systems": {
        "system_prompt": SYSTEM_PROMPT_SYSTEMS,
        "out_suffix": "systems",
    },
}


def strip_markdown_json_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    t = re.sub(r"^```(?:json)?\s*", "", t, count=1, flags=re.IGNORECASE)
    t = re.sub(r"\s*```\s*$", "", t, count=1)
    return t.strip()


def count_verify_values(obj: Any) -> int:
    n = 0
    if isinstance(obj, dict):
        for v in obj.values():
            n += count_verify_values(v)
    elif isinstance(obj, list):
        for item in obj:
            n += count_verify_values(item)
    elif isinstance(obj, str) and obj == "verify":
        n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract POH PDF to structured JSON via Anthropic.")
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF relative to repository root",
    )
    parser.add_argument(
        "--section",
        required=True,
        choices=["limitations", "emergency_procedures", "systems"],
        help="POH section to extract",
    )
    args = parser.parse_args()

    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        print("Error: ANTHROPIC_API_KEY is missing or empty. Set it in .env or the environment.", file=sys.stderr)
        raise SystemExit(1)

    pdf_path = (REPO_ROOT / args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        raise SystemExit(1)

    cfg = SECTION_CONFIG[args.section]
    system_prompt = cfg["system_prompt"]

    parts: list[str] = []
    num_pages = 0
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"\n--- PAGE {i} ---\n")
            parts.append(text)

    raw_text = "".join(parts)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": raw_text}],
    )

    block = message.content[0]
    if block.type != "text":
        print(f"Error: unexpected content block type: {block.type}", file=sys.stderr)
        raise SystemExit(1)

    response_text = strip_markdown_json_fences(block.text)

    try:
        parsed: dict[str, Any] = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Error: model response is not valid JSON: {e}", file=sys.stderr)
        print("--- Response (first 2000 chars) ---", file=sys.stderr)
        print(response_text[:2000], file=sys.stderr)
        raise SystemExit(1) from e

    source_filename = pdf_path.name
    today = date.today().isoformat()

    metadata = {
        "aircraft": "R22",
        "poh_source": args.section,
        "source_file": source_filename,
        "extracted_date": today,
        "extraction_script_version": EXTRACTION_SCRIPT_VERSION,
    }
    merged: dict[str, Any] = {**metadata, **parsed}

    out_dir = REPO_ROOT / "extracted-data" / "aircraft"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"r22_{cfg['out_suffix']}.json"

    out_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    verify_count = count_verify_values(merged)
    print(f"Pages processed: {num_pages}")
    print(f"Output: {out_path}")
    print(f"Verify flags: {verify_count}")


if __name__ == "__main__":
    main()
