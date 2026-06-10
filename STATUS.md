# STATUS.md — 3G Heli Study App
### Fast-moving session tracker — updated at the end of every agent session

---

### Last Updated
June 10, 2026 — Question bank pipeline **COMPLETE** (4 of 5 ratings; ATP deferred). Next: Phase 1 PDF renderer.

---

### Git / Remote
**Local `main` is in sync with `origin/main`**. Instrument bank manual-review commit pushed 2026-06-10.

### Current Sprint Goal
Build Phase 1 PDF renderer — **Private Pilot Study Sheet — R22** (SKU 1 of 8).

### Question Bank Pipeline
**COMPLETE** — 4 of 5 ratings final (Private, Commercial, CFI, Instrument). **ATP deferred** (no FAA Helicopter ATP ACS). Phase 3 question banks ready for UI development when Phase 1 complete.

---

### Completed (This Sprint)

- **Question bank pipeline — COMPLETE** — 4 of 5 ratings final; ATP deferred (no Helicopter ATP ACS). Phase 3 banks ready for UI when Phase 1 ships (2026-06-10)
- **Instrument Helicopter question bank — COMPLETE** — generate → verify → triage → manual review → reject coverage → commit (2026-06-09–10). Final bank **2,530** questions, **0** FLAG; committed and pushed. **`analyze_instrument_reject_coverage.py`** → **`question-bank/instrument/instrument_reject_coverage_report.txt`**
- **Instrument Helicopter FLAG pre-triage** — `triage_flag_questions.py --input qbank_instrument_helicopter.json` complete (~17 min). **244** FLAGs → **9 APPROVE**, **186 EDIT**, **49 ESCALATE**; **79.9%** automated resolution. **49** FLAG remaining. Next: review server (2026-06-10)
- **Instrument Helicopter question bank verification** — `verify_question_bank.py --input qbank_instrument_helicopter.json` complete (~38 min). **2,584** processed → **2,334 PASS** (90.3%), **244 FLAG** (9.4%), **6 FAIL removed** (0.2%); **2,578** on disk. Next: triage → review server (2026-06-10)
- **Instrument Helicopter question bank generation** — `patch_instrument_acs_item_codes.py` + `generate_question_bank.py --rating instrument` complete (~6.1 h). **323** ACS API calls → **`qbank_instrument_helicopter.json`** with **2,584** questions; **0** items with 0 questions; **0** errors. Committed (2026-06-09)
- **HI.XVIII.I.K2 regeneration** — `regenerate_cfi_acs_item.py` → **8** new questions merged; **HI.XVIII.I.K2** coverage restored (**8** in bank). Bank **9,396** questions, **0** FLAG (2026-06-09)
- **CFI ESCALATE manual review** — review server session complete (2026-06-09). **170** ESCALATE items → **1 EDITED**, **169 REJECTED**; bank was **9,388** before regen. **`scripts/analyze_cfi_reject_coverage.py`** → **`question_banks/cfi/cfi_reject_coverage_report.txt`**
- **CFI FLAG pre-triage** — `run_triage_cfi.ps1` complete (~53 min). **868** FLAGs → **17 APPROVE**, **681 EDIT**, **170 ESCALATE**; **80.4%** automated resolution. Review server launched for ESCALATE queue (2026-06-08)
- **CFI question bank verification** — `verify_question_bank.py --input qbank_cfi_helicopter.json` complete (~2 h). **9,576** processed → **8,689 PASS** (90.7%), **868 FLAG** (9.1%), **19 FAIL removed** (0.2%); **9,557** on disk. **0** API-failure placeholder FLAGs (all genuine content flags); **1** API parse error (recovered). Next: triage → review server (2026-06-07)
- **CFI Helicopter ACS extraction** — PDF at `raw-pdfs/faa/FAA-S-ACS-29_CFI_Helicopter_ACS.pdf`; `extract_poh_json.py --section faa_acs` → **`extracted-data/faa/FAA-S-ACS-29_CFI_Helicopter_ACS.json`** (18 areas, 87 tasks, 1,197 ACS items, 1 verify flag; gitignored) (2026-06-05)
- **CFI question bank generation** — `generate_question_bank.py --rating cfi` complete (~22 h). **1,197** ACS API calls → **`qbank_cfi_helicopter.json`** with **9,576** questions; **0** items with 0 questions; **0** errors (2026-06-06)
- **CFI ACS item code patch** — `patch_cfi_acs_item_codes.py` prepended **FI.** (Area I) / **HI.** (Areas II+) to all 1,197 item lines (2026-06-05)
- **ACS patch + merge** — `patch_acs_codes.py` fixed 177 truncated codes; merged **261** rewrites (161 private, 100 commercial); banks **6,526** / **7,016** (2026-06-03)
- **Retry fence extraction fix** — all 4 API failures recovered; **332** questions in `qbank_rewritten_rejects.json` covering all **336** reject blocks (2026-06-03)
- **Retry + merge scripts** — `retry_failed_rewrites.py`, `merge_rewritten_questions.py`, `patch_acs_codes.py`, PowerShell wrappers (2026-06-03)
- **Rejected-question rewrite pipeline** — verify + triage complete (2026-06-03)
- **Private + Commercial FLAG manual review** — both banks at **0** FLAG (2026-06-02)
- **`question-bank/verification_fails.log`** and **`verification_summary.txt`** — committed and pushed (2026-06-02)
- **`run_review_server_commercial.ps1`** — commercial review server wrapper (2026-06-02)
- **`CONTEXT.md` and `STATUS.md` added** at repo root — project knowledge system initialized (2026-05-02)
- **`r44_systems.json` regenerated** — 33 systems sections, 0 `confidence: verify` flags per `AGENTS.md` (2026-04-22)
- **PowerShell wrappers:** `run_verify_commercial.ps1`, `run_generate_instrument.ps1`, `run_generate_cfi.ps1`, `run_generate_atp.ps1`
- **`run_triage_cfi.ps1` / `run_triage_atp.ps1`** — FLAG pre-triage wrappers (2026-05-03)
- **ATP Helicopter ACS** + **`qbank_atp_helicopter.json`** — **2,072** questions (2026-05-03); bank gitignored
- **FLAG pre-triage** (`triage_flag_questions.py`) — private + commercial runs (2026-05-02)
- **`review_server.py`** — used for private + commercial manual review; activity in local `review_changes.log` (gitignored)

**Final question banks (2026-06-10):**

| Bank | Questions | FLAG | Status |
|------|-----------|------|--------|
| Private | 6,526 | 0 | ✅ Complete |
| Commercial | 7,016 | 0 | ✅ Complete |
| CFI | 9,396 | 0 | ✅ Complete |
| Instrument | 2,530 | 0 | ✅ Complete |
| ATP | — | — | 🔲 Deferred (no ACS) |

---

### In Progress

_(none)_

---

### Up Next (Prioritized)

1. **Build Phase 1 PDF renderer** — `render_study_sheet.py` → Private R22 study sheet set ($9.97)
2. Resolve Lycoming O-360 / O-540 / IO-540 manual URLs
3. Resolve `rgl.faa.gov` DNS issue — AC 61-67D and AC 91-13D blocked
4. Monitor FAA ACS page for Helicopter ATP ACS release (ATP bank deferred)

---

### Open Decisions

- **R44 Raven I vs Raven II — separate SKUs or combined?**
- **PDF renderer approach** — ReportLab vs HTML-to-PDF (WeasyPrint)
- **Additional topics beyond STUDY_SHEET_MASTER?**
- **Mock Checkride session block pricing** — after beta token cost data

---

### Blockers

- **Lycoming engine manual URLs** returning 404
- **`rgl.faa.gov` DNS issue** — blocks AC 61-67D and AC 91-13D

---

### Recent Pivots

- **`review_changes.log` stays gitignored** — full review audit local only; `verification_fails.log` is the committed reject index
- Verification uses **`claude-haiku-4-5-20251001`** for batched calls

---

### Session Exit Checklist
At the end of every future session, the active agent must:
- [x] Update "Completed" with anything finished this session (with date)
- [x] Update "In Progress" — remove completed items, add newly started items
- [x] Re-prioritize "Up Next" based on what was learned this session
- [ ] Log any new Open Decisions or Blockers
- [x] Update "Last Updated" with today's date and a one-line session summary
- [x] Commit STATUS.md: `git add STATUS.md && git commit -m "chore: update STATUS.md — [one-line summary]" && git push`
