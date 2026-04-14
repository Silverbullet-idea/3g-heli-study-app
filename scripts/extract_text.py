#!/usr/bin/env python3
"""Extract plain text from a PDF for manual review (page markers between pages)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from a PDF to extracted-data/raw-text/")
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the PDF file relative to the repository root",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output path relative to repo root (default: extracted-data/raw-text/<pdf_stem>.txt)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    pdf_path = (repo_root / args.pdf).resolve()

    if not pdf_path.is_file():
        print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
        raise SystemExit(1)

    if args.output:
        out_path = (repo_root / args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = repo_root / "extracted-data" / "raw-text"
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = pdf_path.stem
        out_path = out_dir / f"{stem}.txt"

    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            parts.append(f"\n--- PAGE {i} ---\n")
            parts.append(text)

    out_path.write_text("".join(parts), encoding="utf-8", newline="\n")
    print(f"Extracted {num_pages} pages -> {out_path}")


if __name__ == "__main__":
    main()
