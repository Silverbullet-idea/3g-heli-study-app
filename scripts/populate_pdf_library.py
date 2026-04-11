"""
Download helicopter document PDFs from configured public URLs into raw-pdfs/.

Run from repo root: .venv\\Scripts\\python.exe scripts/populate_pdf_library.py [--manufacturer NAME]
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

AIRCRAFT_LIBRARY: list[dict[str, Any]] = [
    {
        "aircraft": "Bell 206B Jet Ranger III",
        "manufacturer": "Bell",
        "priority": "tier_2",
        "documents": [
            {
                "type": "flight_manual",
                "filename": "bell_206b3_fm_1.pdf",
                "url": "https://www.mvheli.com/wp-content/uploads/bell-206b3-fm-1.pdf",
                "dest": "raw-pdfs/bell/bell_206b3_fm_1.pdf",
                "source": "mvheli.com",
                "notes": "Bell 206B-3 Flight Manual — public web host",
            },
            {
                "type": "maintenance_manual",
                "filename": "bell_206ab_maintenance_manual.pdf",
                "url": "https://rotorair.ch/uploads/1/4/9/4/149427595/206ab-maintenance_manual.pdf",
                "dest": "raw-pdfs/bell/bell_206ab_maintenance_manual.pdf",
                "source": "rotorair.ch",
                "notes": "Bell 206A/B Maintenance Manual — for technical reference only",
            },
        ],
    },
    {
        "aircraft": "Bell 505 Jet Ranger X",
        "manufacturer": "Bell",
        "priority": "tier_2",
        "documents": [
            {
                "type": "flight_manual",
                "filename": "bell_505_rfm_bht505fm1_rev3.pdf",
                "url": "https://pdfcoffee.com/manual-bell-505-fm-pdf-free.html",
                "dest": "raw-pdfs/bell/bell_505_rfm_bht505fm1_rev3.pdf",
                "source": "pdfcoffee.com (third-party host)",
                "notes": "BHT-505-FM-1 Rev 3, 25 Jul 2018. COPYRIGHT WARNING: Bell Textron proprietary content hosted on third-party site. Confirm legal right to use before processing. ECCN EAR99 applies.",
                "copyright_flag": True,
            },
            {
                "type": "product_specifications",
                "filename": "bell_505_product_specifications_feb2026.pdf",
                "url": "https://www.bellflight.com/-/media/site-specific/bell-flight/documents/products/505/bell-505-product-specifications.pdf",
                "dest": "raw-pdfs/bell/bell_505_product_specifications_feb2026.pdf",
                "source": "bellflight.com (official)",
                "notes": "Official Bell spec sheet Feb 2026 — free public download",
            },
            {
                "type": "type_certificate_data_sheet",
                "filename": "bell_505_easa_tcds_issue4_apr2021.pdf",
                "url": "https://www.easa.europa.eu/en/downloads/43927/en",
                "dest": "raw-pdfs/bell/bell_505_easa_tcds_issue4_apr2021.pdf",
                "source": "easa.europa.eu (official)",
                "notes": "EASA TCDS EASA.IM.R.520 Issue 4, 23 Apr 2021 — official regulatory doc",
            },
            {
                "type": "normal_checklist",
                "filename": "bell_505_normal_checklist_iss1_rev1.pdf",
                "url": "https://www.heli-academy.ch/wp-content/uploads/2023/07/Normal_Checklist_B505_Iss1_Rev1.pdf",
                "dest": "raw-pdfs/bell/bell_505_normal_checklist_iss1_rev1.pdf",
                "source": "heli-academy.ch (third-party training provider)",
                "notes": "Heli Academy Switzerland — Issue 1 Rev 1 2023. Not Bell-issued. Based on RFM but not officially approved by Bell.",
            },
            {
                "type": "emergency_procedures",
                "filename": "bell_505_emergency_procedures_iss1_rev0.pdf",
                "url": "https://www.heli-academy.ch/wp-content/uploads/2023/07/Emergency_Procedures_B505_Iss1_Rev0.pdf",
                "dest": "raw-pdfs/bell/bell_505_emergency_procedures_iss1_rev0.pdf",
                "source": "heli-academy.ch (third-party training provider)",
                "notes": "Heli Academy Switzerland — Issue 1 Rev 0 2023. Not Bell-issued. Use for reference only — verify all steps against official RFM before training use.",
            },
            {
                "type": "mmel",
                "filename": "bell_505_tc_mmel_feb2017.pdf",
                "url": "https://wwwapps2.tc.gc.ca/saf-sec-sur/2/MEL-LEM/tcbbs/mmels/BH_505.pdf",
                "dest": "raw-pdfs/bell/bell_505_tc_mmel_feb2017.pdf",
                "source": "Transport Canada (official)",
                "notes": "Transport Canada Master Minimum Equipment List, original revision 28 Feb 2017. Use wwwapps2.tc.gc.ca path (legacy wwwapps host returned 404).",
            },
        ],
    },
    {
        "aircraft": "Robinson Maintenance Manuals",
        "manufacturer": "Robinson",
        "priority": "tier_1",
        "documents": [
            {
                "type": "maintenance_manual_revision_file",
                "filename": "R22_MM_Revision_NOV2024.pdf",
                "url": "https://robinsonstrapistorprod.blob.core.windows.net/uploads/assets/R22_MM_Revison_File_NOV_2024_ac53652313.pdf",
                "dest": "raw-pdfs/robinson/maintenance-manuals/R22_MM_Revision_NOV2024.pdf",
                "source": "robinsonheli.com (official blob storage)",
                "notes": "R22 MM revision file NOV 2024 — public. Full MM is a paid Robinson publication. Use this for current revision tracking and supplemental content.",
            },
            {
                "type": "maintenance_manual_full",
                "filename": "R22_Maintenance_Manual_full.pdf",
                "url": "https://robinsonstrapistorprod.blob.core.windows.net/uploads/assets/r22_mm_full_book_2024.pdf",
                "dest": "raw-pdfs/robinson/maintenance-manuals/R22_Maintenance_Manual_full.pdf",
                "source": "robinsonheli.com (official blob storage)",
                "notes": "Attempt download — URL pattern inferred from POH naming convention. May 404 if Robinson does not publish full MM publicly. Log result.",
                "url_uncertain": True,
            },
            {
                "type": "maintenance_manual_full",
                "filename": "R44_Maintenance_Manual_full.pdf",
                "url": "https://robinsonstrapistorprod.blob.core.windows.net/uploads/assets/r44_mm_full_book_2024.pdf",
                "dest": "raw-pdfs/robinson/maintenance-manuals/R44_Maintenance_Manual_full.pdf",
                "source": "robinsonheli.com (official blob storage)",
                "notes": "Attempt download — URL pattern inferred. May 404. Log result.",
                "url_uncertain": True,
            },
        ],
    },
    {
        "aircraft": "Lycoming Engine Operator's Manuals",
        "manufacturer": "Lycoming",
        "priority": "tier_1",
        "documents": [
            {
                "type": "engine_operators_manual",
                "filename": "Lycoming_O-320_Operators_Manual_60297-30.pdf",
                "url": "https://yankee-aviation.com/docs/Lycoming%20O-320%20Operators%20Manual.pdf",
                "dest": "raw-pdfs/engines/Lycoming_O-320_Operators_Manual_60297-30.pdf",
                "source": "yankee-aviation.com (public host of Lycoming PN 60297-30)",
                "notes": "Covers O-320-A/B/D/E series — R22 Standard, HP, Alpha engine. Part No. 60297-30.",
            },
            {
                "type": "engine_operators_manual",
                "filename": "Lycoming_O-360_Operators_Manual_60297-12.pdf",
                "url": "https://www.lycoming.com/sites/default/files/attachments/60297-12.pdf",
                "dest": "raw-pdfs/engines/Lycoming_O-360_Operators_Manual_60297-12.pdf",
                "source": "lycoming.com (official)",
                "notes": "Covers O-360-J2A (R22 Beta II engine) and full O/HO/IO/AIO/HIO/TIO-360 series. Part No. 60297-12. If 404, locate current PDF on lycoming.com for document 60297-12.",
                "url_uncertain": True,
            },
            {
                "type": "engine_operators_manual",
                "filename": "Lycoming_O-540_Operators_Manual.pdf",
                "url": "https://www.lycoming.com/sites/default/files/attachments/60297-14.pdf",
                "dest": "raw-pdfs/engines/Lycoming_O-540_Operators_Manual.pdf",
                "source": "lycoming.com (official)",
                "notes": "Covers O-540 series — R44 Raven I engine. Part No. 60297-14. If 404, locate current PDF on lycoming.com for document 60297-14.",
                "url_uncertain": True,
            },
            {
                "type": "engine_operators_manual",
                "filename": "Lycoming_IO-540_Operators_Manual.pdf",
                "url": "https://www.lycoming.com/sites/default/files/attachments/60297-15.pdf",
                "dest": "raw-pdfs/engines/Lycoming_IO-540_Operators_Manual.pdf",
                "source": "lycoming.com (official)",
                "notes": "Covers IO-540 series — R44 Raven II engine. Part No. 60297-15. If 404, locate current PDF on lycoming.com for document 60297-15.",
                "url_uncertain": True,
            },
            {
                "type": "engine_overhaul_manual",
                "filename": "Lycoming_Direct_Drive_Overhaul_Manual.pdf",
                "url": "https://www.expaircraft.com/PDF/Lycoming-OH-Manual.pdf",
                "dest": "raw-pdfs/engines/Lycoming_Direct_Drive_Overhaul_Manual.pdf",
                "source": "expaircraft.com (public host)",
                "notes": "General overhaul procedures for all Lycoming direct-drive engines. Deep technical reference for CFI and commercial systems questions.",
            },
        ],
    },
    {
        "aircraft": "FAA Pilot Handbooks",
        "manufacturer": "FAA",
        "priority": "tier_1",
        "documents": [
            {
                "type": "faa_handbook",
                "filename": "FAA-H-8083-25C_Pilots_Handbook_Aeronautical_Knowledge.pdf",
                "url": "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/faa-h-8083-25c.pdf",
                "dest": "raw-pdfs/faa/FAA-H-8083-25C_Pilots_Handbook_Aeronautical_Knowledge.pdf",
                "source": "faa.gov (official)",
                "notes": "PHAK FAA-H-8083-25C 2023 edition. Source document for weather, airspace, navigation, aeromedical, ADM study sheet content. Covers all knowledge areas tested at private through ATP.",
            },
            {
                "type": "faa_handbook",
                "filename": "FAA-H-8083-15B_Instrument_Flying_Handbook.pdf",
                "url": "https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/FAA-H-8083-15B.pdf",
                "dest": "raw-pdfs/faa/FAA-H-8083-15B_Instrument_Flying_Handbook.pdf",
                "source": "faa.gov (official)",
                "notes": "Already in repo — skip if file exists. Include for completeness in library index.",
            },
            {
                "type": "faa_handbook",
                "filename": "FAA-H-8083-16B_Instrument_Procedures_Handbook.pdf",
                "url": "https://www.faa.gov/sites/faa.gov/files/regulations_policies/handbooks_manuals/aviation/instrument_procedures_handbook/FAA-H-8083-16B.pdf",
                "dest": "raw-pdfs/faa/FAA-H-8083-16B_Instrument_Procedures_Handbook.pdf",
                "source": "faa.gov (official)",
                "notes": "Instrument Procedures Handbook. Required reading for instrument rating study sheets — approaches, holds, IFR departure/arrival procedures.",
            },
            {
                "type": "faa_handbook",
                "filename": "FAA_Aeronautical_Information_Manual_AIM_2024.pdf",
                "url": "https://www.faa.gov/air_traffic/publications/media/AIM_Basic_w_Chg_1_and_2_dtd_1-22-26.pdf",
                "dest": "raw-pdfs/faa/FAA_AIM_2024.pdf",
                "source": "faa.gov (official)",
                "notes": "AIM — current combined basic PDF from Air Traffic Publications (effective dates in filename). Re-download when FAA publishes updates.",
            },
        ],
    },
    {
        "aircraft": "FAA Advisory Circulars",
        "manufacturer": "FAA",
        "priority": "tier_2",
        "documents": [
            {
                "type": "advisory_circular",
                "filename": "AC_61-67D_Stall_Spin_Awareness.pdf",
                "url": "https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/c3cf5bf0e21b5b3386257cfc005c3e2e/$FILE/AC%2061-67D.pdf",
                "dest": "raw-pdfs/faa/advisory-circulars/AC_61-67D_Stall_Spin_Awareness.pdf",
                "source": "faa.gov (official)",
                "notes": "Stall/spin awareness — directly tested at private oral. Examiner favorite. RGL host — if download fails, open the same link in a browser or use FAA AC search.",
                "url_uncertain": True,
            },
            {
                "type": "advisory_circular",
                "filename": "AC_00-6B_Aviation_Weather.pdf",
                "url": "https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_00-6B.pdf",
                "dest": "raw-pdfs/faa/advisory-circulars/AC_00-6B_Aviation_Weather.pdf",
                "source": "faa.gov (official)",
                "notes": "Aviation Weather AC 00-6B. Supplements FAA-H-8083-21B weather chapters. Deep meteorology reference for instrument and commercial study sheets.",
            },
            {
                "type": "advisory_circular",
                "filename": "AC_91-13D_Carburetor_Icing.pdf",
                "url": "https://rgl.faa.gov/Regulatory_and_Guidance_Library/rgAdvisoryCircular.nsf/0/a9b6d8e45f1e26ae862569ac006b6e96/$FILE/AC91-13D.pdf",
                "dest": "raw-pdfs/faa/advisory-circulars/AC_91-13D_Carburetor_Icing.pdf",
                "source": "faa.gov (official)",
                "notes": "Carburetor icing AC. Directly relevant to R22/R44 operations — examiner will ask about this. RGL host — if download fails, open the same link in a browser or use FAA AC search.",
                "url_uncertain": True,
            },
        ],
    },
]

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download PDFs listed in AIRCRAFT_LIBRARY into raw-pdfs/."
    )
    p.add_argument(
        "--manufacturer",
        metavar="NAME",
        help="Only download documents for this manufacturer (case-insensitive), e.g. bell",
    )
    return p.parse_args()


def filter_library(
    library: list[dict[str, Any]], manufacturer: str | None
) -> list[dict[str, Any]]:
    if not manufacturer:
        return library
    m = manufacturer.casefold().strip()
    return [e for e in library if e.get("manufacturer", "").casefold().strip() == m]


def download_one(url: str, dest: Path, timeout: float = 300.0) -> int:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_UA},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def copyright_warning(filename: str) -> None:
    print(
        f"WARNING: {filename} is flagged as potentially copyrighted Bell Textron\n"
        "content hosted on a third-party site. Skipping automatic download.\n"
        "Review manually and confirm legal right to use before adding to repo."
    )


def main() -> int:
    args = parse_args()
    entries = filter_library(AIRCRAFT_LIBRARY, args.manufacturer)
    if not entries:
        print(
            "No aircraft entries match the filter.",
            file=sys.stderr,
        )
        return 1

    downloaded: list[tuple[str, int]] = []
    skipped_existing: list[tuple[str, int]] = []
    skipped_copyright: list[str] = []
    failed: list[tuple[str, str]] = []
    failed_uncertain: list[tuple[str, str]] = []
    total_bytes = 0

    for entry in entries:
        aircraft = entry.get("aircraft", "?")
        for doc in entry.get("documents", []):
            filename = doc.get("filename", "?")
            url = doc.get("url", "")
            dest_rel = doc.get("dest", "")
            dest = REPO_ROOT / dest_rel
            uncertain = bool(doc.get("url_uncertain"))

            print(f"[{aircraft}] {filename}", flush=True)

            if doc.get("copyright_flag"):
                copyright_warning(filename)
                skipped_copyright.append(filename)
                continue

            if dest.exists() and dest.stat().st_size > 0:
                sz = dest.stat().st_size
                skipped_existing.append((dest_rel, sz))
                print(
                    f"  SKIP (already exists): {dest_rel} ({sz:,} bytes)",
                    flush=True,
                )
                continue

            if uncertain:
                print(
                    f"NOTE: {filename} URL is inferred/uncertain — attempting download.\n"
                    "If this fails, manual URL lookup required. Logging result.",
                    flush=True,
                )

            try:
                n = download_one(url, dest)
                total_bytes += n
                downloaded.append((dest_rel, n))
                print(f"  OK -> {dest_rel} ({n:,} bytes)", flush=True)
            except urllib.error.HTTPError as e:
                reason = f"HTTP {e.code}"
                if uncertain:
                    failed_uncertain.append((filename, reason))
                    print(
                        f"FAILED (uncertain URL): {filename} — find correct URL manually",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    failed.append((filename, reason))
                    print(
                        f"  FAILED: HTTP {e.code} ({filename})",
                        file=sys.stderr,
                        flush=True,
                    )
            except urllib.error.URLError as e:
                reason = f"URL error: {e.reason}"
                if uncertain:
                    failed_uncertain.append((filename, reason))
                    print(
                        f"FAILED (uncertain URL): {filename} — find correct URL manually",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    failed.append((filename, reason))
                    print(
                        f"  FAILED: {e.reason} ({filename})",
                        file=sys.stderr,
                        flush=True,
                    )
            except TimeoutError as e:
                reason = str(e)
                if uncertain:
                    failed_uncertain.append((filename, reason))
                    print(
                        f"FAILED (uncertain URL): {filename} — find correct URL manually",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    failed.append((filename, reason))
                    print(
                        f"  FAILED: timeout ({filename})",
                        file=sys.stderr,
                        flush=True,
                    )
            except OSError as e:
                reason = str(e)
                if uncertain:
                    failed_uncertain.append((filename, reason))
                    print(
                        f"FAILED (uncertain URL): {filename} — find correct URL manually",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    failed.append((filename, reason))
                    print(
                        f"  FAILED: {e} ({filename})",
                        file=sys.stderr,
                        flush=True,
                    )

            time.sleep(0.5)

    print()
    print("=== Summary ===")
    print(f"Successfully downloaded ({len(downloaded)}):")
    for path, n in downloaded:
        print(f"  - {path} ({n:,} bytes)")
    print(f"Total size of newly downloaded PDFs: {total_bytes:,} bytes")
    print()
    print(f"Skipped (already exist) ({len(skipped_existing)}):")
    for path, sz in skipped_existing:
        print(f"  - {path} ({sz:,} bytes)")
    print()
    print(f"Skipped due to copyright_flag ({len(skipped_copyright)}):")
    for p in skipped_copyright:
        print(f"  - {p}")
    print()
    print(f"Failed (uncertain URL — expected possible) ({len(failed_uncertain)}):")
    for name, reason in failed_uncertain:
        print(f"  - {name}: {reason}")
    print()
    print(f"Failed (unexpected) ({len(failed)}):")
    for name, reason in failed:
        print(f"  - {name}: {reason}")

    return 0 if not failed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
