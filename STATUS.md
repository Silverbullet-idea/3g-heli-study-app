# STATUS.md — 3G Heli Study App
### Fast-moving session tracker — updated at the end of every agent session

---

### Last Updated
June 3, 2026 — Rejected-question rewrite pipeline ready (rewrite → verify → triage); not yet run

---

### Current Sprint Goal
Verify remaining banks (CFI, Instrument, ATP); run **336-question reject rewrite pipeline**; render and ship first **Private R22** PDF study sheet set (Phase 1 SKU 1).

---

### Completed (This Sprint)

- **Rejected-question rewrite pipeline** — `rewrite_rejected_questions.py` + `run_rewrite_rejects.ps1`, `run_verify_rejects.ps1`, `run_triage_rejects.ps1` (2026-06-03); dry-run parses **336** blocks; full run pending
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

**On-disk banks (2026-06-02):**

| Bank | Questions | FLAG |
|------|-----------|------|
| Private | 6,365 | 0 |
| Commercial | 6,916 | 0 |
| CFI | 13,568 | (not verified) |
| Instrument | 2,584 | (not verified) |
| ATP | 2,072 | (not verified) |

---

### In Progress

- **336 rejected questions** — rewrite pipeline built; awaiting `run_rewrite_rejects.ps1` → verify → triage

---

### Up Next (Prioritized)

1. Run **rewrite → verify → triage** on rejected questions (`run_rewrite_rejects.ps1`, then `run_verify_rejects.ps1`, then `run_triage_rejects.ps1`)
2. Run **verification** on Instrument, then ATP, then CFI (`verify_question_bank.py --input …`)
3. **Pre-triage** + manual review any new FLAGs per bank
4. **Build Phase 1 PDF output** — `render_study_sheet.py` → Private R22 study sheet set
5. Confirm **`FAA-S-ACS-29_CFI_Helicopter_ACS.json`** completeness if needed
6. Resolve Lycoming O-360 / O-540 / IO-540 manual URLs
7. Resolve `rgl.faa.gov` DNS issue — AC 61-67D and AC 91-13D blocked

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
- [ ] Commit STATUS.md: `git add STATUS.md && git commit -m "chore: update STATUS.md — [one-line summary]" && git push`
