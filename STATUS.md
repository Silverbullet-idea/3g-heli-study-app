# STATUS.md — 3G Heli Study App
### Fast-moving session tracker — updated at the end of every agent session

---

### Last Updated
June 3, 2026 — Retry-failed-rewrites + merge scripts added; rewrite pipeline complete (329/336 in output bank)

---

### Current Sprint Goal
Verify remaining banks (CFI, Instrument, ATP); finish **3 remaining failed rewrite retries**; run merge after review; render and ship first **Private R22** PDF study sheet set (Phase 1 SKU 1).

---

### Completed (This Sprint)

- **Retry + merge scripts** — `retry_failed_rewrites.py`, `merge_rewritten_questions.py`, PowerShell wrappers (2026-06-03); merge script ready for post-review use
- **Rejected-question rewrite pipeline** — **329** of **336** rewrites in `qbank_rewritten_rejects.json` (328 original + 1 retry recovery); verify + triage run complete
- **Rejected-question rewrite pipeline** — `rewrite_rejected_questions.py` + `run_rewrite_rejects.ps1`, `run_verify_rejects.ps1`, `run_triage_rejects.ps1` (2026-06-03)
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

- **3 failed rewrite retries** — `PH.XV.B.RM.003` (2nd block), `PH.IV.C.006`, `PH.VI.F.RM.002` still failing JSON parse (API returns preamble + markdown fence); re-run `run_retry_failed_rewrites.ps1` or manual fix

---

### Up Next (Prioritized)

1. Resolve **3 remaining rewrite failures** (API returns JSON inside markdown with preamble — may need prompt tweak or manual extraction)
2. **Review** rewritten rejects in review server; approve PASS items
3. **Merge** approved rewrites into main banks (`run_merge_rewritten_dryrun.ps1` first, then `run_merge_rewritten.ps1`)
4. Run **verification** on Instrument, then ATP, then CFI (`verify_question_bank.py --input …`)
5. **Pre-triage** + manual review any new FLAGs per bank
6. **Build Phase 1 PDF output** — `render_study_sheet.py` → Private R22 study sheet set
7. Confirm **`FAA-S-ACS-29_CFI_Helicopter_ACS.json`** completeness if needed
8. Resolve Lycoming O-360 / O-540 / IO-540 manual URLs
9. Resolve `rgl.faa.gov` DNS issue — AC 61-67D and AC 91-13D blocked

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
