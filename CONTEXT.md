# CONTEXT.md — 3G Heli Study App
### Stable reference layer — update only when architecture or direction changes fundamentally

---

### Project Identity
- **Purpose:** Digital study tool suite for helicopter pilot students — printable PDF study sheets, a web POH memory aid, and an AI-powered oral exam simulator
- **Owner:** Ryan Dale / 3G Heli Prep / 3GSI LLC, Post Falls, Idaho
- **Target user:** Aspiring helicopter pilots preparing for FAA Private, Commercial, Instrument, CFI, and ATP checkrides; primary training aircraft R22/R44
- **Current phase:** Phase 1 — Printable/Digital PDF Study Sheet Sets
- **Revenue model:** $9.97/set PDF downloads sold individually by rating × aircraft; Mock Checkride $39.97 standalone (Phase 3) — storefront integration (CC360 / GoHighLevel) not verified in repo ?

---

### Tech Stack

| Layer | Detail |
|-------|--------|
| PDF renderer | Python 3, ReportLab — `scripts\render_study_sheet.py` |
| Extraction pipeline | Python 3, Anthropic API (`claude-sonnet-4-6`) — `scripts\extract_poh_json.py` |
| Verification | Python 3, Anthropic API — **`claude-haiku-4-5-20251001`** in `call_verifier_api()` (`scripts\verify_question_bank.py`); file also defines unused `MODEL_ID = "claude-sonnet-4-6"` (docstring mismatch — cleanup ?) |
| Review UI | Flask (`review_server.py`, default port **5000**) |
| Question bank storage | JSON flat files under `question-bank\` |
| Database | None in Phase 1; Supabase (lightweight JSON profiles) planned for Phase 3 |
| Auth | None in Phase 1 |
| Phase 1 delivery | Static PDF downloads via storefront ? (see Project Identity) |
| Phase 3 delivery | TBD — React + Vercel + Supabase (Phase 2/3 gate per `AGENTS.md`) |
| External services | Anthropic API (extraction, generation, verification, Phase 3 student interactions) |
| Dev environment | Windows, PowerShell, Python via **`.venv\Scripts\python.exe`** for scripts; API key in `repo\.env` (gitignored). Parent workspace `AGENTS.md` documents interactive `py -3` for shells — both conventions coexist ? |

---

### Repository Layout

| Folder | Owns |
|--------|------|
| `scripts\` | All pipeline scripts — extraction, generation, verification, review server, PDF renderer, PowerShell wrappers |
| `extracted-data\aircraft\` | Structured JSON from POH extractions — **tracked in git when committed** (not gitignored; see `.gitignore`) |
| `extracted-data\faa\` | Structured JSON from FAA handbook/ACS extractions |
| `extracted-data\raw-text\` | Raw PDF text output (**gitignored**) |
| `question-bank\` | Generated question bank JSON drafts (**`qbank_*.json` gitignored**) |
| `raw-pdfs\` | Source PDFs — Robinson, Bell, Airbus, FAA handbooks (**gitignored**) |
| `study-cards\` | Output folder for rendered PDF study sheets |
| `assets\` | Brand assets — `logo_horizontal.png`, `heli_icon.png` |
| `docs\` | `LIBRARY_INDEX.md` and supporting documentation |

---

### Design System

| Token | Value |
|-------|-------|
| Primary orange | `#E8650A` |
| Primary blue/purple | `#4B5EBF` |
| Background | `#FFFFFF` |
| Body text | `#1A1A1A` |
| Watermark opacity | 8–10% |

**Layout rules:**
- Portrait letter (8.5" × 11"), white background, no decorative borders
- Logo: `logo_horizontal.png`, ~1.5" wide, top-center
- Title: bold, centered, below logo
- Body: **Bold term** — Regular definition, sub-items indented
- Watermark: `heli_icon.png`, centered, ~8–10% opacity
- Cover line: "By the author of the ASA Helicopter Oral Exam Guide"
- Typography: Windows Arial (body), Courier (data/tables) via ReportLab

---

### Architectural Rules (Non-Negotiable)

- **Never invent POH numbers** — all values must come from extracted JSON only
- **R22 and R44 data must never mix** — aircraft-specific data and sheets only
- **R44 variants (Raven I / II / Cadet) are distinct** — never combine into one sheet
- **SFAR 73 awareness** required for all R22/R44 content
- **Python runtime:** always **`.venv\Scripts\python.exe`** — never bare `python` in automation; interactive `py -3` appears in workspace docs for human use ?  
- **Never commit PDFs or draft question bank JSON** — `qbank_*.json` gitignored by design
- **Never commit `raw-pdfs\`** — source PDFs stay local
- **API key in `repo\.env` only** — never hardcode in scripts
- **Generator iterates ACS items (K1/R1/S1 lines per task), not whole tasks only** — `iter_acs_items()` in `generate_question_bank.py`; do not revert this
- **Review server:** `atexit` + `finally` call `_write_session_footer()`; prefer **Ctrl+C** for clean shutdown — force-closing the terminal may skip footer ?  
- **`AGENTS.md` at repo root is the living agent status board** — every agent reads it on start and updates it on completion

---

### Phase Map

| Phase | Name | Description | Status |
|-------|------|-------------|--------|
| 1 | PDF Study Sheet Sets | $9.97/set branded PDFs by rating × aircraft, sold as downloads | IN PROGRESS |
| 2 | POH Memory Aid Builder | Web app (React, Vercel, Supabase) | DEFERRED — gate: Phase 1 ships and earns |
| 3 | Mock Checkride / Oral Exam Simulator | AI (Claude API), ACS banks, Supabase profiles | **Product** gated like Phase 2; **question bank + verification pipeline** in active use in repo |

**Phase 1 SKU build order:** Private R22 → Private R44 → Commercial R22 → Commercial R44 → CFI R22 → CFI R44 → Instrument R22 → Instrument R44

---

### Key Decisions Log

- **PDF format: full-page study sheet** (not flashcard) — matches existing 3G Heli Prep branding exactly
- **$9.97 per rating × aircraft SKU** — maximizes revenue ladder; entry at Private R22
- **Robinson Tier 1 priority (R22, R44, R66)** — 80%+ of US training helicopter market
- **Extraction model: `claude-sonnet-4-6`** — quality at reasonable cost
- **Verification API model: `claude-haiku-4-5-20251001`** — batched QA in `verify_question_bank.py` (cost/accuracy tradeoff; “3× cheaper than Sonnet” — business estimate ?)
- **Prompt caching:** `cache_control: ephemeral` on system + handbook blocks in generator and verifier — **~90% input token reduction** stated in planning docs — not re-measured in this session ?
- **8 questions per ACS item** (3 basic / 3 intermediate / 2 advanced) — full Private run in `AGENTS.md` reported **6,744** questions; **current** local `qbank_private_helicopter.json` totals **6,396** (delta unexplained — review edits / partial file ?)
- **Generator iterates ACS items not tasks** — per-task approach only yielded ~392 questions (historical)
- **Verification batched 10 questions per API call** (`BATCH_SIZE = 10`) — ~675 batches vs ~6,744 rows for a full private-sized bank
- **Mock Checkride: no student API key required** — UX friction kills conversion; 3G absorbs cost
- **Mock Checkride: hybrid interaction model** (canned opener from verified bank + AI conversational follow-ups)
- **Mock Checkride: session-based pricing** — bounds token cost exposure per student
- **Mock Checkride: per-student Supabase JSON profile** — lightweight, scales to thousands
- **Question bank JSON gitignored during draft/review** — committed only after Ryan verification pass
- **ASA publishing agreement constraint** — Mock Checkride must use original question bank; no HOEG content
