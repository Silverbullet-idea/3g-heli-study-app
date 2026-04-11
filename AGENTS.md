# 3G Heli Study App — Agent Reference

## Project: 3G Heli Study App

Last updated: 2026-04-11

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
- scripts/run_faa_r44_extract.ps1 — FAA handbooks + R44 (IN PROGRESS)
- scripts/run_expanded_library.ps1 — engine manuals, PHAK, AIM, ACs

### Extracted JSON (verified, committed)

- extracted-data/aircraft/r22_limitations.json (1 verify flag — VNE chart)
- extracted-data/aircraft/r22_emergency_procedures.json (17 procedures, 0 verify)
- extracted-data/aircraft/r22_systems.json (28 systems, 0 verify)

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
- raw-pdfs/faa/advisory-circulars/
  - AC_00-6B Aviation Weather (downloaded)
  - AC_61-67D, AC_91-13D — DNS failure on rgl.faa.gov (retry later)

---

## Next Steps (in order)

1. Confirm FAA handbook + R44 JSON extraction completed
   (scripts/run_faa_r44_extract.ps1 was running at session end)
2. Review verify flag counts across all extracted JSON
3. Commit all extracted JSON files
4. Build PDF renderer — reads JSON, outputs branded 8.5x11 study sheets
5. Produce first complete study sheet set: Private Pilot R22

---

## Open Items / Blocked

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
5. After completing any task, update LIBRARY_INDEX.md if PDFs were
   added or moved
6. Never commit PDF files — they are gitignored by design
7. Never hard-delete extracted JSON — these are verified source data
8. Use `.venv\Scripts\python.exe` — never bare python
