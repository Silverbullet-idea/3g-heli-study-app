# 3G Heli Study App — Master Project Context
### Last updated: May 30, 2026

---

## What This Project Is

This is the master context document for the **3G Heli Study App** — a suite of digital study tools built by Ryan Dale (3G Heli Prep / 3GSI LLC) to help helicopter students memorize, practice, and prepare for FAA knowledge exams, oral exams, and checkrides.

Every new session reads this document first. It replaces re-explaining context and keeps token usage down.

**GitHub Repository:** https://github.com/Silverbullet-idea/3g-heli-study-app
**Local repo path (Windows):** `D:\Documents\3G Heli Study App\repo`
**Companion business context:** See `3G_HELI_PREP_PROJECT.md` in this Claude project

---

## Three-Product Build Sequence

| Phase | Product | Status |
|-------|---------|--------|
| 1 | Printable / Digital Study Cards (PDF downloads) | 🔄 Data layer complete — PDF renderer next |
| 2 | POH Memory Aid Builder (web app) | 🔲 Not started |
| 3 | 3G CheckMate (Mock Checkride / Oral Exam Simulator) (AI-powered) | 🔄 Private + Commercial banks generated — verification in progress |

---

## API Cost Tracking

**Total spent to date: ~$166**

| Key | Spend | Work Covered |
|-----|-------|--------------|
| `3g-heli-study-app` | $105.55 | All extractions, Private question bank generation |
| `3G_Study_App` | $60.63 | Script debugging, Commercial Area I test, full Commercial generation |

**Current key:** `3G_Study_App` — ~$39 remaining from $100 load

**Estimated remaining costs to completion:**

| Work Item | Est. Cost |
|-----------|-----------|
| Instrument generation (~168 ACS items) | ~$12 |
| CFI generation (~858 ACS items) | ~$60 |
| ATP generation (~10 ACS items) | ~$1 |
| All verification — Commercial through ATP (Haiku) | ~$6 |
| PDF renderer testing + Phase 3 UI dev | ~$20 |
| **Total remaining** | **~$99** |

**Action needed:** Load $75 more credits before starting CFI generation.
**Projected total project API cost:** ~$240–250

---

## Cost Optimization — IMPLEMENTED

All three cost reduction measures are live in the scripts:

| Measure | Impact | Status |
|---------|--------|--------|
| Prompt caching on system prompt + handbook content | ~90% reduction on cached input tokens | ✅ Live in generate_question_bank.py |
| Haiku 4.5 for verification (vs Sonnet 4.6) | 3× cheaper per verification call | ✅ Live in verify_question_bank.py |
| Batch API | Deferred — Haiku already cheap enough for verification | 🔲 Deferred |

**Caching validation:** Commercial run showed `cache_read_input_tokens=2,439` with `input_tokens=~160` on subsequent calls within each task — cache hitting correctly.

---

## Phase 1 — Printable / Digital Study Cards

### Decisions — LOCKED

| Decision | Answer |
|----------|--------|
| Card format | Full-page study sheet style — matches existing 3G Heli Prep study sheets exactly |
| Aircraft bundling | Sold individually by aircraft AND rating level. SKU example: "Private Pilot Study Sheet — R22" |
| Price per set | $9.97 |
| Branding | Match existing 3G Heli Prep branding exactly (see Branding section below) |

### Product SKU Structure

| Priority | SKU | Status |
|----------|-----|--------|
| 1 | Private Pilot Study Sheet — R22 | 🔄 Data extracted — renderer needed |
| 2 | Private Pilot Study Sheet — R44 | 🔄 Data extracted |
| 3 | Private Pilot Study Sheet — R66 | ✅ Data extracted |
| 4 | Private Pilot Study Sheet — Bell 505 | ✅ Data extracted (manual) |
| 5 | Private Pilot Study Sheet — Bell 206B3 | ✅ Data extracted |
| 6 | Private Pilot Study Sheet — Bell 407 | ✅ Data extracted |
| 7 | Commercial Pilot Study Sheet — R22 | 🔲 |
| 8 | Commercial Pilot Study Sheet — R44 | 🔲 |

### Build Approach

1. ✅ Extract R22 POH Sections 2, 3, 7 to JSON
2. ✅ Extract R44 POH Sections 2, 3 to JSON (Section 7 needs rerun)
3. ✅ Extract FAA handbooks to JSON
4. ✅ Bell 505 limitations, emergency procedures, systems extracted (manual)
5. ✅ R66, Bell 206B3, Bell 407 extraction complete
6. 🔲 Build PDF renderer that reads JSON → outputs branded 8.5"×11" study sheets
7. 🔲 Package into per-rating, per-aircraft PDF sets

### Existing Study Sheet Inventory

| Sheet Title | Type | Verify Against | Notes |
|-------------|------|----------------|-------|
| Helicopter Systems | General | FAA-H-8083-21B Ch. 6 | Piston engine, rotor types, electrical, fuel |
| Instruments | General | FAA-H-8083-21B Ch. 11 | 3 pages: pitot-static, gyro, compass, power instruments |
| Aerodynamics Basics | General | FAA-H-8083-21B Ch. 2 | Airfoil theory, AOA, chord line definitions |
| Four Aerodynamic Forces | General | FAA-H-8083-21B Ch. 2-3 | Lift/weight/thrust/drag, Bernoulli, Newton, drag types |
| Aerodynamic Principles | General | FAA-H-8083-21B Ch. 3 | Ground effect, ETL, transverse flow, dissymmetry of lift |
| Aerodynamics Hazards | General | FAA-H-8083-21B Ch. 11 | LTE, dynamic rollover, settling with power, retreating blade stall |
| Autorotations | General | FAA-H-8083-21B Ch. 11 | Driven/driving/stalled regions |
| Weight & Balance | General | FAA-H-8083-1B | 2 pages: definitions and computation methods |
| R22 Specific Systems | R22 | R22 POH Section 7 | ALL VALUES VERIFIED against current POH JSON |
| Weather Theory | General | FAA-H-8083-21B Ch. 12 | Multi-page atmospheric science |
| Weather Information | General | FAA-H-8083-21B Ch. 12 | METAR, TAF, ATIS, PIREP, SIGMETs |
| Airspace | General | ACS + AIM | Class A-G, special use airspace |
| Navigation | General | FAA-H-8083-21B Ch. 13 | VOR, GPS, charts, compass errors |
| Flight Planning | General | FAA-H-8083-21B Ch. 13 | VFR flight plans, VOR, GPS, traffic patterns |
| Airport Markings | General | AIM | Signs, beacons, VASI, PAPI — includes color tables |
| Aeromedical | General | FAA-H-8083-21B Ch. 16 | Hypoxia, spatial disorientation, vision, illusions |
| Aeronautical Decision Making | General | FAA-H-8083-21B Ch. 17 | IMSAFE, PAVE, 3P, 5 hazardous attitudes |
| FAR Part 61 | General | FAR/AIM | Key section references |
| FAR Part 91 | General | FAR/AIM | Full section list + A TOMATO FLAMES AF mnemonic + VFR minimums table |
| NTSB 830 & Inspections | General | NTSB 830 / FAR 43 | Accident reporting, MEL, Form 337, inspection types |

**Sheets still needed (new builds from extracted JSON):**
- R22 Limitations & V-speeds (from r22_limitations.json)
- R22 Emergency Procedures (from r22_emergency_procedures.json)
- R44 Specific Systems (from r44_systems.json — pending rerun)
- R44 Limitations & V-speeds (from r44_limitations.json)
- R44 Emergency Procedures (from r44_emergency_procedures.json)
- R66 Limitations, Systems, Emergency Procedures (data ready)
- Bell 505 Limitations, Systems, Emergency Procedures (data ready)
- Bell 206B3 Limitations, Systems, Emergency Procedures (data ready)
- Bell 407 Limitations, Systems, Emergency Procedures (data ready)

---

## Phase 3 — 3G CheckMate (Mock Checkride / Oral Exam Simulator)

### Product Decision — LOCKED

- **Interaction model:** Hybrid — verified question bank provides opening questions; AI generates conversational follow-ups. Replicates actual DPE oral structure.
- **Pricing model:** Session-based blocks. NOT per-question or unlimited.
- **Pricing (finalize after beta):** ~$39.97 / 10 sessions; ~$9.97/month / 4 sessions
- **Bundle:** Included free with 21-Day Course; $19.97 add-on for existing students
- **API model:** claude-haiku-4-5-20251001 for student interactions
- **Est. cost per session:** $0.02–$0.04 with prompt caching
- **At 1,000 active students × 4 sessions/month:** ~$120/month API cost
- **No student API key required** — 3G absorbs cost
- **Student profiles:** Supabase lightweight JSON per student, injected at session start

### Interaction Model — LOCKED

1. AI opens with **canned question** from verified bank for current topic
2. Student responds (typed, V1)
3. AI generates **conversational follow-up** — probing gaps, edge cases, as a real DPE would
4. Thread continues until topic adequately covered
5. AI transitions to next canned opener for next topic
6. Session ends after defined topic set complete

Token usage naturally bounded — AI responds within defined topic context.

### Student Profile & Memory — LOCKED

Supabase per-student JSON. Per topic: sessions practiced, self-assessed confidence (1–3), AI-flagged performance. Context injected at session start. Scales to thousands of students without meaningful cost increase.

### Session Modes — LOCKED

| Mode | Description |
|------|-------------|
| **Full Oral Simulation** | Complete ACS topic set in sequence. For students 30–60 days from checkride. |
| **Weak Area Drill** | Student selects specific topics. 15–20 min. High replay value. |
| **Checkride Countdown** | Optional. Student sets checkride date. Sessions auto-adjust by proximity. |

### Post-Session Summary — LOCKED

Student can save or email:
- Topics covered, performance by topic
- Specific weak areas + FAA resource recommendations with **direct links to free FAA PDFs**
- Recommended next session focus
- Contextual 3G course upsell where relevant (non-pushy, triggered by weak area)

### FAA Citation Debrief — LOCKED

Every post-session debrief displays the exact FAA knowledge base citation for each question answered — FAR section, AIM paragraph, or ACS task code. Citations are drawn from `acs_to_resources.json` and mapped to helicopter-specific handbook chapters (FAA-H-8083-21B) rather than generic FAR/AIM references. This is a direct differentiator over competitors (Checkride.bot, Sporty's ChatDPE) who cite generic references not specific to rotorcraft.

Citation format per question in debrief:
- ACS task code (e.g., PA.I.B.K1)
- Primary FAA source with chapter/section
- Direct link to free FAA PDF where available

Build `acs_to_resources.json` to include helicopter-specific chapter mapping before Phase 3 UI build begins.

---

### Knowledge Test Weak Area Import — LOCKED

Students can enter their FAA knowledge test score report data (manually, V1 — no image upload yet) to pre-populate their weak ACS areas. The session automatically weights questions toward those gaps on first launch.

This meets the student at maximum motivation — right after receiving their written test results. Implementation: a simple onboarding step during first session setup. Student selects which ACS areas were flagged on their knowledge test; these are stored in their Supabase profile and used to weight initial session topic order.

This is the on-ramp to the existing "Weak Area Drill" mode and complements the ACS coverage dashboard already planned.

---

### Aircraft-Specific Systems Questioning — LOCKED

CheckMate asks aircraft-specific systems questions grounded in the extracted POH JSON data layer, not generic helicopter questions. This is the primary technical differentiator over all known competitors — none have POH-level aircraft data backing their questions.

Examples:
- "Walk me through the R22's low rotor RPM warning system."
- "What are the R44's vortex ring state recovery procedures per the POH?"
- "What is the Bell 505's engine-off landing sequence?"

Implementation: during session setup, student selects their training aircraft. Aircraft tag is stored in Supabase profile. Session question weighting draws from the corresponding aircraft JSON files already extracted:
- R22: r22_limitations.json, r22_emergency_procedures.json, r22_systems.json ✅
- R44: r44_limitations.json, r44_emergency_procedures.json (r44_systems.json ❌ needs rerun)
- R66: r66_limitations.json, r66_emergency_procedures.json, r66_systems.json ✅
- Bell 505: b505_limitations.json, b505_emergency_procedures.json, b505_systems.json ✅
- Bell 206B3: b206_limitations.json, b206_emergency_procedures.json, b206_systems.json ✅
- Bell 407: b407_limitations.json, b407_emergency_procedures.json, b407_systems.json ✅

Aircraft selection is required at session start. This field is stored in the student's Supabase profile and persists across sessions.

---

### AI Coaching Tone — LOCKED

The AI examiner's feedback voice is calibrated as "Ryan coaching," not a cold grader. When a student answers incorrectly or incompletely, the AI does not simply output the correct answer — it explains the concept the way a CFI would, including the "why" and a practical example where appropriate.

System prompt guidance: "When a student's answer is wrong or incomplete, respond the way an experienced helicopter CFI would — acknowledge what they got right, correct what's wrong, explain the reasoning, and give a real-world example if it helps. Do not sound like a bureaucrat. Sound like Ryan."

This framing is applied to all AI follow-up turns. The opening canned question maintains examiner tone; feedback turns shift to coaching tone.

### FAA Resource Recommendations — LOCKED

Build `acs_to_resources.json` at Phase 3 UI start.

| ACS Topic Area | Primary FAA Resource | Chapter/Section |
|----------------|---------------------|-----------------|
| Weather Theory / Air Masses | FAA-H-8083-28B Aviation Weather Handbook | Ch. 11 |
| Weather Information (METARs, TAFs) | FAA-H-8083-28B | Ch. 13 |
| Aerodynamics | FAA-H-8083-21B Helicopter Flying Handbook | Ch. 2–3 |
| Helicopter Systems | FAA-H-8083-21B | Ch. 6 |
| Emergency Procedures | FAA-H-8083-21B | Ch. 11 |
| Weight & Balance | FAA-H-8083-1B | Ch. 4–5 |
| Airspace | AIM | Ch. 3 |
| Navigation | FAA-H-8083-21B | Ch. 13 |
| Regulations (Part 61/91) | FAR/AIM | Parts 61, 91 |
| Aeromedical | FAA-H-8083-21B | Ch. 16 |
| ADM / Risk Management | FAA-H-8083-21B | Ch. 17 |
| Instruments | FAA-H-8083-21B | Ch. 11 |

### Progress Dashboard — LOCKED

Student-facing ACS coverage map: green/yellow/red by topic. Progress visualization — not gamification. Sessions completed, weak areas, recommended next focus.

### Gamification — DEFERRED

Not in 3G CheckMate. Future standalone app for earlier-stage students. Question bank and topic-tagging feed that future product.

### Copyright — RESOLVED

Original question bank using ACS + FAA handbooks. No HOEG content used.

### Question Bank Status

| Rating | Questions | Verified | FLAG Queue |
|--------|-----------|---------|------------|
| Private | 6,728 | ✅ Complete | 480 — pending Ryan review |
| Commercial | 6,279 | 🔲 Not run | — |
| Instrument | 🔲 Not generated | — | — |
| CFI | 🔲 Not generated | — | — |
| ATP | 🔲 Not generated | — | — |

**Private FLAG review:** Run `.\scripts\run_review_server.ps1` → `http://localhost:5000`. Stop with **Ctrl+C** (not window close). review_changes.log records all edits/rejections for publisher submissions.

**IMPORTANT:** Generator iterates ACS **items** (K1/R1/S1), not tasks. Do not revert this.

### Verifier Flags

- `--retry-failures` — only re-processes API-failure questions, skips PASS
- `--batch-limit N` — process only first N batches (testing)

**Root cause of prior verification failures:** Stale API key in `repo\.env`. Fixed: `.env` now loads repo first, then parent with `override=True`.

**Known accuracy corrections in verifier system prompt:**
- BasicMed max gross weight: 12,500 lbs (NOT 6,000 lbs)
- BasicMed: no distance limitation, no turbine restriction
- ADS-B Out required since January 1, 2020

### Scripts Reference

| Script | Purpose | Status |
|--------|---------|--------|
| `extract_text.py` | PDF → raw text | ✅ |
| `extract_poh_json.py` | Raw text → structured JSON | ✅ |
| `generate_question_bank.py` | ACS + handbook → question bank (caching live) | ✅ |
| `verify_question_bank.py` | Haiku verifier (caching, .env fix, logging, batch-limit) | ✅ |
| `review_server.py` | Flask FLAG review + review_changes.log | ✅ |
| `run_generate_private.ps1` | Private generation wrapper | ✅ |
| `run_verify_private.ps1` | Private verification wrapper | ✅ |
| `run_review_server.ps1` | Review server wrapper | ✅ |
| `verify_private_question_count.py` | Count questions, PASS/FAIL gate | ✅ |
| `diagnose_flags.py` | FLAG distribution report | ✅ |
| `populate_pdf_library.py` | PDF download manager | ✅ |

---

## Data Layer Status

### Extracted JSON — Aircraft

| File | Records | Verify Flags | Status |
|------|---------|-------------|--------|
| `aircraft/r22_limitations.json` | 9 sections | 1 (VNE chart) | ✅ |
| `aircraft/r22_emergency_procedures.json` | 17 procedures | 0 | ✅ |
| `aircraft/r22_systems.json` | 28 systems | 0 | ✅ |
| `aircraft/r44_limitations.json` | 8 sections | 0 | ✅ |
| `aircraft/r44_emergency_procedures.json` | 17 procedures | 0 | ✅ |
| `aircraft/r44_systems.json` | — | — | ❌ Needs rerun |
| `aircraft/b505_limitations.json` | Full limits | 0 | ✅ |
| `aircraft/b505_emergency_procedures.json` | 11 procedures | 0 | ✅ |
| `aircraft/b505_systems.json` | 9 systems | 0 | ✅ |
| `aircraft/r66_limitations.json` | 9 groups | 7 | ✅ |
| `aircraft/r66_emergency_procedures.json` | 21 procedures | 0 | ✅ |
| `aircraft/r66_systems.json` | 32 sections | 0 | ✅ |
| `aircraft/b206_limitations.json` | 9 groups | 8 | ✅ |
| `aircraft/b206_emergency_procedures.json` | 47 procedures | 0 | ✅ |
| `aircraft/b206_systems.json` | 24 sections | 0 | ✅ |
| `aircraft/b407_limitations.json` | 9 groups | 8 | ✅ |
| `aircraft/b407_emergency_procedures.json` | 27 procedures | 0 | ✅ |
| `aircraft/b407_systems.json` | 22 sections | 0 | ✅ |

### Extracted JSON — FAA

| File | Records | Status |
|------|---------|--------|
| `faa/FAA-H-8083-21B_Helicopter_Flying_Handbook.json` | 7 topics | ✅ |
| `faa/FAA-H-8083-4_Helicopter_Instructors_Handbook.json` | 21 topics | ✅ |
| `faa/FAA-H-8083-15B_Instrument_Flying_Handbook.json` | 84 topics | ✅ |
| `faa/FAA-H-8083-1B_Weight_Balance_Handbook.json` | 5 topics | ✅ |
| `faa/FAA-S-ACS-15_Private_Helicopter_ACS.json` | 14 areas | ✅ |
| `faa/FAA-S-ACS-16_Commercial_Helicopter_ACS.json` | 14 areas | ✅ |
| `faa/FAA-S-ACS-14_Instrument_Helicopter_ACS.json` | 8 areas | ✅ |
| `faa/FAA-S-ACS-29_CFI_Helicopter_ACS.json` | — | ❌ Needs rerun |
| `faa/FAA-S-ACS-ATP_Helicopter_ACS.json` | — | ❌ Not yet run |
| `faa/acs_to_resources.json` | — | 🔲 Build at Phase 3 UI start |

---

## Branding — 3G Heli Prep

### Colors
| Element | Value |
|---------|-------|
| Primary orange | #E8650A |
| Primary blue/purple | #4B5EBF |
| Background | White (#FFFFFF) |
| Body text | Near-black (#1A1A1A) |
| Watermark | Logo icon at ~10% opacity, centered |

### Logo Assets (in this Claude project)
- `AILogoFinal.png` — Full color horizontal lockup with radar icon
- `HeliOnlyLarge.png` — Full color icon only (watermark use)
- `WhiteLogoONLY.png` — White version
- `BlackLogoHeliOnly.png` — Dark icon version

### Study Sheet Layout Rules
- White 8.5" x 11" portrait, no borders
- Logo top-center, ~1.5" wide
- Large bold centered title below logo
- **Bold term** — Regular definition, sub-items indented
- Watermark: helicopter icon centered at ~10% opacity
- Tables for structured data
- "By the author of the ASA Helicopter Oral Exam Guide" on cover page

---

## GitHub Repository

**URL:** https://github.com/Silverbullet-idea/3g-heli-study-app
**Local clone:** `D:\Documents\3G Heli Study App\repo`
**Branch:** main
**Auth:** Windows Credential Manager
**AGENTS.md:** Repo root — every Cursor agent reads and updates it

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| April 2026 | Build order: Cards → POH Builder → Oral Simulator | Lowest dev cost first |
| April 2026 | Study sheet format (full page, matches existing) | Consistent brand |
| April 2026 | Sold by rating × aircraft ($9.97 per SKU) | Maximizes revenue |
| April 2026 | Robinson Tier 1 priority (R22, R44, R66) | 80%+ of US training market |
| April 2026 | Bell 505, 206B3, 407 in Phase 1 data layer | Popular training aircraft |
| April 2026 | Military aircraft deferred | NATOPS not public |
| April 2026 | Extraction model: claude-sonnet-4-6 | Quality at reasonable cost |
| April 2026 | 3G CheckMate (Mock Checkride / Oral Exam Simulator): session-based pricing | Bounds token cost exposure |
| April 2026 | 3G CheckMate: original Q&A only | ASA agreement prohibits HOEG content |
| April 2026 | 8 questions per ACS item (3/3/2 difficulty) | ~6,744 Private questions |
| April 2026 | Generator iterates ACS items not tasks | Per-task only produced 392 questions |
| April 2026 | Verification: batched 10 per API call | 675 calls vs 6,744 |
| April 2026 | 3G CheckMate API: claude-haiku-4-5-20251001 | ~$3/month max per active student |
| April 2026 | No student API key required | UX friction kills conversion |
| April 16, 2026 | Hybrid interaction model (canned opener + AI follow-ups) | Replicates real DPE oral |
| April 16, 2026 | Per-student Supabase profile for session memory | Lightweight JSON, scales to thousands |
| April 16, 2026 | Three session modes: Full Oral, Weak Area Drill, Countdown | Serves different student needs |
| April 16, 2026 | Post-session summary with save/email | Embeds product in training workflow |
| April 16, 2026 | FAA resource links on weak areas | Direct links to free FAA PDFs; built-in upsell |
| April 16, 2026 | ACS coverage dashboard (green/yellow/red) | Progress visualization without gamification |
| April 16, 2026 | Gamification deferred to future standalone app | Undercuts checkride-prep positioning |
| April 17, 2026 | Verifier switched to Haiku 4.5 | 3× cheaper; sufficient for QA task |
| April 17, 2026 | Prompt caching on system prompt + handbook content | ~90% input token savings confirmed |
| April 17, 2026 | .env fix: load repo then parent with override=True | Stale repo key caused 100% auth failures |
| April 17, 2026 | review_changes.log added to review_server.py | Publisher submission record for corrections |
| April 17, 2026 | --batch-limit flag added to verifier | Single-batch testing |
| April 17, 2026 | Error logging in both scripts | Errors visible not silently swallowed |
| April 19, 2026 | Commercial bank: 6,279 questions generated | Caching confirmed working on full run |
| May 2026 | Product named 3G CheckMate | Brand alignment; competitive differentiation |
| May 2026 | FAA citation debrief — helicopter-specific chapter mapping | Differentiates from Sporty's/Checkride.bot generic citations |
| May 2026 | Knowledge test weak area import (manual, V1) | Meets student at peak motivation post-written-test |
| May 2026 | Aircraft-specific POH questioning — LOCKED | Only product with POH-grounded aircraft systems Q&A |
| May 2026 | AI feedback tone: CFI coaching voice, not cold grader | Inspired by Gleim DPE model; matches Ryan's brand voice |

---

## Open Questions

**Phase 1:**
- [ ] R44 Raven I vs Raven II — separate SKUs or combined? (Limitations differ)
- [ ] H125 (AS350) extraction — after current pipeline confirmed
- [ ] PDF renderer: Python (reportlab/weasyprint) or HTML-to-PDF?
- [ ] Additional topics Ryan wants beyond STUDY_SHEET_MASTER content?

**Phase 3:**
- [ ] Confirm session block size + price after beta token cost data
- [ ] Confirm monthly subscription price after beta
- [ ] Ryan willing to record short video explanations for correct-answer moments?
- [ ] B2B / flight school licensing — after consumer MVP proven
- [ ] Caching layer for common Q&A pairs — defer until 500+ active users
- [ ] Build acs_to_resources.json at Phase 3 UI start
- [ ] V2: Add image upload for FAA knowledge test score report (auto-parse weak ACS areas)
- [ ] V2: Consider 30-day unlimited access tier as alternative to session blocks (ref: Checkride.bot model)
- [ ] Confirm aircraft selection UI — dropdown at session start or stored in profile only?
- [ ] R44 systems JSON must be rerun before R44 aircraft-specific questioning can go live

**Library — still needed:**
- [ ] Lycoming O-360, O-540, IO-540 — find URLs at lycoming.com/publications
- [ ] AC 61-67D, AC 91-13D — rgl.faa.gov DNS issue, retry
- [ ] r44_systems.json rerun when credits available
- [ ] CFI ACS JSON rerun when credits available

---

## Immediate Next Steps

1. **Load $75 more API credits** before starting CFI generation
2. **Run Private FLAG review** — `.\scripts\run_review_server.ps1` → `http://localhost:5000` — 480 FLAG queue — stop with Ctrl+C
3. **Run Commercial verification** — after Private review complete
4. **Generate Instrument bank** — `generate_question_bank.py --rating instrument`
5. **Generate CFI bank** — largest remaining (~858 items) — run overnight
6. **Generate ATP bank** — smallest remaining
7. **Verify all remaining banks** — Commercial through ATP
8. **Rerun r44_systems + CFI ACS extraction** — when credits confirmed
9. **Build PDF renderer** — reads JSON → branded study sheets
10. **Build Phase 3 UI** — hybrid session loop, Supabase profiles, three modes, post-session summary, FAA citation debrief (helicopter-specific), knowledge test weak area import, aircraft selection + POH-grounded questions, AI coaching tone, ACS coverage dashboard

---

## Session Startup Checklist

1. Read this document fully
2. Read `3G_HELI_PREP_PROJECT.md` for business context
3. Read `AGENTS.md` in repo root for current git state
4. Check Immediate Next Steps — start at item 1
5. Check Decision Log — do not re-open closed decisions
6. Confirm API credits before running generation or verification
7. Always use `.venv\Scripts\python.exe` — never bare `python`
8. Never commit PDF files or draft question bank JSON
9. Generator iterates ACS **items** (K1/R1/S1), not tasks — do not revert
10. Stop review server with **Ctrl+C** not window close — session footer requires clean exit