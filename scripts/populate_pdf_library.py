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

    downloaded: list[str] = []
    skipped_copyright: list[str] = []
    failed: list[tuple[str, str]] = []
    total_bytes = 0

    for entry in entries:
        aircraft = entry.get("aircraft", "?")
        for doc in entry.get("documents", []):
            filename = doc.get("filename", "?")
            url = doc.get("url", "")
            dest_rel = doc.get("dest", "")
            dest = REPO_ROOT / dest_rel

            print(f"[{aircraft}] {filename}", flush=True)

            if doc.get("copyright_flag"):
                copyright_warning(filename)
                skipped_copyright.append(filename)
                continue

            try:
                n = download_one(url, dest)
                total_bytes += n
                downloaded.append(dest_rel)
                print(f"  OK -> {dest_rel} ({n:,} bytes)", flush=True)
            except urllib.error.HTTPError as e:
                failed.append((filename, f"HTTP {e.code}"))
                print(
                    f"  FAILED: HTTP {e.code} ({filename})",
                    file=sys.stderr,
                    flush=True,
                )
            except urllib.error.URLError as e:
                failed.append((filename, f"URL error: {e.reason}"))
                print(
                    f"  FAILED: {e.reason} ({filename})",
                    file=sys.stderr,
                    flush=True,
                )
            except TimeoutError as e:
                failed.append((filename, str(e)))
                print(
                    f"  FAILED: timeout ({filename})",
                    file=sys.stderr,
                    flush=True,
                )
            except OSError as e:
                failed.append((filename, str(e)))
                print(
                    f"  FAILED: {e} ({filename})",
                    file=sys.stderr,
                    flush=True,
                )

            time.sleep(0.5)

    print()
    print("=== Summary ===")
    print(f"Successfully downloaded ({len(downloaded)}):")
    for p in downloaded:
        print(f"  - {p}")
    print(f"Total size of downloaded PDFs: {total_bytes:,} bytes")
    print()
    print(f"Skipped due to copyright_flag ({len(skipped_copyright)}):")
    for p in skipped_copyright:
        print(f"  - {p}")
    print()
    print(f"Failed ({len(failed)}):")
    for name, reason in failed:
        print(f"  - {name}: {reason}")

    return 0 if not failed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
