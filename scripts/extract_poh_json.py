#!/usr/bin/env python3
"""Extract POH PDF text and call Anthropic to produce structured JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import anthropic
import pdfplumber
from anthropic import APIStatusError, RateLimitError
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
# override=True: a stale/empty ANTHROPIC_API_KEY in the shell would otherwise
# block values from .env (python-dotenv defaults to override=False).
load_dotenv(REPO_ROOT / ".env", override=True)
if not (os.environ.get("ANTHROPIC_API_KEY") or "").strip():
    load_dotenv(REPO_ROOT.parent / ".env", override=True)

EXTRACTION_SCRIPT_VERSION = "1.0.0"

MODEL_ID = "claude-sonnet-4-6"
# ~200k input token ceiling; chunk larger handbooks.
FAA_HANDBOOK_INPUT_CHAR_BUDGET = 280_000
# ACS PDFs need many small chunks so each JSON response stays under max output tokens.
FAA_ACS_INPUT_CHAR_BUDGET = 35_000
# Opus allows at most 32_000 output tokens per request.
FAA_MAX_OUTPUT_TOKENS = 32_000
FAA_STREAM_MAX_RETRIES = 10
FAA_STREAM_RETRY_BASE_S = 55.0

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

SYSTEM_PROMPT_R44_LIMITATIONS = """You are extracting helicopter performance and limitation data
from a Robinson R44 Pilot's Operating Handbook, Section 2
(Limitations).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

For every numeric value include:
  "value": <number>,
  "unit": "<string>",
  "notes": "<any conditions or qualifiers from the POH>",
  "confidence": "<extracted|inferred|verify>"

Use "extracted" when clearly stated in plain text.
Use "inferred" when found in a table caption or figure.
Use "verify" when you cannot read the value confidently.

{
  "airspeed_limits": {
    "vne_powered": {"value":null,"unit":"KIAS","notes":"","confidence":""},
    "vne_autorotation": {"value":null,"unit":"KIAS","notes":"","confidence":""},
    "max_sideward": {"value":null,"unit":"KIAS","notes":"","confidence":""},
    "max_rearward": {"value":null,"unit":"KIAS","notes":"","confidence":""}
  },
  "rotor_speed_limits": {
    "power_on_max": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""},
    "power_on_min": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""},
    "power_off_max": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""},
    "power_off_min": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""}
  },
  "weight_limits": {
    "max_gross": {"value":null,"unit":"lbs","kg":null,"notes":"","confidence":""},
    "min_gross": {"value":null,"unit":"lbs","kg":null,"notes":"","confidence":""},
    "max_per_seat": {"value":null,"unit":"lbs","kg":null,"notes":"","confidence":""},
    "max_baggage": {"value":null,"unit":"lbs","kg":null,"notes":"","confidence":""}
  },
  "altitude_limits": {
    "max_operating_density_altitude": {"value":null,"unit":"ft DA","notes":"","confidence":""}
  },
  "engine": {
    "approved_models": [],
    "speed_max_continuous": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""},
    "speed_max_transient": {"value":null,"unit":"%","rpm":null,"notes":"","confidence":""},
    "cht_max": {"value":null,"unit":"°F","celsius":null,"notes":"","confidence":""},
    "oil_temp_max": {"value":null,"unit":"°F","celsius":null,"notes":"","confidence":""},
    "oil_pressure_min_idle": {"value":null,"unit":"PSI","notes":"","confidence":""},
    "oil_pressure_min_flight": {"value":null,"unit":"PSI","notes":"","confidence":""},
    "oil_pressure_max_flight": {"value":null,"unit":"PSI","notes":"","confidence":""},
    "oil_quantity_min_takeoff": {"value":null,"unit":"qt","liters":null,"notes":"","confidence":""}
  },
  "fuel": {
    "approved_grades": [],
    "capacity": {
      "total": {"value":null,"unit":"gal US","liters":null},
      "usable": {"value":null,"unit":"gal US","liters":null},
      "confidence": ""
    }
  },
  "required_equipment_for_dispatch": [],
  "flight_restrictions": [
    {"item":"","status":"PROHIBITED|REQUIRED|PERMITTED","notes":"","confidence":""}
  ]
}
"""

SYSTEM_PROMPT_R44_EMERGENCY = """You are extracting emergency procedure checklists from a Robinson
R44 Pilot's Operating Handbook, Section 3 (Emergency Procedures).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

Preserve EXACT step sequence from the POH. Verbatim accuracy is
critical for flight training use.

For confidence:
  "extracted" = complete procedure clearly readable
  "inferred" = found but some steps unclear from formatting
  "verify" = incomplete or unreadable — needs human review

{
  "procedures": [
    {
      "id": "<snake_case>",
      "title": "<exact POH title>",
      "conditions": "<entry conditions or empty string>",
      "steps": ["<step 1 verbatim>", "<step 2 verbatim>"],
      "warnings": ["<WARNING or CAUTION notes>"],
      "confidence": "<extracted|inferred|verify>"
    }
  ]
}
"""

SYSTEM_PROMPT_R44_SYSTEMS = """You are extracting aircraft systems descriptions from a Robinson
R44 Pilot's Operating Handbook, Section 7 (Aircraft and Systems
Description).

Return ONLY valid JSON — no explanation, no markdown, no preamble.

{
  "systems": {
    "<system_name_snake_case>": {
      "title": "<exact POH section title>",
      "description": "<concise summary>",
      "key_points": ["<fact 1>", "<fact 2>"],
      "components": ["<component 1>", "<component 2>"],
      "specifications": [
        {"item":"","value":null,"unit":"","notes":""}
      ],
      "confidence": "<extracted|inferred|verify>"
    }
  }
}
"""

SYSTEM_PROMPT_FAA_HANDBOOK = """You are extracting structured knowledge from an FAA helicopter
training handbook. This content will be used to create study
sheets for student helicopter pilots preparing for FAA knowledge
exams and checkrides.

Return ONLY valid JSON — no explanation, no markdown, no preamble.

Extract content organized by chapter or major topic section.
For each topic include a concise summary, key terms, important
values with units, mnemonics, and key points.

For confidence flags:
  "extracted" = clearly stated in plain text
  "inferred" = implied or requires interpretation
  "verify" = unclear or incomplete

{
  "handbook_title": "",
  "topics": [
    {
      "id": "<snake_case>",
      "title": "<chapter or section title>",
      "summary": "<2-3 sentence overview>",
      "key_terms": [
        {"term": "", "definition": ""}
      ],
      "key_values": [
        {"item":"","value":null,"unit":"","notes":"","confidence":""}
      ],
      "mnemonics": [
        {"mnemonic":"","meaning":"","notes":""}
      ],
      "key_points": ["",""],
      "confidence": "<extracted|inferred|verify>"
    }
  ]
}
"""

SYSTEM_PROMPT_FAA_ACS = """You are extracting structured data from an FAA Airman
Certification Standards (ACS) document for helicopter pilots.
This content will be used to create checkride preparation
study sheets.

Return ONLY valid JSON — no explanation, no markdown, no preamble.

Extract every Task in every Area of Operation. Capture knowledge,
risk management, and skills standards verbatim — these are the
exact standards an examiner will use on a checkride.

{
  "certificate_level": "",
  "areas_of_operation": [
    {
      "id": "<snake_case>",
      "title": "<exact ACS title>",
      "tasks": [
        {
          "id": "<snake_case>",
          "title": "<exact task title>",
          "knowledge": ["<item 1>", "<item 2>"],
          "risk_management": ["<item 1>", "<item 2>"],
          "skills": ["<item 1>", "<item 2>"],
          "confidence": "<extracted|inferred|verify>"
        }
      ]
    }
  ]
}
"""

SECTION_CONFIG: dict[str, dict[str, str]] = {
    "limitations": {"system_prompt": SYSTEM_PROMPT_LIMITATIONS},
    "emergency_procedures": {"system_prompt": SYSTEM_PROMPT_EMERGENCY},
    "systems": {"system_prompt": SYSTEM_PROMPT_SYSTEMS},
    "r44_limitations": {"system_prompt": SYSTEM_PROMPT_R44_LIMITATIONS},
    "r44_emergency_procedures": {"system_prompt": SYSTEM_PROMPT_R44_EMERGENCY},
    "r44_systems": {"system_prompt": SYSTEM_PROMPT_R44_SYSTEMS},
    "faa_handbook": {"system_prompt": SYSTEM_PROMPT_FAA_HANDBOOK},
    "faa_acs": {"system_prompt": SYSTEM_PROMPT_FAA_ACS},
}


def strip_markdown_json_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    t = re.sub(r"^```(?:json)?\s*", "", t, count=1, flags=re.IGNORECASE)
    t = re.sub(r"\s*```\s*$", "", t, count=1)
    return t.strip()


def first_balanced_json_object(text: str) -> str:
    """First top-level JSON object; respects quoted strings."""
    start = text.find("{")
    if start < 0:
        return text.strip()
    depth = 0
    in_string = False
    escape = False
    quote = ""
    i = start
    while i < len(text):
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == quote:
                in_string = False
            i += 1
            continue
        if c in "\"'":
            in_string = True
            quote = c
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return text[start:].strip()


def extract_json_blob(text: str) -> str:
    """Strip markdown fences, preamble, or prose around a JSON object."""
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if fence:
        t = fence.group(1).strip()
    t = strip_markdown_json_fences(t)
    if not t.lstrip().startswith("{"):
        j = t.find("{")
        if j > 0:
            t = t[j:]
    return first_balanced_json_object(t)


def pages_to_raw_text(page_rows: list[tuple[int, str]]) -> str:
    parts: list[str] = []
    for pnum, txt in page_rows:
        parts.append(f"\n--- PAGE {pnum} ---\n")
        parts.append(txt)
    return "".join(parts)


def chunk_pages_by_char_budget(
    page_rows: list[tuple[int, str]],
    max_chars: int,
) -> list[list[tuple[int, str]]]:
    chunks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    size = 0
    for pnum, txt in page_rows:
        block_len = len(f"\n--- PAGE {pnum} ---\n") + len(txt)
        if current and size + block_len > max_chars:
            chunks.append(current)
            current = []
            size = 0
        current.append((pnum, txt))
        size += block_len
    if current:
        chunks.append(current)
    return chunks


def call_anthropic_faa_stream(
    client: anthropic.Anthropic,
    *,
    model_id: str,
    max_tokens: int,
    system_prompt: str,
    user_text: str,
) -> str:
    delay = FAA_STREAM_RETRY_BASE_S
    last_err: Exception | None = None
    for attempt in range(FAA_STREAM_MAX_RETRIES):
        try:
            if attempt:
                print(f"Waiting {delay:.0f}s before retry {attempt + 1}/{FAA_STREAM_MAX_RETRIES}...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 1.35, 300.0)
            with client.messages.stream(
                model=model_id,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_text}],
            ) as stream:
                return stream.get_final_text()
        except RateLimitError as e:
            last_err = e
            print(f"Rate limited: {e}", file=sys.stderr)
        except APIStatusError as e:
            last_err = e
            if getattr(e, "status_code", None) == 429:
                print(f"HTTP 429: {e}", file=sys.stderr)
            else:
                raise
    if last_err:
        raise last_err
    raise RuntimeError("Anthropic streaming failed without specific error")


def max_tokens_for_poh_section(section: str) -> int:
    if section == "r44_limitations":
        return 8192
    if section in ("r44_emergency_procedures", "r44_systems"):
        return 16384
    return 4096


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
        choices=[
            "limitations",
            "emergency_procedures",
            "systems",
            "r44_limitations",
            "r44_emergency_procedures",
            "r44_systems",
            "faa_handbook",
            "faa_acs",
        ],
        help="POH section to extract",
    )
    args = parser.parse_args()
    section = args.section

    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        print("Error: ANTHROPIC_API_KEY is missing or empty. Set it in .env or the environment.", file=sys.stderr)
        raise SystemExit(1)

    pdf_path = (REPO_ROOT / args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        raise SystemExit(1)

    cfg = SECTION_CONFIG[section]
    system_prompt = cfg["system_prompt"]

    page_rows: list[tuple[int, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            page_rows.append((i, page.extract_text() or ""))

    raw_full = pages_to_raw_text(page_rows)
    client = anthropic.Anthropic(api_key=api_key)

    if section in ("faa_handbook", "faa_acs"):
        if section == "faa_handbook":
            char_budget = FAA_HANDBOOK_INPUT_CHAR_BUDGET
            subchunks = chunk_pages_by_char_budget(page_rows, char_budget)
            use_chunks = len(subchunks) > 1
        else:
            char_budget = FAA_ACS_INPUT_CHAR_BUDGET
            subchunks = chunk_pages_by_char_budget(page_rows, char_budget)
            use_chunks = len(subchunks) > 1

        if use_chunks:
            print(
                f"Splitting PDF ({len(raw_full)} chars) into {len(subchunks)} API chunk(s).",
                file=sys.stderr,
            )
            if section == "faa_handbook":
                parsed: dict[str, Any] = {"handbook_title": "", "topics": []}
            else:
                parsed = {"certificate_level": "", "areas_of_operation": []}
            for ci, ch in enumerate(subchunks):
                p_lo = ch[0][0]
                p_hi = ch[-1][0]
                prefix = (
                    f"MULTI-PART EXTRACTION: part {ci + 1} of {len(subchunks)} "
                    f"(PDF pages {p_lo} to {p_hi} of {num_pages}). "
                    "Extract ONLY from the excerpt below. Use the same JSON schema. "
                    "Do not invent content from pages not shown.\n\n"
                )
                chunk_text = prefix + pages_to_raw_text(ch)
                response_text = call_anthropic_faa_stream(
                    client,
                    model_id=MODEL_ID,
                    max_tokens=FAA_MAX_OUTPUT_TOKENS,
                    system_prompt=system_prompt,
                    user_text=chunk_text,
                )
                try:
                    part = json.loads(extract_json_blob(response_text))
                except json.JSONDecodeError as e:
                    print(f"Error: invalid JSON (chunk {ci + 1}): {e}", file=sys.stderr)
                    print(response_text[:2000], file=sys.stderr)
                    raise SystemExit(1) from e
                if section == "faa_handbook":
                    parsed["handbook_title"] = parsed["handbook_title"] or part.get("handbook_title") or ""
                    parsed["topics"].extend(part.get("topics") or [])
                else:
                    parsed["certificate_level"] = parsed["certificate_level"] or part.get("certificate_level") or ""
                    parsed["areas_of_operation"].extend(part.get("areas_of_operation") or [])
        else:
            response_text = call_anthropic_faa_stream(
                client,
                model_id=MODEL_ID,
                max_tokens=FAA_MAX_OUTPUT_TOKENS,
                system_prompt=system_prompt,
                user_text=raw_full,
            )
            try:
                parsed = json.loads(extract_json_blob(response_text))
            except json.JSONDecodeError as e:
                print(f"Error: model response is not valid JSON: {e}", file=sys.stderr)
                print(response_text[:2000], file=sys.stderr)
                raise SystemExit(1) from e
    else:
        max_out = max_tokens_for_poh_section(section)
        # SDK requires streaming when a request may exceed the non-streaming timeout
        # (large max_tokens on long PDF text — e.g. R44 emergency/systems).
        response_text = call_anthropic_faa_stream(
            client,
            model_id=MODEL_ID,
            max_tokens=max_out,
            system_prompt=system_prompt,
            user_text=raw_full,
        )
        try:
            parsed = json.loads(extract_json_blob(response_text))
        except json.JSONDecodeError as e:
            print(f"Error: model response is not valid JSON: {e}", file=sys.stderr)
            print(response_text[:2000], file=sys.stderr)
            raise SystemExit(1) from e

    metadata: dict[str, Any] = {}
    if section in ("limitations", "emergency_procedures", "systems"):
        metadata["aircraft"] = "R22"
    elif section in ("r44_limitations", "r44_emergency_procedures", "r44_systems"):
        metadata["aircraft"] = "R44"
    else:
        metadata["aircraft"] = None

    metadata["poh_source"] = section
    metadata["source_file"] = Path(args.pdf).name
    metadata["extracted_date"] = date.today().isoformat()
    metadata["extraction_script_version"] = EXTRACTION_SCRIPT_VERSION
    merged: dict[str, Any] = {**metadata, **parsed}

    if section in ("limitations", "emergency_procedures", "systems"):
        out_dir = REPO_ROOT / "extracted-data" / "aircraft"
        out_filename = f"r22_{section}.json"
    elif section in ("r44_limitations", "r44_emergency_procedures", "r44_systems"):
        out_dir = REPO_ROOT / "extracted-data" / "aircraft"
        section_short = section.replace("r44_", "")
        out_filename = f"r44_{section_short}.json"
    elif section in ("faa_handbook", "faa_acs"):
        out_dir = REPO_ROOT / "extracted-data" / "faa"
        out_filename = f"{Path(args.pdf).stem}.json"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_filename

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
