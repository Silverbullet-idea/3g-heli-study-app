#!/usr/bin/env python3
"""Local Flask UI to review FLAG-status questions in the verified question bank."""

from __future__ import annotations

import argparse
import atexit
import html
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, redirect, request

REPO_ROOT = Path(__file__).resolve().parent.parent

CHANGE_LOG_PATH = REPO_ROOT / "question-bank" / "review_changes.log"

app = Flask(__name__)

_data: dict[str, Any] | None = None
_json_path: Path | None = None

_change_log_lock = threading.Lock()
_session_counts = {"approved": 0, "edited": 0, "rejected": 0}
_change_log_footer_written = False


def _local_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _format_issues_lines(v: dict[str, Any]) -> str:
    issues = v.get("issues") if isinstance(v.get("issues"), list) else []
    if not issues:
        return "(none)"
    return "\n".join(str(x) for x in issues)


def _append_change_log_block(text: str) -> None:
    with _change_log_lock:
        CHANGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CHANGE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")


def _write_session_header() -> None:
    ts = _local_ts()
    block = (
        "========================================\n"
        f"Review session started: {ts}\n"
        "========================================\n"
    )
    _append_change_log_block(block)


def _write_session_footer() -> None:
    global _change_log_footer_written
    with _change_log_lock:
        if _change_log_footer_written:
            return
        _change_log_footer_written = True
    ts = _local_ts()
    a = _session_counts["approved"]
    e = _session_counts["edited"]
    r = _session_counts["rejected"]
    block = (
        f"\nSession ended: {ts}\n"
        f"This session: {a} approved, {e} edited, {r} rejected\n"
        "========================================\n"
    )
    _append_change_log_block(block)


def _log_approval_line(qid: str) -> None:
    ts = _local_ts()
    _append_change_log_block(f"APPROVED: {qid} | {ts}\n")


def _log_edit(
    q: dict[str, Any],
    original_answer: str,
    revised_answer: str,
) -> None:
    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    qid = str(q.get("id") or "")
    acs = str(q.get("acs_code") or "")
    diff = str(q.get("difficulty") or "")
    qtext = str(q.get("question") or "")
    issues_block = _format_issues_lines(v)
    reviewed = _local_ts()
    block = (
        "--- EDITED ---\n"
        f"Question ID:   {qid}\n"
        f"ACS Code:      {acs}\n"
        f"Difficulty:    {diff}\n"
        "\n"
        "Question:\n"
        f"{qtext}\n"
        "\n"
        "Original Answer:\n"
        f"{original_answer}\n"
        "\n"
        "Revised Answer:\n"
        f"{revised_answer}\n"
        "\n"
        "Verifier Notes:\n"
        f"{issues_block}\n"
        "\n"
        f"Reviewed: {reviewed}\n"
        "----------------------------------------\n"
    )
    _append_change_log_block(block)


def _log_rejection(q: dict[str, Any]) -> None:
    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    qid = str(q.get("id") or "")
    acs = str(q.get("acs_code") or "")
    diff = str(q.get("difficulty") or "")
    qtext = str(q.get("question") or "")
    ans = str(q.get("answer") or "")
    issues_block = _format_issues_lines(v)
    reviewed = _local_ts()
    block = (
        "--- REJECTED ---\n"
        f"Question ID:   {qid}\n"
        f"ACS Code:      {acs}\n"
        f"Difficulty:    {diff}\n"
        "\n"
        "Question:\n"
        f"{qtext}\n"
        "\n"
        "Answer (at time of rejection):\n"
        f"{ans}\n"
        "\n"
        "Reason for rejection (verifier notes):\n"
        f"{issues_block}\n"
        "\n"
        f"Reviewed: {reviewed}\n"
        "----------------------------------------\n"
    )
    _append_change_log_block(block)


def load_bank(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_bank(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


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


def collect_flag_queue(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Questions with verification.status == FLAG, sorted by confidence ascending."""
    rows: list[tuple[float, dict[str, Any]]] = []
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                v = q.get("verification")
                if not isinstance(v, dict):
                    continue
                if v.get("status") != "FLAG":
                    continue
                try:
                    conf = float(v.get("confidence", 0.0))
                except (TypeError, ValueError):
                    conf = 0.0
                rows.append((conf, q))
    rows.sort(key=lambda x: x[0])
    return [q for _, q in rows]


def find_question_by_id(data: dict[str, Any], qid: str) -> dict[str, Any] | None:
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if isinstance(q, dict) and q.get("id") == qid:
                    return q
    return None


def find_task_for_question(data: dict[str, Any], qid: str) -> dict[str, Any] | None:
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if isinstance(q, dict) and q.get("id") == qid:
                    return task
    return None


def count_reviewed_by_notes(data: dict[str, Any]) -> tuple[int, int]:
    approved = 0
    edited = 0
    for area in data.get("areas_of_operation") or []:
        if not isinstance(area, dict):
            continue
        for task in area.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for q in task.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                v = q.get("verification")
                if not isinstance(v, dict) or v.get("status") != "REVIEWED_PASS":
                    continue
                notes = str(q.get("ryan_notes") or "")
                if notes == "approved":
                    approved += 1
                elif notes == "edited":
                    edited += 1
    return approved, edited


def count_ryan_rejects(log_path: Path) -> int:
    if not log_path.is_file():
        return 0
    n = 0
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("RYAN_REJECT\t"):
            n += 1
    return n


def append_ryan_reject_log(log_path: Path, qid: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"RYAN_REJECT\t{ts}\t{qid}\tManual rejection during review\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def progress_stats(data: dict[str, Any], log_path: Path) -> dict[str, int]:
    queue = collect_flag_queue(data)
    appr, ed = count_reviewed_by_notes(data)
    rej = count_ryan_rejects(log_path)
    processed = appr + ed + rej
    remaining = len(queue)
    total_pile = processed + remaining
    return {
        "approved": appr,
        "edited": ed,
        "rejected": rej,
        "processed": processed,
        "remaining": remaining,
        "total_pile": total_pile,
    }


def difficulty_badge_style(diff: str) -> str:
    d = (diff or "").lower()
    if d == "basic":
        bg = "#228B22"
    elif d == "intermediate":
        bg = "#E8650A"
    elif d == "advanced":
        bg = "#C62828"
    else:
        bg = "#555"
    return f"display:inline-block;padding:4px 10px;border-radius:4px;background:{bg};color:#fff;font-size:0.85em;font-weight:bold;"


def page_shell(inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>FLAG Question Review</title>
</head>
<body style="margin:0;font-family:Segoe UI,system-ui,sans-serif;background:#1a1a1a;color:#fff;padding:24px;max-width:920px;margin-left:auto;margin-right:auto;">
{inner}
</body>
</html>"""


@app.route("/")
def index() -> str:
    assert _data is not None and _json_path is not None
    log_path = REPO_ROOT / "question-bank" / "verification_fails.log"
    stats = progress_stats(_data, log_path)
    queue = collect_flag_queue(_data)

    if not queue:
        inner = f"""
<h1 style="color:#E8650A;margin-top:0;">FLAG review queue</h1>
<p>All FLAG items are cleared — nothing left to review.</p>
<p><a href="/summary" style="color:#E8650A;">View summary</a></p>
"""
        return page_shell(inner)

    q = queue[0]
    qid = str(q.get("id", ""))
    pos = stats["processed"] + 1
    total_y = stats["total_pile"]
    z = stats["remaining"]

    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    conf = v.get("confidence", 0.0)
    try:
        conf_f = float(conf)
    except (TypeError, ValueError):
        conf_f = 0.0
    issues = v.get("issues") if isinstance(v.get("issues"), list) else []
    issues_html = ""
    if issues:
        items = "".join(f"<li>{html.escape(str(x))}</li>" for x in issues)
        issues_html = f"""
<div style="background:#3d3510;border:1px solid #bda623;padding:12px 16px;border-radius:6px;margin:16px 0;">
<strong style="color:#ffeb3b;">Verifier issues</strong>
<ul style="margin:8px 0 0 18px;color:#ffecb3;">{items}</ul>
</div>"""

    diff = str(q.get("difficulty") or "")
    badge_style = difficulty_badge_style(diff)
    tags = q.get("tags") if isinstance(q.get("tags"), list) else []
    tags_s = ", ".join(html.escape(str(t)) for t in tags)

    fu = str(q.get("follow_up") or "").strip()
    fua = str(q.get("follow_up_answer") or "").strip()
    follow_block = ""
    if fu or fua:
        follow_block = f"""
<div style="margin-top:20px;padding:12px;background:#2a2a2a;border-radius:6px;">
<p style="margin:0 0 8px 0;color:#aaa;font-size:0.9em;">Follow-up (read-only)</p>
<p style="margin:0 0 8px 0;">{html.escape(fu) if fu else "<em>(none)</em>"}</p>
<p style="margin:0;color:#ccc;white-space:pre-wrap;">{html.escape(fua) if fua else ""}</p>
</div>"""

    ans = str(q.get("answer") or "")

    inner = f"""
<h1 style="color:#E8650A;margin-top:0;">FLAG Question Review</h1>
<p style="color:#ccc;"><strong>{stats["processed"]}</strong> of <strong>{total_y}</strong> reviewed — <strong>{z}</strong> remaining</p>
<p style="color:#bbb;">Question <strong style="color:#fff;">{pos}</strong> of <strong>{total_y}</strong></p>
<p style="color:#888;font-size:0.95em;">Keyboard: <kbd style="background:#333;padding:2px 6px;border-radius:3px;">A</kbd> Approve · <kbd style="background:#333;padding:2px 6px;border-radius:3px;">R</kbd> Reject</p>

<div style="background:#252525;padding:20px;border-radius:8px;border:1px solid #333;">
<p style="margin:0 0 8px 0;"><span style="{badge_style}">{html.escape(diff or "?")}</span>
<span style="color:#888;margin-left:12px;">confidence: {conf_f:.2f}</span></p>
<p style="margin:8px 0;color:#aaa;font-size:0.9em;">id: {html.escape(qid)} · acs_code: {html.escape(str(q.get("acs_code") or ""))}</p>
<p style="margin:8px 0;color:#bbb;">tags: {tags_s or "(none)"}</p>
<h2 style="font-size:1.1em;margin:20px 0 10px 0;color:#E8650A;">Question</h2>
<p style="white-space:pre-wrap;line-height:1.5;margin:0;">{html.escape(str(q.get("question") or ""))}</p>
{issues_html}
<h2 style="font-size:1.1em;margin:20px 0 10px 0;color:#E8650A;">Answer (edit below)</h2>
<textarea id="answerBox" name="answer" form="formEdit" rows="8" style="width:100%;min-height:12em;box-sizing:border-box;background:#1a1a1a;color:#fff;border:1px solid #444;border-radius:4px;padding:10px;font-size:1rem;">{html.escape(ans)}</textarea>
{follow_block}

<div style="margin-top:20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;">
<button type="button" id="approveBtn" style="background:#E8650A;color:#fff;border:none;padding:10px 20px;border-radius:6px;font-weight:bold;cursor:pointer;">Approve</button>
<button type="submit" form="formEdit" style="background:#E8650A;color:#fff;border:none;padding:10px 20px;border-radius:6px;font-weight:bold;cursor:pointer;">Save Edit</button>
<button type="button" id="rejectBtn" style="background:#8B4513;color:#fff;border:none;padding:10px 20px;border-radius:6px;font-weight:bold;cursor:pointer;">Reject</button>
</div>

<form id="formEdit" method="post" action="/edit" style="display:none;">
<input type="hidden" name="id" value="{html.escape(qid)}"/>
</form>
</div>

<script>
(function() {{
  var qid = {json.dumps(qid)};
  function postJSON(url, body) {{
    fetch(url, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body)
    }}).then(function() {{ window.location.href = '/'; }});
  }}
  document.getElementById('approveBtn').addEventListener('click', function() {{
    postJSON('/approve', {{ id: qid }});
  }});
  document.getElementById('rejectBtn').addEventListener('click', function() {{
    if (!confirm('Reject and remove this question from the bank?')) return;
    postJSON('/reject', {{ id: qid }});
  }});
  document.getElementById('formEdit').addEventListener('submit', function(ev) {{
    ev.preventDefault();
    var ans = document.getElementById('answerBox').value;
    postJSON('/edit', {{ id: qid, answer: ans }});
  }});
  document.addEventListener('keydown', function(e) {{
    var t = e.target;
    if (t && (t.tagName === 'TEXTAREA' || t.tagName === 'INPUT')) return;
    if (e.key === 'a' || e.key === 'A') {{ e.preventDefault(); document.getElementById('approveBtn').click(); }}
    if (e.key === 'r' || e.key === 'R') {{ e.preventDefault(); document.getElementById('rejectBtn').click(); }}
  }});
}})();
</script>
"""
    return page_shell(inner)


@app.route("/summary")
def summary() -> str:
    assert _data is not None and _json_path is not None
    log_path = REPO_ROOT / "question-bank" / "verification_fails.log"
    stats = progress_stats(_data, log_path)
    queue = collect_flag_queue(_data)
    done_msg = ""
    if not queue:
        done_msg = '<p style="color:#4CAF50;font-size:1.2em;">All done!</p>'

    inner = f"""
<h1 style="color:#E8650A;">Review summary</h1>
{done_msg}
<ul style="line-height:1.8;font-size:1.05em;">
<li>Approved (review pass): <strong>{stats["approved"]}</strong></li>
<li>Edited (review pass): <strong>{stats["edited"]}</strong></li>
<li>Rejected (removed): <strong>{stats["rejected"]}</strong></li>
<li>Total reviewed (approve + edit + reject): <strong>{stats["processed"]}</strong></li>
<li>Remaining in FLAG queue: <strong>{stats["remaining"]}</strong></li>
</ul>
<p><a href="/" style="color:#E8650A;">Back to review</a></p>
"""
    return page_shell(inner)


@app.route("/approve", methods=["POST"])
def approve() -> Response:
    assert _data is not None and _json_path is not None
    payload = request.get_json(silent=True) or {}
    qid = str(payload.get("id") or "").strip()
    if not qid:
        return Response("missing id", status=400)
    q = find_question_by_id(_data, qid)
    if not q:
        return Response("question not found", status=404)
    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    was_rv = bool(q.get("ryan_verified"))
    v["status"] = "REVIEWED_PASS"
    q["verification"] = v
    q["ryan_verified"] = True
    q["ryan_notes"] = "approved"
    if not was_rv:
        rv = int(_data.get("ryan_verified_count") or 0)
        _data["ryan_verified_count"] = rv + 1
    save_bank(_json_path, _data)
    _session_counts["approved"] += 1
    _log_approval_line(qid)
    return redirect("/", code=303)


@app.route("/edit", methods=["POST"])
def edit() -> Response:
    assert _data is not None and _json_path is not None
    payload = request.get_json(silent=True) or {}
    qid = str(payload.get("id") or "").strip()
    answer = payload.get("answer")
    if answer is None:
        return Response("missing answer", status=400)
    if not qid:
        return Response("missing id", status=400)
    q = find_question_by_id(_data, qid)
    if not q:
        return Response("question not found", status=404)
    original_answer = str(q.get("answer") or "")
    was_rv = bool(q.get("ryan_verified"))
    q["answer"] = str(answer)
    revised_answer = q["answer"]
    v = q.get("verification") if isinstance(q.get("verification"), dict) else {}
    v["status"] = "REVIEWED_PASS"
    q["verification"] = v
    q["ryan_verified"] = True
    q["ryan_notes"] = "edited"
    if not was_rv:
        rv = int(_data.get("ryan_verified_count") or 0)
        _data["ryan_verified_count"] = rv + 1
    save_bank(_json_path, _data)
    _session_counts["edited"] += 1
    _log_edit(q, original_answer, revised_answer)
    return redirect("/", code=303)


@app.route("/reject", methods=["POST"])
def reject() -> Response:
    assert _data is not None and _json_path is not None
    payload = request.get_json(silent=True) or {}
    qid = str(payload.get("id") or "").strip()
    if not qid:
        return Response("missing id", status=400)
    task = find_task_for_question(_data, qid)
    if not task:
        return Response("question not found", status=404)
    q = find_question_by_id(_data, qid)
    if not q:
        return Response("question not found", status=404)
    qs = task.get("questions")
    if not isinstance(qs, list):
        return Response("invalid task", status=500)
    new_qs = [x for x in qs if not (isinstance(x, dict) and x.get("id") == qid)]
    if len(new_qs) == len(qs):
        return Response("question not in task", status=404)
    task["questions"] = new_qs
    log_path = REPO_ROOT / "question-bank" / "verification_fails.log"
    append_ryan_reject_log(log_path, qid)
    _data["total_questions"] = recompute_total_questions(_data)
    save_bank(_json_path, _data)
    _session_counts["rejected"] += 1
    _log_rejection(q)
    return redirect("/", code=303)


def main() -> None:
    global _data, _json_path
    parser = argparse.ArgumentParser(description="Review FLAG questions in the question bank.")
    parser.add_argument(
        "--input",
        default="question-bank/qbank_private_helicopter.json",
        help="Path to question bank JSON (relative to repo root unless absolute)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = REPO_ROOT / in_path
    if not in_path.is_file():
        print(f"ERROR: input file not found: {in_path}", file=sys.stderr)
        raise SystemExit(2)

    _json_path = in_path
    _data = load_bank(in_path)
    queue = collect_flag_queue(_data)
    n = len(queue)
    print(f"FLAG queue: {n} questions loaded. Open http://localhost:{args.port} in your browser.", flush=True)

    _write_session_header()
    atexit.register(_write_session_footer)
    try:
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        _write_session_footer()


if __name__ == "__main__":
    main()
