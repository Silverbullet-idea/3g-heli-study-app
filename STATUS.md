# STATUS.md — 3G Heli Study App
### Fast-moving session tracker — updated at the end of every agent session

---

### Last Updated
May 2, 2026 — Initialized project knowledge files (`CONTEXT.md`, `STATUS.md`); reconciled question-bank counts and `verification_summary.txt` against on-disk JSON

---

### Current Sprint Goal
Complete question bank generation and verification runs; work through Private FLAG review; render and ship first **Private R22** PDF study sheet set (Phase 1 SKU 1).

---

### Completed (This Sprint)

- **`CONTEXT.md` and `STATUS.md` added** at repo root — project knowledge system initialized (2026-05-02)
- **`r44_systems.json` regenerated** — 33 systems sections, 0 `confidence: verify` flags per `AGENTS.md` (2026-04-22)
- **PowerShell wrappers present:** `run_verify_commercial.ps1`, `run_generate_instrument.ps1`, `run_generate_cfi.ps1` (overnight-scale caution in script), `run_generate_atp.ps1` (low-cost caution in script)
- **On-disk question banks (parsed 2026-05-02):**
  - `qbank_private_helicopter.json` — **6,396** questions; **521** with `verification.status == "FLAG"`
  - `qbank_commercial_helicopter.json` — **7,042** questions; **694** FLAG
  - `qbank_instrument_helicopter.json` — **2,584** questions; **0** FLAG (likely not yet verified)
- **`question-bank\verification_summary.txt`:** `total_processed: 7071`, `pass: 6361`, `flag: 696`, `fail_removed: 14` (timestamp **2026-04-22T18:05:40Z**)
- **`review_server.py` + `review_changes.log`** — log shows review activity from **2026-04-17** onward (APPROVED / EDITED / REJECTED entries)
- **Prompt caching** — `cache_control` / ephemeral blocks confirmed in `generate_question_bank.py` and verifier (`verify_question_bank.py`)

*Not verified on disk this session:* `.env` 401 fix (2026-04-22); “Commercial verification first batch all PASS”; exact Commercial generation date “2026-04-19”; historical claim “6,728 private / 480 FLAG queue” — superseded by counts above.

---

### In Progress

- **Private FLAG review** — **521** FLAG rows in current `qbank_private_helicopter.json`; use `run_review_server.ps1` → `http://localhost:5000` (default `--input` private bank)
- **Commercial verification / Instrument generation** — `AGENTS.md` (2026-04-22) reported runs **started**; whether processes are **still active today** not verified ?

---

### Up Next (Prioritized)

1. Continue Private FLAG review until queue clears (Ryan / review server)
2. Run or resume **Commercial** verification and **Instrument** generation to completion; then verify Instrument bank
3. Run **CFI** generation when ready — `.\scripts\run_generate_cfi.ps1` (~858 ACS items — cost per `AGENTS.md` / script notes ?)
4. Run **ATP** generation — `.\scripts\run_generate_atp.ps1` (~small ACS set per planning)
5. Verify Commercial, Instrument, CFI, ATP banks after generation complete
6. **Build Phase 1 PDF output** — `render_study_sheet.py` against R22 extracted JSON → Private R22 study sheet set
7. **ATP ACS JSON extraction** — no `FAA-S-ACS-*ATP*` JSON under `extracted-data\faa\` on disk (ATP ACS PDF noted in `docs\LIBRARY_INDEX.md` / library)
8. Confirm **`FAA-S-ACS-29_CFI_Helicopter_ACS.json`** completeness vs any outstanding “pending re-run” notes in `AGENTS.md` (file **exists** with `areas_of_operation` populated — 2026-04-11 extract)
9. Resolve Lycoming O-360 / O-540 / IO-540 manual URLs (`lycoming.com/publications` 404s per `AGENTS.md`)
10. Resolve `rgl.faa.gov` DNS issue — AC 61-67D and AC 91-13D blocked

---

### Open Decisions

- **R44 Raven I vs Raven II — separate SKUs or combined?** Limitations differ between variants; affects study sheet structure and SKU count. Ryan to decide before R44 renderer work begins.
- **PDF renderer approach** — ReportLab (in `.venv`, `render_study_sheet.py` present) vs HTML-to-PDF (e.g. WeasyPrint). Confirm before changing approach.
- **Additional topics beyond existing STUDY_SHEET_MASTER content?** Ryan to confirm if any subject areas are missing before renderer is built out fully.
- **Mock Checkride session block pricing** — confirm exact size and price after beta token cost data is collected.

---

### Blockers

- **ATP ACS JSON** — not present under `extracted-data\faa\` (extraction/run pending)
- **Lycoming engine manual URLs** returning 404 — O-360, O-540, IO-540 not yet in library (`AGENTS.md`)
- **`rgl.faa.gov` DNS issue** — blocks AC 61-67D and AC 91-13D Advisory Circulars

---

### Recent Pivots

- Verification implementation uses **`claude-haiku-4-5-20251001`** for batched calls (see `verify_question_bank.py`); cost vs Sonnet — operational choice
- Generator iterates **ACS item lines** (K/R/S), not whole tasks only — fixes ~392-question ceiling

---

### Session Exit Checklist
At the end of every future session, the active agent must:
- [ ] Update "Completed" with anything finished this session (with date)
- [ ] Update "In Progress" — remove completed items, add newly started items
- [ ] Re-prioritize "Up Next" based on what was learned this session
- [ ] Log any new Open Decisions or Blockers
- [ ] Update "Last Updated" with today's date and a one-line session summary
- [ ] Commit STATUS.md: `git add STATUS.md && git commit -m "chore: update STATUS.md — [one-line summary]" && git push`
