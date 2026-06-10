#!/usr/bin/env python3
"""Render branded PDF study sheets from data/study_sheet_specs/*.json."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "data" / "study_sheet_specs"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "study_sheets"
ASSETS_DIR = REPO_ROOT / "assets"

PAGE_W, PAGE_H = letter
MARGIN_TOP = 0.6 * 72
MARGIN_LEFT = 0.5 * 72
MARGIN_RIGHT = 0.5 * 72
HEADER_HEIGHT = 1.1 * 72
HEADER_RULE_Y = PAGE_H - HEADER_HEIGHT
CONTENT_TOP = HEADER_RULE_Y - 8
FOOTER_RULE_Y = 36
CONTENT_BOTTOM_Y = FOOTER_RULE_Y + 12
CONTENT_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_GAP = 14
LEFT_COL_W = (CONTENT_WIDTH - COL_GAP) * 0.47
RIGHT_COL_W = (CONTENT_WIDTH - COL_GAP) * 0.53
LEFT_COL_X = MARGIN_LEFT
RIGHT_COL_X = MARGIN_LEFT + LEFT_COL_W + COL_GAP

ORANGE = HexColor("#E8650A")
BLUE = HexColor("#4B5EBF")
BLACK = HexColor("#1A1A1A")
WHITE = HexColor("#FFFFFF")
GRAY_LIGHT = HexColor("#F5F5F5")
GRAY_RULE = HexColor("#E0E0E0")
GRAY_NOTE = HexColor("#666666")
GRAY_FOOTER = HexColor("#888888")

LOGO_FILENAME = "AILogoFinal.png"
WATERMARK_FILENAME = "HeliOnlyLarge.png"
LOGO_WIDTH = 1.8 * 72
WATERMARK_SIZE = 3.5 * 72
WATERMARK_X = PAGE_W / 2
WATERMARK_Y = PAGE_H / 2

RATING_BADGE_TEXT = {
    "private": "PRIVATE PILOT",
    "commercial": "COMMERCIAL PILOT",
    "instrument": "INSTRUMENT",
    "cfi": "CERTIFIED FLIGHT INSTRUCTOR",
}

FONT_SECTION = "Helvetica-Bold"
FONT_LABEL = "Helvetica-Bold"
FONT_VALUE = "Helvetica"
FONT_NOTE = "Helvetica-Oblique"
FONT_FOOTER = "Helvetica"
FONT_AIRCRAFT = "Helvetica-Bold"
FONT_SUBLINE = "Helvetica-Oblique"

SIZE_SECTION = 9
SIZE_LABEL = 8
SIZE_VALUE = 8
SIZE_NOTE = 7
SIZE_FOOTER = 6.5
SIZE_AIRCRAFT = 14
SIZE_BADGE = 8
SIZE_SUBLINE = 7

SECTION_PAD_TOP = 4
SECTION_PAD_BOTTOM = 3
SECTION_RULE = 0.5
SECTION_GAP_AFTER = 6
ROW_PAD = 3
ROW_INDENT = 4
NOTE_EXTRA_INDENT = 4
ROW_HEIGHT = 14
ROW_HEIGHT_NOTE = 20
ITEM_LABEL_FRAC = 0.60


@dataclass
class LayoutBlock:
    kind: str
    section: dict[str, Any] | None = None
    item: dict[str, Any] | None = None
    item_index: int = 0
    height: float = 0


@dataclass
class ColumnState:
    x: float
    width: float
    y: float


@dataclass
class PageLayout:
    columns: list[ColumnState] = field(default_factory=list)
    blocks: list[tuple[int, int, LayoutBlock]] = field(default_factory=list)


def ensure_assets() -> tuple[Path | None, Path | None]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    logo_path = ASSETS_DIR / LOGO_FILENAME
    watermark_path = ASSETS_DIR / WATERMARK_FILENAME

    search_roots = [
        REPO_ROOT.parent,
        REPO_ROOT,
        REPO_ROOT.parent / "assets",
    ]
    names = {
        logo_path: (LOGO_FILENAME, "3G_Heli_Prep_Logo-A3.png", "logo_horizontal.png"),
        watermark_path: (WATERMARK_FILENAME, "BlackLogoHeliOnly.png", "heli_icon.png"),
    }

    for dest, candidates in names.items():
        if dest.is_file():
            continue
        found: Path | None = None
        for root in search_roots:
            if not root.exists():
                continue
            for name in candidates:
                for match in root.rglob(name):
                    if match.is_file():
                        found = match
                        break
                if found:
                    break
            if found:
                break
        if found:
            shutil.copy2(found, dest)
            print(f"Copied asset: {found} -> {dest}")
        else:
            warnings.warn(f"Asset not found: {dest.name} — header/watermark may be skipped")

    logo = logo_path if logo_path.is_file() else None
    watermark = watermark_path if watermark_path.is_file() else None
    return logo, watermark


def wrap_text(text: str, font: str, size: float, max_width: float, c: canvas.Canvas) -> list[str]:
    if not text.strip():
        return [""]
    words = text.replace("\n", " ").split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if c.stringWidth(trial, font, size) <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def item_row_height(item: dict[str, Any], col_width: float, c: canvas.Canvas) -> float:
    base = ROW_HEIGHT_NOTE if item.get("note") else ROW_HEIGHT
    value_w = col_width * (1 - ITEM_LABEL_FRAC) - ROW_INDENT
    value_lines = wrap_text(str(item.get("value", "")), FONT_VALUE, SIZE_VALUE, value_w, c)
    extra = max(0, len(value_lines) - 1) * (SIZE_VALUE + 2)
    return max(base, ROW_HEIGHT + extra)


def section_header_height() -> float:
    return SECTION_PAD_TOP + SIZE_SECTION + SECTION_PAD_BOTTOM + SECTION_RULE


def section_total_height(section: dict[str, Any], col_width: float, c: canvas.Canvas) -> float:
    total = section_header_height()
    for item in section.get("items") or []:
        total += item_row_height(item, col_width, c)
    total += SECTION_GAP_AFTER
    return total


def min_section_fit_height(section: dict[str, Any], col_width: float, c: canvas.Canvas) -> float:
    items = section.get("items") or []
    item_heights = [item_row_height(it, col_width, c) for it in items[:2]]
    return section_header_height() + sum(item_heights)


def build_blocks(spec: dict[str, Any]) -> list[LayoutBlock]:
    blocks: list[LayoutBlock] = []
    for section in spec.get("sections") or []:
        blocks.append(LayoutBlock(kind="section_start", section=section))
        for idx, item in enumerate(section.get("items") or []):
            blocks.append(
                LayoutBlock(kind="item", section=section, item=item, item_index=idx)
            )
        blocks.append(LayoutBlock(kind="section_end", section=section))
    return blocks


def compute_block_height(block: LayoutBlock, col_width: float, c: canvas.Canvas) -> float:
    if block.kind == "section_start":
        return section_header_height()
    if block.kind == "section_end":
        return SECTION_GAP_AFTER
    if block.kind == "item" and block.item:
        return item_row_height(block.item, col_width, c)
    return 0


def layout_spec(spec: dict[str, Any], c: canvas.Canvas) -> tuple[list[PageLayout], int]:
    blocks = build_blocks(spec)
    col_widths = [LEFT_COL_W, RIGHT_COL_W]
    col_x = [LEFT_COL_X, RIGHT_COL_X]

    pages: list[PageLayout] = [PageLayout()]
    page_idx = 0
    col_idx = 0
    y = CONTENT_TOP

    def start_new_page() -> None:
        nonlocal page_idx, col_idx, y
        page_idx += 1
        pages.append(PageLayout())
        col_idx = 0
        y = CONTENT_TOP

    def start_next_column() -> None:
        nonlocal col_idx, y
        if col_idx == 0:
            col_idx = 1
            y = CONTENT_TOP
        else:
            start_new_page()

    i = 0
    while i < len(blocks):
        block = blocks[i]
        width = col_widths[col_idx]

        if block.kind == "section_start" and block.section:
            remaining = y - CONTENT_BOTTOM_Y
            section = block.section
            min_fit = min_section_fit_height(section, width, c)
            if remaining < min_fit:
                start_next_column()
                width = col_widths[col_idx]

            section_blocks: list[LayoutBlock] = [block]
            j = i + 1
            while j < len(blocks) and blocks[j].kind != "section_end":
                section_blocks.append(blocks[j])
                j += 1
            if j < len(blocks):
                section_blocks.append(blocks[j])

            section_height = sum(compute_block_height(b, width, c) for b in section_blocks)
            remaining = y - CONTENT_BOTTOM_Y
            if remaining < section_height:
                start_next_column()
                width = col_widths[col_idx]
                remaining = y - CONTENT_BOTTOM_Y
                if remaining < section_height:
                    start_new_page()
                    width = col_widths[col_idx]

            for sb in section_blocks:
                h = compute_block_height(sb, width, c)
                pages[page_idx].blocks.append((col_idx, y, sb))
                pages[page_idx].columns = [
                    ColumnState(col_x[0], col_widths[0], CONTENT_TOP),
                    ColumnState(col_x[1], col_widths[1], CONTENT_TOP),
                ]
                y -= h
            i = j + 1
            continue

        h = compute_block_height(block, width, c)
        if y - h < CONTENT_BOTTOM_Y:
            start_next_column()
            width = col_widths[col_idx]
            if y - h < CONTENT_BOTTOM_Y:
                start_new_page()
                width = col_widths[col_idx]

        pages[page_idx].blocks.append((col_idx, y, block))
        y -= h
        i += 1

    return pages, len(pages)


def draw_watermark(c: canvas.Canvas, img_path: Path | None) -> None:
    if not img_path or not img_path.is_file():
        return
    try:
        img = PILImage.open(img_path).convert("RGBA")
        _r, _g, _b, alpha = img.split()
        alpha = alpha.point(lambda i: int(i * 0.07))
        img.putalpha(alpha)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(
            ImageReader(buf),
            WATERMARK_X - WATERMARK_SIZE / 2,
            WATERMARK_Y - WATERMARK_SIZE / 2,
            width=WATERMARK_SIZE,
            height=WATERMARK_SIZE,
            mask="auto",
        )
    except Exception as exc:
        print(f"Warning: watermark skipped — {exc}")


def draw_header(
    c: canvas.Canvas,
    spec: dict[str, Any],
    logo_path: Path | None,
) -> None:
    header_top = PAGE_H
    header_bottom = HEADER_RULE_Y
    logo_h = LOGO_WIDTH * 0.28
    logo_x = MARGIN_LEFT
    logo_y = (header_top + header_bottom) / 2 - logo_h / 2

    if logo_path and logo_path.is_file():
        try:
            c.drawImage(
                ImageReader(str(logo_path)),
                logo_x,
                logo_y,
                width=LOGO_WIDTH,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception as exc:
            print(f"Warning: logo skipped — {exc}")
            logo_h = 0
            logo_y = header_top - 20
    else:
        print("Warning: logo skipped — AILogoFinal.png not found")
        logo_h = 0
        logo_y = header_top - 20

    rule_x = logo_x + LOGO_WIDTH + 8
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(1)
    c.line(rule_x, logo_y, rule_x, logo_y + logo_h)

    text_x = rule_x + 8
    aircraft_name = spec.get("aircraft_name", "Aircraft")
    c.setFillColor(BLUE)
    c.setFont(FONT_AIRCRAFT, SIZE_AIRCRAFT)
    name_y = header_top - MARGIN_TOP - SIZE_AIRCRAFT
    c.drawString(text_x, name_y, aircraft_name)

    rating = spec.get("rating", "private").lower()
    badge_text = RATING_BADGE_TEXT.get(rating, rating.upper())
    c.setFont(FONT_SECTION, SIZE_BADGE)
    badge_pad_x = 8
    badge_pad_y = 3
    badge_w = c.stringWidth(badge_text, FONT_SECTION, SIZE_BADGE) + 2 * badge_pad_x
    badge_h = SIZE_BADGE + 2 * badge_pad_y
    badge_y = name_y - badge_h - 6
    c.setFillColor(ORANGE)
    c.roundRect(text_x, badge_y, badge_w, badge_h, badge_h / 2, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.drawString(text_x + badge_pad_x, badge_y + badge_pad_y, badge_text)

    subline = "By the author of the ASA Helicopter Oral Exam Guide"
    c.setFillColor(GRAY_FOOTER)
    c.setFont(FONT_SUBLINE, SIZE_SUBLINE)
    c.drawString(text_x, badge_y - 10, subline)

    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, HEADER_RULE_Y, PAGE_W - MARGIN_RIGHT, HEADER_RULE_Y)


def draw_footer(
    c: canvas.Canvas,
    spec: dict[str, Any],
    page_num: int,
    total_pages: int,
) -> None:
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, FOOTER_RULE_Y, PAGE_W - MARGIN_RIGHT, FOOTER_RULE_Y)

    c.setFillColor(GRAY_FOOTER)
    c.setFont(FONT_FOOTER, SIZE_FOOTER)
    text_y = FOOTER_RULE_Y - 10

    left = "3GHeliPrep.com"
    c.drawString(MARGIN_LEFT, text_y, left)

    rating_label = spec.get("rating", "private").replace("_", " ").title()
    center = f"{spec.get('aircraft_name', 'Aircraft')} | {rating_label} Study Sheet"
    if total_pages > 1:
        center += f" — Page {page_num} of {total_pages}"
    center_w = c.stringWidth(center, FONT_FOOTER, SIZE_FOOTER)
    c.drawString((PAGE_W - center_w) / 2, text_y, center)

    right = "© 2026 3GSI LLC. All rights reserved."
    right_w = c.stringWidth(right, FONT_FOOTER, SIZE_FOOTER)
    c.drawString(PAGE_W - MARGIN_RIGHT - right_w, text_y, right)


def draw_section_header(c: canvas.Canvas, x: float, width: float, y: float, title: str) -> float:
    y -= SECTION_PAD_TOP
    c.setFillColor(BLUE)
    c.setFont(FONT_SECTION, SIZE_SECTION)
    text = title.upper()
    c.drawString(x, y - SIZE_SECTION, text)
    y -= SIZE_SECTION + SECTION_PAD_BOTTOM
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(SECTION_RULE)
    c.line(x, y, x + width, y)
    return y - SECTION_RULE


def draw_item_row(
    c: canvas.Canvas,
    x: float,
    width: float,
    y_top: float,
    item: dict[str, Any],
    row_index: int,
) -> float:
    row_h = item_row_height(item, width, c)
    y_bottom = y_top - row_h
    bg = WHITE if row_index % 2 == 0 else GRAY_LIGHT
    c.setFillColor(bg)
    c.rect(x, y_bottom, width, row_h, stroke=0, fill=1)

    inner_x = x + ROW_INDENT
    inner_w = width - ROW_INDENT
    label_w = inner_w * ITEM_LABEL_FRAC
    value_w = inner_w * (1 - ITEM_LABEL_FRAC)

    label = str(item.get("label", ""))
    value = str(item.get("value", ""))
    note = item.get("note")

    text_y = y_top - ROW_PAD - SIZE_LABEL
    c.setFillColor(BLACK)
    c.setFont(FONT_LABEL, SIZE_LABEL)
    c.drawString(inner_x, text_y, label)

    if note:
        c.setFillColor(GRAY_NOTE)
        c.setFont(FONT_NOTE, SIZE_NOTE)
        c.drawString(inner_x + NOTE_EXTRA_INDENT, text_y - SIZE_NOTE - 2, str(note))

    value_lines = wrap_text(value, FONT_VALUE, SIZE_VALUE, value_w, c)
    c.setFillColor(BLACK)
    c.setFont(FONT_VALUE, SIZE_VALUE)
    vy = y_top - ROW_PAD - SIZE_VALUE
    for line in value_lines:
        line_w = c.stringWidth(line, FONT_VALUE, SIZE_VALUE)
        c.drawString(inner_x + inner_w - line_w, vy, line)
        vy -= SIZE_VALUE + 2

    return y_bottom


def render_block(
    c: canvas.Canvas,
    col_idx: int,
    y: float,
    block: LayoutBlock,
) -> None:
    x = LEFT_COL_X if col_idx == 0 else RIGHT_COL_X
    width = LEFT_COL_W if col_idx == 0 else RIGHT_COL_W

    if block.kind == "section_start" and block.section:
        draw_section_header(c, x, width, y, block.section.get("section_title", ""))
    elif block.kind == "item" and block.item is not None:
        draw_item_row(c, x, width, y, block.item, block.item_index)


def render_pdf(
    spec_path: Path,
    output_dir: Path,
    logo_path: Path | None,
    watermark_path: Path | None,
) -> Path:
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    aircraft_id = spec.get("aircraft_id", spec_path.stem.split("_")[0])
    rating = spec.get("rating", "private")
    out_name = f"{aircraft_id}_{rating}_study_sheet.pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / out_name

    layout_buf = io.BytesIO()
    probe = canvas.Canvas(layout_buf, pagesize=letter)
    pages, total_pages = layout_spec(spec, probe)

    pdf = canvas.Canvas(str(out_path), pagesize=letter)
    for page_num, page in enumerate(pages, start=1):
        draw_watermark(pdf, watermark_path)
        draw_header(pdf, spec, logo_path)
        for col_idx, y, block in page.blocks:
            render_block(pdf, col_idx, y, block)
        draw_footer(pdf, spec, page_num, total_pages)
        if page_num < total_pages:
            pdf.showPage()

    pdf.save()
    print(f"Rendered {out_path.relative_to(REPO_ROOT)} ({total_pages} page(s))")
    return out_path


def discover_specs(aircraft: str | None) -> list[Path]:
    if not SPECS_DIR.is_dir():
        print(f"Specs directory not found: {SPECS_DIR}", file=sys.stderr)
        sys.exit(1)
    paths = sorted(SPECS_DIR.glob("*_study_sheet.json"))
    if aircraft:
        needle = f"{aircraft.lower()}_"
        paths = [p for p in paths if p.name.startswith(needle)]
        if not paths:
            print(f"No spec found for aircraft '{aircraft}' in {SPECS_DIR}", file=sys.stderr)
            sys.exit(1)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Render branded PDF study sheets from spec JSON.")
    ap.add_argument("--aircraft", default=None, help="Aircraft slug (e.g. r22). Default: all specs.")
    ap.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)})",
    )
    args = ap.parse_args()

    logo_path, watermark_path = ensure_assets()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir

    specs = discover_specs(args.aircraft)
    print(f"Rendering {len(specs)} study sheet(s) -> {output_dir.relative_to(REPO_ROOT)}")

    for spec_path in specs:
        render_pdf(spec_path, output_dir, logo_path, watermark_path)

    print("Done.")


if __name__ == "__main__":
    main()
