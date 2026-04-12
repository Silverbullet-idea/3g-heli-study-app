# Library Index

## Local Archive — AHC POH Collection

| File | Aircraft | Manufacturer | Category | Source | Status |
|------|----------|--------------|----------|--------|--------|
| Bell-206B3.pdf | Bell 206B-3 Jet Ranger | Bell | Flight Manual | Local archive | Ready for extraction |
| BH05FM3.pdf | Bell 205 | Bell | Flight Manual | Local archive | Ready for extraction |
| BH06LR.pdf | Bell 206L Long Ranger | Bell | Flight Manual | Local archive | Ready for extraction |
| BH12.pdf | Bell 212 | Bell | Flight Manual | Local archive | Ready for extraction |
| BH12SFMS.pdf | Bell 212 SFMS | Bell | Supplement | Local archive | Ready for extraction |
| BHT-212-CAA-FM-1.pdf | Bell 212 (CAA) | Bell | Flight Manual | Local archive | Ready for extraction |
| BHT-212-IFR-FM-1.pdf | Bell 212 IFR | Bell | IFR Supplement | Local archive | Ready for extraction |
| BHT-212-MD1.pdf | Bell 212 Maintenance Data | Bell | Maintenance | Local archive | Reference only |
| BHT-407-FM-1.pdf | Bell 407 | Bell | Flight Manual | Local archive | Ready for extraction |
| EC120BFM.pdf | Airbus EC120B Colibri | Airbus | Flight Manual | Local archive | Ready for extraction |
| EC120FM.pdf | Airbus EC120 | Airbus | Flight Manual | Local archive | Ready for extraction |
| EC130B4.pdf | Airbus EC130B4 | Airbus | Flight Manual | Local archive | Ready for extraction |
| AW139_Flight_Manual.pdf | AgustaWestland AW139 | Leonardo | Flight Manual | Local archive | Ready for extraction |
| Know_your_PT6A.pdf | PT6A Engine | Pratt & Whitney | Engine Reference | Local archive | Reference only |
| MD500D.pdf | MD Helicopters MD500D | MD Helicopters | Flight Manual | Local archive | Ready for extraction |
| TD_AS365_N3.pdf | Aerospatiale AS365 N3 Dauphin | Airbus | Flight Manual | Local archive | Ready for extraction |

## Skipped Documents

| File | Reason |
|------|--------|
| SUPER_KING_AIR_200_200C_POH_AFM | Fixed wing — out of scope |
| SUPER_KING_AIR_B200_B200C_POH_AFM | Fixed wing — out of scope |
| G1000_CessnaMustang_PilotsGuide | Fixed wing — out of scope |
| G1000_Mustang_LMM_RevF | Fixed wing — out of scope |
| SH-60B Seahawk | Military rotorcraft — NATOPS restricted |

## Bell Downloads (populate_pdf_library.py)

| File | Aircraft | Source | Status |
|------|----------|--------|--------|
| bell_206b3_fm_1.pdf | Bell 206B-3 | mvheli.com | Downloaded |
| bell_206ab_maintenance_manual.pdf | Bell 206A/B | rotorair.ch | Downloaded |
| bell_505_product_specifications_feb2026.pdf | Bell 505 | bellflight.com (official) | Downloaded |
| bell_505_easa_tcds_issue4_apr2021.pdf | Bell 505 | easa.europa.eu (official) | Downloaded |
| bell_505_normal_checklist_iss1_rev1.pdf | Bell 505 | heli-academy.ch | Downloaded |
| bell_505_emergency_procedures_iss1_rev0.pdf | Bell 505 | heli-academy.ch | Downloaded |
| bell_505_tc_mmel_feb2017.pdf | Bell 505 | Transport Canada (official) | Downloaded |
| bell_505_rfm_bht505fm1_rev3.pdf | Bell 505 | pdfcoffee.com | SKIPPED — copyright flag |

## FAA ACS Documents

| File | Title | Issuer | Type | Source | Status |
|------|-------|--------|------|--------|--------|
| FAA-S-ACS-ATP_Helicopter_ACS.pdf | ATP Helicopter ACS | FAA | ACS Document | Local archive (pre-release) | Ready for extraction |

Note: ATP ACS sourced from Ryan's local archive (FAA-2022-1463-0012). Pre-release copy — not yet publicly available. Treat as authoritative for extraction purposes.

## Engine Manuals and FAA References

Documents below are configured in `scripts/populate_pdf_library.py`. Entries marked **url uncertain** may 404 or fail on some networks; update URLs in the script after manual verification.

| File | Category | Manufacturer | Source | Notes |
|------|----------|--------------|--------|-------|
| R22_MM_Revision_NOV2024.pdf | Maintenance revision file | Robinson | robinsonheli.com (blob) | R22 MM revision NOV 2024 |
| R22_Maintenance_Manual_full.pdf | Maintenance manual (full) | Robinson | robinsonheli.com (blob) | **url uncertain** — inferred URL may 404 |
| R44_Maintenance_Manual_full.pdf | Maintenance manual (full) | Robinson | robinsonheli.com (blob) | **url uncertain** — inferred URL may 404 |
| Lycoming_O-320_Operators_Manual_60297-30.pdf | Engine operator's manual | Lycoming | yankee-aviation.com | O-320 — R22 Standard/HP/Alpha |
| Lycoming_O-360_Operators_Manual_60297-12.pdf | Engine operator's manual | Lycoming | lycoming.com | O-360 — R22 Beta II — **url uncertain** if direct attachment 404 |
| Lycoming_O-540_Operators_Manual.pdf | Engine operator's manual | Lycoming | lycoming.com | O-540 — R44 Raven I — **url uncertain** if direct attachment 404 |
| Lycoming_IO-540_Operators_Manual.pdf | Engine operator's manual | Lycoming | lycoming.com | IO-540 — R44 Raven II — **url uncertain** if direct attachment 404 |
| Lycoming_Direct_Drive_Overhaul_Manual.pdf | Engine overhaul manual | Lycoming | expaircraft.com | Direct-drive overhaul reference |
| FAA-H-8083-25C_Pilots_Handbook_Aeronautical_Knowledge.pdf | PHAK | FAA | faa.gov | FAA-H-8083-25C (full PDF) |
| FAA-H-8083-15B_Instrument_Flying_Handbook.pdf | Instrument Flying Handbook | FAA | faa.gov | Skip download if already in repo |
| FAA-H-8083-16B_Instrument_Procedures_Handbook.pdf | Instrument Procedures Handbook | FAA | faa.gov | IFR procedures |
| FAA_AIM_2024.pdf | AIM | FAA | faa.gov | Current AIM basic PDF from Air Traffic Publications |
| AC_61-67D_Stall_Spin_Awareness.pdf | Advisory circular | FAA | faa.gov (RGL) | Stall/spin — **url uncertain** if RGL host unreachable |
| AC_00-6B_Aviation_Weather.pdf | Advisory circular | FAA | faa.gov | Aviation weather |
| AC_91-13D_Carburetor_Icing.pdf | Advisory circular | FAA | faa.gov (RGL) | Carb icing — **url uncertain** if RGL host unreachable |
