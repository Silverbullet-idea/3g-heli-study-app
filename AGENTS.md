# 3G Heli Study App — Agent Reference

## Project: 3G Heli Study App

Last updated: 2026-06-10 (Instrument bank verified — 2,334 PASS / 244 FLAG / 6 FAIL; 2,578 on disk)

---

## Current Phase

Phase 1 — Printable / Digital Study Cards (PDF downloads)

Active SKU: Private Pilot Study Sheet — R22 (SKU 1 of 8)

---

## Completed This Session

### Instrument Helicopter question bank verification (2026-06-10)

- **`scripts/verify_question_bank.py --input question-bank/qbank_instrument_helicopter.json`** — Full run completed (~38 min, 259 batches). **2,584** processed → **2,334 PASS** (90.3%), **244 FLAG** (9.4%), **6 FAIL removed** (0.2%). On-disk bank: **2,578** questions. Model: **claude-haiku-4-5-20251001**; system-prompt caching configured (`cache_control: ephemeral`). FLAG rate below 15% — **`diagnose_flags.py` not required**. Next: triage → review server on FLAGs.
- **`qbank_instrument_helicopter.json`** — verification metadata written in place; committed and pushed.

### Instrument Helicopter question bank generation (2026-06-09)

- **`scripts/patch_instrument_acs_item_codes.py`** — Prepended **IH.** codes to all **323** Instrument ACS item lines (ACS JSON had description-only lines, no codes).
- **`scripts/generate_question_bank.py --rating instrument`** — Full run completed (~6.1 h). **12** areas, **27** tasks, **323** ACS API calls, **2,584** questions → `question-bank/qbank_instrument_helicopter.json`. **0** ACS items with 0 questions; **0** API/validation errors. Prompt caching active (`cache_read_input_tokens` on batch 2+). Model: **claude-sonnet-4-6**.
- **`qbank_instrument_helicopter.json`** — committed with `git add -f` (gitignored pattern). Verified 2026-06-10 (see above).
- Legacy pre-patch bank moved to `question-bank/qbank_instrument_helicopter_20260422_legacy.json` (gitignored).

### HI.XVIII.I.K2 regeneration — zero-coverage gap filled (2026-06-09)

- **`scripts/regenerate_cfi_acs_item.py`** — Targeted regen for **HI.XVIII.I.K2** using **`claude-sonnet-4-6`** + same prompt schema as **`generate_question_bank.py`**. **8** questions (**3** basic / **3** intermediate / **2** advanced), IDs **HI.XVIII.I.K2.001–008**. Answers cite **FAA-S-ACS-29 HI.XVIII.I.K2** verbatim (evaluator operational requirement, multiengine OEI task only).
- **Verification** — `verify_question_bank.py --batch-limit 1` on staging: all **8** API-FLAG (Haiku does not recognize **FAA-S-ACS-29**). Triage also ESCALATE ×8. Content validated against repo **`extracted-data/faa/FAA-S-ACS-29_CFI_Helicopter_ACS.json`**; merged with **`local_acs_verified: true`**. Main bank: **9,396** questions (**HI.XVIII.I.K2** = **8**).
- **Rejection themes avoided** — prior rejects failed because answers did not cite the ACS line; new set quotes ACS directly and distinguishes ACS evaluator requirements from 14 CFR / RFM performance data. No accident-rate statistics.
- **`qbank_cfi_helicopter.json`** — committed and pushed at **`question-bank/qbank_cfi_helicopter.json`** (commit `124a221`, **9,396** questions on origin).

### CFI ESCALATE manual review + reject coverage report (2026-06-09)

- **Review server session** — `run_review_server.ps1 --input question-bank/qbank_cfi_helicopter.json` complete. **170** ESCALATE items → **1 EDITED**, **169 REJECTED**. On-disk bank: **9,388** questions, **0** FLAG, **9,387 PASS** + **1 REVIEWED_PASS**.
- **Reject source** — no dedicated `cfi_rejected.json`; rejects parsed from gitignored `question-bank/review_changes.log` (169 FI/HI `--- REJECTED ---` blocks; matches **169** `RYAN_REJECT` lines in `verification_fails.log`).
- **`scripts/analyze_cfi_reject_coverage.py`** — read-only diagnostic; writes **`question_banks/cfi/cfi_reject_coverage_report.txt`**. **138** unique ACS codes rejected; top concentration **HI.XVIII.I.K2** (8 rejects). **Coverage risk:** **1** ACS item with **0** remaining (**HI.XVIII.I.K2**); **0** with only 1 remaining.
- **`qbank_cfi_helicopter.json`** — not committed (gitignored). Next: regenerate or rewrite gap item **HI.XVIII.I.K2** before CFI bank release.

### CFI FLAG pre-triage complete (2026-06-08)

- **`run_triage_cfi.ps1`** — `triage_flag_questions.py --input question-bank/qbank_cfi_helicopter.json` complete (~53 min, 290 batches). **868** FLAGs processed → **17 APPROVE**, **681 EDIT**, **170 ESCALATE**. Automated resolution rate: **80.4%** ((17 + 681) / 868). On-disk bank: **9,557** questions, **170** FLAG remaining (all ESCALATE).
- **Review server** — `run_review_server.ps1 --input question-bank/qbank_cfi_helicopter.json` launched at `http://localhost:5000` for manual review of **170** ESCALATE items. Stop with **Ctrl+C** when queue cleared. ESCALATE review: **in progress** (170 remaining as of triage completion).
- **`qbank_cfi_helicopter.json`** — not committed (gitignored). Do not start rewrite pipeline until ESCALATE manual review is complete.

### CFI question bank verification complete (2026-06-07)

- **`scripts/verify_question_bank.py --input question-bank/qbank_cfi_helicopter.json`** — Full run completed (~2 h, 958 batches). **9,576** questions processed → **8,689 PASS** (90.7%), **868 FLAG** (9.1%), **19 FAIL removed** (0.2%). On-disk bank: **9,557** questions after FAIL removals.
- **API errors:** **1** `[VERIFIER ERROR]` in log (JSON parse on one batch; recovered on retry). **0** API-failure placeholder FLAGs — all **868** FLAGs are genuine Haiku content flags, not rate-limit failures. **`--retry-failures` not needed**; proceed to `triage_flag_questions.py` then review server.
- **`qbank_cfi_helicopter.json`** — not committed (gitignored). Triage complete 2026-06-08; manual ESCALATE review in progress (see above).

### CFI question bank generation complete (2026-06-06)

- **`scripts/patch_cfi_acs_item_codes.py`** — Prepended **FI.** (Area I) / **HI.** (Areas II–XVIII) codes to all **1,197** CFI ACS item lines (2026-06-05).
- **`scripts/generate_question_bank.py --rating cfi`** — Full run completed (~22 h). **18** areas, **87** tasks, **1,197** ACS API calls, **9,576** questions → `question-bank/qbank_cfi_helicopter.json` (gitignored). **0** ACS items with 0 questions; **0** API/validation errors in log.
- **`qbank_cfi_helicopter.json`** — not committed (gitignored). Verification complete 2026-06-07 (see above).

### Rejected-question rewrite pipeline (2026-06-03)

Three-step pipeline for **336** manual rejects logged in local `review_changes.log`:

1. **`scripts/rewrite_rejected_questions.py`** — Parses `--- REJECTED ---` blocks; calls **`claude-sonnet-4-6`** (cached system prompt) to rewrite each answer; writes gitignored **`question-bank/qbank_rewritten_rejects.json`**; checkpoint every 25; errors → `rewrite_errors.log`. CLI: `--dry-run` (parse first 5 blocks, no API).
2. **`scripts/run_rewrite_rejects.ps1`** — Runs the rewriter.
3. **`scripts/run_verify_rejects.ps1`** — `verify_question_bank.py --input question-bank/qbank_rewritten_rejects.json`
4. **`scripts/run_triage_rejects.ps1`** — `triage_flag_questions.py --input question-bank/qbank_rewritten_rejects.json`

**Run order:** rewrite → verify → triage → review server on any remaining FLAGs → merge approved rewrites.

### Retry failed rewrites + merge back to main banks (2026-06-03)

- **`scripts/retry_failed_rewrites.py`** + **`run_retry_failed_rewrites.ps1`** — Re-attempts IDs logged in `rewrite_errors.log` (5 API retries, 3 s sleep); markdown-fence JSON extraction for preamble-wrapped responses; appends successes to `qbank_rewritten_rejects.json`. **All 4 original failures recovered** (332/336 in output bank — remaining 4 are duplicate-ID blocks from review log).
- **`scripts/patch_acs_codes.py`** — Fixes truncated `acs_code` values in gitignored `qbank_rewritten_rejects.json` (Rule B manual overrides, then Rule A auto-derive from question ID); validates all codes match `^[PC]H\.` before save.
- **`scripts/merge_rewritten_questions.py`** + **`run_merge_rewritten.ps1`** / **`run_merge_rewritten_dryrun.ps1`** — Merges questions with `verification.status` PASS or REVIEWED_PASS (and `ryan_verified: false`) into `qbank_private_helicopter.json` (PH.*) or `qbank_commercial_helicopter.json` (CH.*) by ACS task match; `--dry-run` for preview; live run requires typing YES. Unmatched → `merge_unmatched.log`. **Merged 2026-06-03:** 161 private + 100 commercial (261 matched of 299 eligible); banks now **6,526** / **7,016** questions.

### Question bank logs in git (2026-06-02)

- **`question-bank/verification_fails.log`** — committed (verifier FAIL removals + `RYAN_REJECT` index lines from review server).
- **`question-bank/verification_summary.txt`** — committed (last verifier run stats snapshot).
- **`question-bank/review_changes.log`** — **gitignored** (`.gitignore` line 14); local only — full APPROVED / EDITED / REJECTED / triage audit trail; do not force-add.
- **`scripts/run_review_server_commercial.ps1`** — review server wrapper for commercial bank (private wrapper unchanged).

### Private + Commercial FLAG review (2026-06-02)

- **Private** `qbank_private_helicopter.json` — **0** FLAG remaining; manual review queue cleared.
- **Commercial** `qbank_commercial_helicopter.json` — **0** FLAG remaining after triage + manual review (~140 escalated items reviewed).

### ATP ACS + question bank (2026-05-03)

- **ATP Helicopter ACS PDF** — already at `raw-pdfs/faa/FAA-S-ACS-ATP_Helicopter_ACS.pdf`; `extract_poh_json.py --section faa_acs` → **`extracted-data/faa/FAA-S-ACS-ATP_Helicopter_ACS.json`** (11 `areas_of_operation`, 28 tasks, 0 verify flags).
- **`scripts/run_generate_atp.ps1`** — full run: **259** ACS API calls → **`question-bank/qbank_atp_helicopter.json`** with **2,072** questions (gitignored).

### FLAG pre-triage (2026-05-02)

- `scripts/triage_flag_questions.py` — Re-examines each `verification.status == "FLAG"` question (skips rows that already have `verification.triage`) using **`claude-haiku-4-5-20251001`** in batches of **3**; sets `APPROVE` → `PASS` + `triage: AUTO_APPROVE`, `EDIT` → corrected text + `PASS` + `triage: AI_EDIT`, or `ESCALATE` → stays `FLAG` + `triage: ESCALATE` + `triage_note`. Appends tab-prefixed lines to `question-bank/review_changes.log`; unparseable API responses go to `question-bank/triage_errors.log`; overwrites `question-bank/triage_summary.txt` each run; saves JSON every **10** batches. CLI: `--input` (required), `--batch-limit N` for testing.
- `scripts/run_triage_private.ps1` — `triage_flag_questions.py --input question-bank/qbank_private_helicopter.json`
- `scripts/run_triage_commercial.ps1` — same for `qbank_commercial_helicopter.json`. Run **before** the review server to shrink the manual FLAG queue (expect a large share of FLAGs cleared automatically; **ESCALATE** remains for expert review).

### Housekeeping (2026-05-02)

- `scripts/verify_question_bank.py` — removed unused top-level `MODEL_ID = "claude-sonnet-4-6"` (dead code; `call_verifier_api()` already hardcodes `claude-haiku-4-5-20251001`).

### R44 Section 7 systems JSON (2026-04-22)

- `scripts/extract_poh_json.py` — `--pdf raw-pdfs/robinson/r44_poh_7_f5e97cee3e.pdf` `--section r44_systems` → `extracted-data/aircraft/r44_systems.json`
- **33** top-level entries under `systems` (POH Section 7); **0** `confidence: verify` flags in model output
- Source PDF: 36 pages; metadata `extracted_date` **2026-04-22**

### Question bank pipeline — PowerShell wrappers (2026-04-22)

Added:

- `scripts/run_verify_commercial.ps1` — `verify_question_bank.py --input question-bank/qbank_commercial_helicopter.json`. (`verify_question_bank.py` has **no** `--rating` flag; use `--input` to select the bank.)
- `scripts/run_generate_instrument.ps1` — `generate_question_bank.py --rating instrument`, then an inline Python count on `qbank_instrument_helicopter.json` (private’s `verify_private_question_count.py` is private-only).
- `scripts/run_generate_cfi.ps1` — `--rating cfi`; first-line comment: overnight-scale cost — **do not run casually** (wrapper only in this session).
- `scripts/run_generate_atp.ps1` — `--rating atp`; first-line comment: short/low-cost — **wrapper only** in this session.

**Instrument generation complete (2026-06-09):** `run_generate_instrument.ps1` / `--rating instrument` → **2,584** questions; ACS patched with **IH.** codes first. Verification pending.

### Full Private question bank (2026-04-14)

- `scripts/run_generate_private.ps1` — full `--rating private` run (~13.7 h). Output: 16 areas, 57 tasks, 760 ACS API calls; `verify_private_question_count.py` total **6,744** questions — **PASS** (≥ 4,800). JSON remains gitignored.

### Question bank verifier (batched API) — built, not yet run

- `scripts/verify_question_bank.py` — processes `question-bank/qbank_private_helicopter.json` in batches of 10 via **`claude-haiku-4-5-20251001`** (`call_verifier_api()`); writes `verification` on each question (PASS/FLAG) or removes FAIL rows and appends to `question-bank/verification_fails.log`; overwrites `question-bank/verification_summary.txt` each run.
- `scripts/run_verify_private.ps1` — wrapper: `.\.venv\Scripts\python.exe scripts\verify_question_bank.py --input question-bank/qbank_private_helicopter.json`
- Ryan to review before first run (large API usage; updates JSON in place).

### FLAG question review (local Flask)

- `scripts/review_server.py` — serves `http://localhost:5000`; queues questions with `verification.status == "FLAG"` (lowest confidence first); Approve / Save Edit / Reject writes UTF-8 JSON in place; rejects append `RYAN_REJECT\t…` to `verification_fails.log` and full `--- REJECTED ---` blocks to `review_changes.log` (gitignored).
- `scripts/run_review_server.ps1` — forwards `@args` to `review_server.py` (e.g. `--input question-bank/qbank_rewritten_rejects.json`; default input is private bank). `scripts/run_review_server_commercial.ps1` — commercial bank shortcut. Requires Flask in `.venv`.

### Question-bank log files (git)

| File | Tracked in git? | Purpose |
|------|-----------------|--------|
| `verification_fails.log` | **Yes** | Verifier FAIL removals (`timestamp\tid\treason`) + manual `RYAN_REJECT` lines |
| `verification_summary.txt` | **Yes** | Last verifier run totals (overwritten each verify run) |
| `review_changes.log` | **No** (gitignored) | Session audit: approvals, edits, rejections, triage lines |
| `triage_summary.txt` | No (untracked) | Last triage run stats (overwritten each triage run) |
| `qbank_*.json` | No (gitignored) | Generated banks until Ryan releases a copy |

### Data Extraction Pipeline

- scripts/extract_text.py — pdfplumber raw text extraction; optional `--output` (repo-relative path); default `extracted-data/raw-text/<pdf_stem>.txt`
- scripts/extract_poh_json.py — Anthropic API structured JSON extraction; use `--pdf` **or** `--input` (pre-extracted UTF-8 text), plus `--output` and `--aircraft` for non-R22/R44 targets (prompt replaces “Robinson R22/R44” with the given label)
- scripts/run_r22_full_extract.ps1 — runs all three R22 sections
- scripts/run_faa_r44_extract.ps1 — FAA handbooks + ACS + R44 (batch runner; in repo)
- scripts/run_expanded_library.ps1 — engine manuals, PHAK, AIM, ACs

### extract_poh_json.py — section routing (2026-04-11)

Eight `--section` values: `limitations`, `emergency_procedures`, `systems` (R22 →
`extracted-data/aircraft/r22_*.json`); `r44_limitations`, `r44_emergency_procedures`,
`r44_systems` (R44 → `extracted-data/aircraft/r44_*.json`); `faa_handbook`, `faa_acs`
(FAA → `extracted-data/faa/<pdf_stem>.json`). FAA PDFs use chunked streaming extraction
when the source is large; POH sections use streaming for long-output requests.

### Extracted JSON — R22 (verified, committed)

- extracted-data/aircraft/r22_limitations.json (9 top-level groups after merge, 1 verify)
- extracted-data/aircraft/r22_emergency_procedures.json (17 procedures, 0 verify)
- extracted-data/aircraft/r22_systems.json (28 systems, 0 verify)

### Extracted JSON — FAA + R44 (on disk; Ryan review before git add)

Present locally under `extracted-data/faa/` and `extracted-data/aircraft/`:

| File | Records (approx.) | Verify flags |
|------|-------------------|--------------|
| aircraft/r44_limitations.json | 8 | 0 |
| aircraft/r44_emergency_procedures.json | 17 | 0 |
| aircraft/r44_systems.json | 33 (`systems` keys) | 0 |
| faa/FAA-H-8083-21B_Helicopter_Flying_Handbook.json | 7 topics | 0 |
| faa/FAA-H-8083-4_Helicopter_Instructors_Handbook.json | 21 | 0 |
| faa/FAA-H-8083-15B_Instrument_Flying_Handbook.json | 84 | 1 |
| faa/FAA-H-8083-1B_Weight_Balance_Handbook.json | 5 | 0 |
| faa/FAA-S-ACS-15_Private_Helicopter_ACS.json | 14 areas | 0 |
| faa/FAA-S-ACS-16_Commercial_Helicopter_ACS.json | 14 areas | 0 |
| faa/FAA-S-ACS-14_Instrument_Helicopter_ACS.json | 12 areas, 323 ACS items (IH. codes patched 2026-06-09) | 0 |
| faa/FAA-S-ACS-ATP_Helicopter_ACS.json | 11 areas | 0 |
| faa/FAA-S-ACS-29_CFI_Helicopter_ACS.json | 18 areas | 1 |

(`r44_systems.json` completed 2026-04-22; CFI ACS extracted 2026-06-05 — 6 PDF chunks, 85 pages, 87 tasks, 1,197 ACS items.)

### Extracted JSON — R66, Bell 206B3, Bell 407 (2026-04-14, committed)

Sources: R66 section PDFs (`r66_poh_section2_limitations.pdf`, `r66_poh_section3_emergency_procedures.pdf`, `r66_poh_section7_systems.pdf`); Bell `bell_206b3_fm_1.pdf`; Bell `BHT-407-FM-1.pdf`. Intermediate text (optional, local): `raw-text/r66_section2|3|7.txt`, `raw-text/b206_full.txt`, `raw-text/b407_full.txt`.

| File | Procedures | Systems sections | Limitation top-level groups | Verify flags | Notes |
|------|------------|------------------|-----------------------------|--------------|--------|
| aircraft/r66_limitations.json | — | — | 9 | 7 | 2× `confidence: inferred` in nested fields |
| aircraft/r66_emergency_procedures.json | 21 | — | — | 0 | — |
| aircraft/r66_systems.json | — | 32 | — | 0 | — |
| aircraft/b206_limitations.json | — | — | 9 | 8 | 1× inferred |
| aircraft/b206_emergency_procedures.json | 47 | — | — | 0 | Full FM single-pass |
| aircraft/b206_systems.json | — | 24 | — | 0 | — |
| aircraft/b407_limitations.json | — | — | 9 | 8 | 1× inferred |
| aircraft/b407_emergency_procedures.json | 27 | — | — | 0 | Full FM single-pass |
| aircraft/b407_systems.json | — | 22 | — | 0 | — |

No `confidence: low` strings in any of the nine files. **H125** extraction not started — confirm these outputs before expanding.

### PDF Library (local only — gitignored)

Robinson:

- raw-pdfs/robinson/ — R22, R44, R44 II, R44 Cadet, R66
  Sections 2, 3, 7 + full POHs + checklists (25 files)
- raw-pdfs/robinson/maintenance-manuals/
  - R22_MM_Revision_NOV2024.pdf (downloaded)
  - R22/R44 full MM — 404 (Robinson does not publish freely)

Bell:

- raw-pdfs/bell/ — 17 files including:
  Bell 206B-3 FM, Bell 206L, Bell 205, Bell 212 series,
  Bell 407, Bell 505 (specs, TCDS, checklists, MMEL)
  Know_your_PT6A.pdf
- Bell 505 RFM — SKIPPED (copyright flag, pdfcoffee.com)

Airbus:

- raw-pdfs/airbus/ — EC120B, EC120, EC130B4, AS365 N3 (5 files)

AgustaWestland:

- raw-pdfs/agustawestland/ — AW139 Flight Manual (1 file)

MD Helicopters:

- raw-pdfs/md_helicopters/ — MD500D (1 file)

Engines:

- raw-pdfs/engines/
  - Lycoming O-320 Operator's Manual (downloaded)
  - Lycoming Direct Drive Overhaul Manual (downloaded)
  - Lycoming O-360, O-540, IO-540 — 404 (find URLs at lycoming.com)

FAA:

- raw-pdfs/faa/
  - FAA-H-8083-21B Helicopter Flying Handbook (existing)
  - FAA-H-8083-4 Helicopter Instructor Handbook (existing)
  - FAA-H-8083-15B Instrument Flying Handbook (existing)
  - FAA-H-8083-1B Weight Balance Handbook (existing)
  - FAA-H-8083-25C PHAK (downloaded)
  - FAA-H-8083-16B Instrument Procedures Handbook (downloaded)
  - FAA_AIM_2024.pdf (downloaded)
  - ACS: Private, Commercial, CFI, Instrument Helicopter (existing)
  - **ATP Helicopter ACS** — `FAA-S-ACS-ATP_Helicopter_ACS.pdf` in `raw-pdfs/faa/`
    (local, pre-release copy from Ryan's archive; not in public FAA set yet)
- raw-pdfs/faa/advisory-circulars/
  - AC_00-6B Aviation Weather (downloaded)
  - AC_61-67D, AC_91-13D — DNS failure on rgl.faa.gov (retry later)

### Project documentation (2026-04-11)

- **AGENTS.md** — Added at repo root, committed, and pushed. Single source for phase,
  pipeline inventory, PDF library notes, next steps, open items, and agent rules.

### Question bank generation pipeline (2026-04-11)

- `scripts/generate_question_bank.py` — Loads ACS JSON + FAA handbook JSON, matches
  handbook topics by keyword to each ACS task, calls Anthropic (`claude-sonnet-4-6`)
  with a fixed system prompt, and writes `question-bank/qbank_{rating}_helicopter.json`
  (8 questions per task: 3 basic / 3 intermediate / 2 advanced). Merge-safe: existing
  non-empty task question lists are preserved so runs can resume after interruption.
- **Output encoding:** `json.dump(..., ensure_ascii=False)` writes real UTF-8 characters
  (apostrophes, quotes, em dashes) instead of `\\u0027`-style escapes; file open uses
  `encoding="utf-8"` so Windows does not mangle extended characters.
- **BasicMed accuracy:** System prompt includes explicit 14 CFR Part 68 / 61.113(i)
  limits (e.g. 12,500 lb certificated takeoff weight — not legacy 6,000 lb training-data
  values). **Area I** in `qbank_private_helicopter.json` was cleared for regeneration
  with these fixes applied (other areas unchanged).
- `scripts/run_generate_private.ps1` — Convenience runner for `--rating private`.
- `question-bank/` — Holds generated banks; `qbank_*.json` is gitignored until Ryan
  verifies and commits a release copy manually. `.gitkeep` keeps the folder in git.
  Verification/reject logs: see **Question-bank log files (git)** above.

**Area I test run (Private):** Pipeline executed (`--rating private --area I`); all
tasks failed with Anthropic “credit balance too low” (0 questions written). After
billing is replenished, re-run the same command to fill Area I, then run without
`--area` for the full bank. Full generation pending Ryan review.

---

## Next Steps (in order)

1. **CFI question bank complete** — **9,576** questions (1,197 ACS items × 8/q); verify next via `verify_question_bank.py --input question-bank/qbank_cfi_helicopter.json`.
   **ATP ACS extraction is complete** (`FAA-S-ACS-ATP_Helicopter_ACS.json`,
   2026-05-03); **`qbank_atp_helicopter.json`** generated with **2,072** questions (259 ACS items × 8/q).
   **`r44_systems.json` is current as of 2026-04-22.**
2. Replenish credits and run `scripts/generate_question_bank.py --rating private --area I`
   to validate question output; then full private bank without `--area` after review
3. Review verify flag counts across all extracted JSON (summary in table above)
4. Commit extracted JSON files after review
5. Build PDF renderer — reads JSON, outputs branded 8.5x11 study sheets
6. Produce first complete study sheet set: Private Pilot R22

---

## Open Items / Blocked

- Anthropic API — credit balance hit zero mid-batch (2026-04-11); complete missing
  extractions when billing allows
- Lycoming O-360 (60297-12), O-540 (60297-14), IO-540 (60297-15)
  → Find current URLs at lycoming.com/publications
- AC 61-67D, AC 91-13D
  → rgl.faa.gov DNS issue — try from different network
- Robinson R22/R44 full maintenance manuals
  → Not published freely. Consider purchasing subscription from
    robinsonheli.com if MM content is needed for study sheets.
- Bell 505 RFM
  → Copyright flagged. Do not download from pdfcoffee.com.
    Contact Bell or use EASA TCDS + spec sheet for study content.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| extract_text.py | PDF → raw text |
| extract_poh_json.py | raw text → structured JSON via API |
| generate_question_bank.py | ACS + handbook JSON → oral exam question bank (Anthropic) |
| patch_cfi_acs_item_codes.py | Prepends FI./HI. codes to CFI ACS JSON item lines (one-time post-extract fix) |
| run_generate_private.ps1 | Runs `generate_question_bank.py --rating private` |
| run_verify_private.ps1 | Runs `verify_question_bank.py --input question-bank/qbank_private_helicopter.json` |
| run_verify_commercial.ps1 | Verifies `qbank_commercial_helicopter.json` via `verify_question_bank.py --input …` |
| triage_flag_questions.py | Pre-triage FLAG rows via Haiku (APPROVE / EDIT / ESCALATE); updates `verification` in place; `--input` required |
| run_triage_private.ps1 | Runs `triage_flag_questions.py --input question-bank/qbank_private_helicopter.json` |
| run_triage_commercial.ps1 | Runs `triage_flag_questions.py --input question-bank/qbank_commercial_helicopter.json` |
| run_triage_cfi.ps1 | Runs `triage_flag_questions.py --input question-bank/qbank_cfi_helicopter.json` |
| run_triage_atp.ps1 | Runs `triage_flag_questions.py --input question-bank/qbank_atp_helicopter.json` |
| rewrite_rejected_questions.py | Parses `review_changes.log` rejects; rewrites via Sonnet → `qbank_rewritten_rejects.json`; `--dry-run` |
| run_rewrite_rejects.ps1 | Runs `rewrite_rejected_questions.py` |
| run_verify_rejects.ps1 | Verifies `qbank_rewritten_rejects.json` via `verify_question_bank.py --input …` |
| run_triage_rejects.ps1 | Pre-triages rewritten rejects bank via `triage_flag_questions.py --input …` |
| run_generate_instrument.ps1 | Generates `qbank_instrument_helicopter.json` (`--rating instrument`) + count |
| run_generate_cfi.ps1 | Generates CFI bank — overnight-scale; see script header |
| run_generate_atp.ps1 | Generates ATP bank — short; see script header |
| run_r22_full_extract.ps1 | R22 Sec 2, 3, 7 extraction |
| run_faa_r44_extract.ps1 | FAA handbooks + ACS + R44 extraction |
| run_expanded_library.ps1 | Engine manuals, PHAK, AIM, ACs download |
| populate_pdf_library.py | Download manager for all PDF sources |

---

## Agent Instructions (READ EVERY SESSION)

1. Read this file before starting any task
2. Check Next Steps — do not re-open completed items
3. Check Open Items — flag if a task depends on a blocked item
4. After completing any task, update the relevant section of this file
5. After completing any task, update `docs/LIBRARY_INDEX.md` if PDFs were
   added or moved
6. Never commit PDF files — they are gitignored by design
7. Never hard-delete extracted JSON — these are verified source data
8. Use `.venv\Scripts\python.exe` — never bare python
