# 3G Heli Study App — Agent Reference

## Project: 3G Heli Study App

Last updated: 2026-04-11 (ATP Helicopter ACS pipeline + library index)

---

## Current Phase

Phase 1 — Printable / Digital Study Cards (PDF downloads)

Active SKU: Private Pilot Study Sheet — R22 (SKU 1 of 8)

---

## Completed This Session

### Data Extraction Pipeline

- scripts/extract_text.py — pdfplumber raw text extraction
- scripts/extract_poh_json.py — Anthropic API structured JSON extraction
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
| faa/FAA-H-8083-21B_Helicopter_Flying_Handbook.json | 7 topics | 0 |
| faa/FAA-H-8083-4_Helicopter_Instructors_Handbook.json | 21 | 0 |
| faa/FAA-H-8083-15B_Instrument_Flying_Handbook.json | 84 | 1 |
| faa/FAA-H-8083-1B_Weight_Balance_Handbook.json | 5 | 0 |
| faa/FAA-S-ACS-15_Private_Helicopter_ACS.json | 14 areas | 0 |
| faa/FAA-S-ACS-16_Commercial_Helicopter_ACS.json | 14 areas | 0 |
| faa/FAA-S-ACS-14_Instrument_Helicopter_ACS.json | 8 areas | 0 |

Pending re-run after API credits: `r44_systems.json`, `FAA-S-ACS-29_CFI_Helicopter_ACS.json`
(batch stopped mid-run on 2026-04-11).

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
- `scripts/run_generate_private.ps1` — Convenience runner for `--rating private`.
- `question-bank/` — Holds generated banks; `qbank_*.json` is gitignored until Ryan
  verifies and commits a release copy manually. `.gitkeep` keeps the folder in git.

**Area I test run (Private):** Pipeline executed (`--rating private --area I`); all
tasks failed with Anthropic “credit balance too low” (0 questions written). After
billing is replenished, re-run the same command to fill Area I, then run without
`--area` for the full bank. Full generation pending Ryan review.

---

## Next Steps (in order)

1. Replenish Anthropic API credits; re-run `scripts/run_faa_r44_extract.ps1` to fill
   `r44_systems.json`, `FAA-S-ACS-29_CFI_Helicopter_ACS.json`, and ATP ACS output
   `extracted-data/faa/FAA-S-ACS-ATP_Helicopter_ACS.json` (pending extraction after
   the batch runner completes)
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
| run_generate_private.ps1 | Runs `generate_question_bank.py --rating private` |
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
