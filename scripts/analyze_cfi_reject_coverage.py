#!/usr/bin/env python3
"""Read-only CFI reject coverage analysis — writes cfi_reject_coverage_report.txt."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REJECT_CANDIDATES = [
    REPO / "question_banks" / "cfi" / "cfi_rejected.json",
    REPO / "question_banks" / "cfi" / "cfi_rejects.json",
]
BANK_CANDIDATES = [
    REPO / "question_banks" / "cfi" / "cfi_verified.json",
    REPO / "question-bank" / "qbank_cfi_helicopter.json",
]
REVIEW_LOG = REPO / "question-bank" / "review_changes.log"
FAILS_LOG = REPO / "question-bank" / "verification_fails.log"
ACS_JSON = REPO / "extracted-data" / "faa" / "FAA-S-ACS-29_CFI_Helicopter_ACS.json"
REPORT_PATH = REPO / "question_banks" / "cfi" / "cfi_reject_coverage_report.txt"

REJECTED_BLOCK_RE = re.compile(
    r"--- REJECTED ---\n(.*?)\n----------------------------------------",
    re.DOTALL,
)
CFI_ID_RE = re.compile(r"^(FI|HI)\.")
ACS_CODE_RE = re.compile(r"^(FI|HI)\.[IVXLC]+\.[A-Z]\.(K|R|S)\d+$")
AREA_RE = re.compile(r"^(FI|HI)\.[IVXLC]+")


def parse_rejected_block(block: str) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if line.startswith("Question ID:"):
            fields["id"] = line.split(":", 1)[1].strip()
        elif line.startswith("ACS Code:"):
            fields["acs_code"] = line.split(":", 1)[1].strip()
        elif line.startswith("Difficulty:"):
            fields["difficulty"] = line.split(":", 1)[1].strip()
    if not fields.get("id") or not CFI_ID_RE.match(fields["id"]):
        return None
    return fields


def load_rejects_from_log() -> list[dict[str, str]]:
    text = REVIEW_LOG.read_text(encoding="utf-8", errors="replace")
    rejects: list[dict[str, str]] = []
    for match in REJECTED_BLOCK_RE.finditer(text):
        item = parse_rejected_block(match.group(1))
        if item:
            rejects.append(item)
    return rejects


def load_rejects_from_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("questions") or data.get("rejected") or []
        if not rows:
            for area in data.get("areas_of_operation", []):
                for task in area.get("tasks", []):
                    for q in task.get("questions", []):
                        v = q.get("verification") or {}
                        status = str(v.get("status", "")).upper()
                        if status in {"REJECTED", "REJECT", "RYAN_REJECT"} or q.get("rejected"):
                            rows.append(q)
    else:
        rows = []
    out: list[dict] = []
    for q in rows:
        qid = str(q.get("id", ""))
        if CFI_ID_RE.match(qid):
            out.append(q)
    return out


def find_reject_source() -> tuple[str, list[dict]]:
    for path in REJECT_CANDIDATES:
        if path.is_file():
            return str(path.relative_to(REPO)), load_rejects_from_json(path)
    rejects = load_rejects_from_log()
    return str(REVIEW_LOG.relative_to(REPO)), rejects


def find_bank_path() -> Path:
    for path in BANK_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("No CFI main bank file found")


def load_acs_item_descriptions() -> dict[str, str]:
    if not ACS_JSON.is_file():
        return {}
    data = json.loads(ACS_JSON.read_text(encoding="utf-8"))
    desc: dict[str, str] = {}
    for area in data.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            for key in ("knowledge", "risk_management", "skills"):
                for line in task.get(key, []) or []:
                    text = str(line).strip()
                    code = text.split(" ", 1)[0]
                    if ACS_CODE_RE.match(code):
                        desc[code] = text
    return desc


def load_bank_task_titles(bank: dict) -> dict[str, str]:
    titles: dict[str, str] = {}
    for area in bank.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            code = str(task.get("acs_code", ""))
            title = str(task.get("title", ""))
            if code:
                titles[code] = title
    return titles


def count_bank_by_acs(bank: dict) -> Counter:
    counts: Counter = Counter()
    for area in bank.get("areas_of_operation", []):
        for task in area.get("tasks", []):
            for q in task.get("questions", []):
                code = str(q.get("acs_code", "")).strip()
                if code:
                    counts[code] += 1
    return counts


def normalize_acs_code(raw: str, question_id: str) -> str:
    code = raw.strip()
    if ACS_CODE_RE.match(code):
        return code
    m = re.match(r"^(FI|HI)\.[IVXLC]+\.[A-Z]\.(K|R|S)\d+", question_id)
    if m:
        return question_id.rsplit(".", 1)[0] if "." in question_id else question_id
    return code


def item_type(code: str) -> str:
    m = re.search(r"\.(K|R|S)\d+$", code)
    return m.group(1) if m else "?"


def area_of_operation(code: str) -> str:
    m = AREA_RE.match(code)
    return m.group(0) if m else "?"


def acs_prefix(code: str) -> str:
    return code.split(".", 1)[0] if "." in code else "?"


def build_report() -> str:
    source_label, raw_rejects = find_reject_source()
    bank_path = find_bank_path()
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    bank_counts = count_bank_by_acs(bank)
    acs_desc = load_acs_item_descriptions()
    task_titles = load_bank_task_titles(bank)

    rejects: list[dict] = []
    for row in raw_rejects:
        qid = str(row.get("id", ""))
        code = normalize_acs_code(str(row.get("acs_code", "")), qid)
        rejects.append({"id": qid, "acs_code": code})

    reject_by_code = Counter(r["acs_code"] for r in rejects)
    unique_reject_codes = len(reject_by_code)

    by_area = Counter(area_of_operation(c) for c in reject_by_code for _ in range(reject_by_code[c]))
    by_type = Counter(item_type(c) for c in reject_by_code for _ in range(reject_by_code[c]))
    by_prefix = Counter(acs_prefix(c) for c in reject_by_code for _ in range(reject_by_code[c]))

    top20 = reject_by_code.most_common(20)
    three_plus = [(c, n) for c, n in reject_by_code.most_common() if n >= 3]

    zero_remaining: list[tuple[str, int, int]] = []
    one_remaining: list[tuple[str, int, int]] = []
    for code, rej_n in reject_by_code.items():
        remaining = bank_counts.get(code, 0)
        original = remaining + rej_n
        if remaining == 0:
            zero_remaining.append((code, original, rej_n))
        elif remaining == 1:
            one_remaining.append((code, original, rej_n))

    zero_remaining.sort(key=lambda x: (-x[2], x[0]))
    one_remaining.sort(key=lambda x: (-x[2], x[0]))

    once_in_bank_codes = [
        code for code, rej_n in reject_by_code.items()
        if bank_counts.get(code, 0) + rej_n == 1
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = [
        "=== CFI REJECT COVERAGE REPORT ===",
        f"Generated: {now}",
        f"Reject source: {source_label}",
        f"Main bank: {bank_path.relative_to(REPO)} ({bank.get('total_questions', '?')} questions on disk)",
        f"Total rejected: {len(rejects)}",
        f"Unique ACS codes rejected: {unique_reject_codes}",
        "",
        "TOP 20 ACS ITEMS BY REJECT COUNT:",
    ]

    for code, n in top20:
        desc = acs_desc.get(code, "")
        if not desc:
            task_key = ".".join(code.split(".")[:3]) if code.count(".") >= 2 else code
            task_key_alt = task_key.replace("FI.", "FIH.", 1).replace("HI.", "HIH.", 1)
            task_title = task_titles.get(task_key_alt, task_titles.get(task_key, ""))
            desc = task_title or "(no description)"
        else:
            desc = desc if len(desc) <= 120 else desc[:117] + "..."
        lines.append(f"{code} — {n} rejects — {desc}")

    lines.extend(["", "REJECT DISTRIBUTION BY AREA:"])
    for area, n in sorted(by_area.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"{area} — {n} rejects")

    lines.extend(["", "REJECT DISTRIBUTION BY ITEM TYPE:"])
    type_labels = {"K": "Knowledge", "R": "Risk management", "S": "Skills", "?": "Unknown"}
    for t in ("K", "R", "S", "?"):
        if by_type.get(t):
            lines.append(f"{type_labels[t]} ({t}) — {by_type[t]} rejects")

    lines.extend(["", "ITEMS WITH 3+ REJECTS (POTENTIAL COVERAGE GAPS):"])
    if three_plus:
        for code, n in three_plus:
            remaining = bank_counts.get(code, 0)
            lines.append(f"{code} — {n} rejects — {remaining} remaining in bank")
    else:
        lines.append("(none)")

    fi_n = by_prefix.get("FI", 0)
    hi_n = by_prefix.get("HI", 0)
    lines.extend([
        "",
        "FI vs HI SPLIT:",
        f"FI. items: {fi_n} rejects",
        f"HI. items: {hi_n} rejects",
        "",
        "=== COVERAGE RISK ===",
        f"{len(zero_remaining)} ACS items have 0 remaining questions after rejects",
        f"{len(one_remaining)} ACS items have only 1 remaining question after rejects",
        f"{len(once_in_bank_codes)} rejected ACS codes had only 1 question in bank before reject (single-question items)",
        "",
        "ACS items with 0 remaining (code | original count | rejects):",
    ])
    if zero_remaining:
        for code, orig, rej in zero_remaining:
            lines.append(f"  {code} | was {orig} | rejected {rej}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("ACS items with only 1 remaining (code | original count | rejects):")
    if one_remaining:
        for code, orig, rej in one_remaining:
            lines.append(f"  {code} | was {orig} | rejected {rej}")
    else:
        lines.append("  (none)")

    lines.extend([
        "",
        "=== END REPORT ===",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    report = build_report()
    print(report, end="")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
