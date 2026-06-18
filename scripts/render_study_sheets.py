#!/usr/bin/env python3
"""Render branded PDF study sheets (v2) from data/study_sheet_specs/*.json."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "data" / "study_sheet_specs"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "study_sheets"
ASSETS_DIR = REPO_ROOT / "assets"
FAA_DATA_DIR = REPO_ROOT / "extracted-data" / "faa"

HFH_JSON = "FAA-H-8083-21B_Helicopter_Flying_Handbook.json"
WBA_JSON = "FAA-H-8083-1B_Weight_Balance_Handbook.json"
IFH_JSON = "FAA-H-8083-15B_Instrument_Flying_Handbook.json"
ACS_PRIVATE_JSON = "FAA-S-ACS-15_Private_Helicopter_ACS.json"

PAGE_W = 612
PAGE_H = 792
MARGIN_TOP = 32.4
MARGIN_LEFT = 32.4
MARGIN_RIGHT = 32.4
MARGIN_BOTTOM = 28.8
CONTENT_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_GAP = 12
COL_A_W = CONTENT_WIDTH * 0.47
COL_B_W = CONTENT_WIDTH - COL_A_W - COL_GAP
COL_A_X = MARGIN_LEFT
COL_B_X = MARGIN_LEFT + COL_A_W + COL_GAP

LOGO_TOP_Y = PAGE_H - MARGIN_TOP
FOOTER_RULE_Y = MARGIN_BOTTOM
FOOTER_TEXT_Y = FOOTER_RULE_Y - 9
CONTENT_BOTTOM_Y = FOOTER_RULE_Y + 14

ORANGE = HexColor("#E8650A")
BLUE = HexColor("#4B5EBF")
BLACK = HexColor("#1A1A1A")
WHITE = HexColor("#FFFFFF")
GRAY_LIGHT = HexColor("#F5F5F5")
GRAY_RULE = HexColor("#E0E0E0")
BLUE_TINT = HexColor("#EEF0FA")
STEP_ORANGE = HexColor("#E8650A")
GRAY_SUBTITLE = HexColor("#888888")
GRAY_LABEL = HexColor("#888888")
GRAY_NOTE = HexColor("#777777")
GRAY_FOOTER = HexColor("#999999")

LOGO_MAX_W = 160
LOGO_MAX_H = 36
QR_BAND_H = 22
QR_BAND_RADIUS = 2
SECTION_HEADER_H = 16
ACCENT_BAR_W = 3

COL_A_SECTIONS = ("limitations", "instrument_markings")
COL_B_SECTIONS = ("emergency_procedures", "systems")

STEP_RE = re.compile(r"\d+\.")


@dataclass
class Spacing:
    section_gap: float = 4.0
    row_height: float = 13.0
    row_height_note: float = 19.0
    post_header_gap: float = 2.0
    emergency_step_h: float = 11.0
    emergency_proc_h: float = 13.0


@dataclass
class PlacedItem:
    kind: str
    y_top: float
    section_id: str = ""
    section_title: str = ""
    item: dict[str, Any] | None = None
    row_index: int = 0
    steps: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class PageLayout:
    col_a: list[PlacedItem] = field(default_factory=list)
    col_b: list[PlacedItem] = field(default_factory=list)
    lowest_y: float = CONTENT_BOTTOM_Y


def draw_watermark(c: canvas.Canvas, img_path: str | Path, page_width: float, page_height: float) -> None:
    try:
        img = PILImage.open(img_path).convert("RGBA")
        r, g, b, a = img.split()
        a = a.point(lambda i: int(i * 0.07))
        img.putalpha(a)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        size = 310
        x = (page_width - size) / 2
        y = (page_height - size) / 2
        c.drawImage(ImageReader(buf), x, y, width=size, height=size, mask="auto")
    except Exception as e:
        print(f"  Warning: watermark skipped — {e}")


def resolve_assets() -> tuple[Path | None, Path | None]:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    watermark_path = ASSETS_DIR / "HeliOnlyLarge.png"
    logo_horizontal = ASSETS_DIR / "logo_horizontal.png"
    logo_final = ASSETS_DIR / "AILogoFinal.png"

    if not watermark_path.is_file():
        for candidate in ("HeliOnlyLarge.png", "BlackLogoHeliOnly.png", "heli_icon.png"):
            for match in REPO_ROOT.rglob(candidate):
                if match.is_file() and match.stat().st_size > 1000:
                    print(f"  Warning: HeliOnlyLarge.png missing — using {match.name}")
                    watermark_path = match
                    break
            if watermark_path.is_file() and watermark_path.stat().st_size > 1000:
                break
        if not watermark_path.is_file() or watermark_path.stat().st_size <= 1000:
            print("  Warning: watermark asset missing — watermark will be skipped")
            watermark_path = None  # type: ignore[assignment]

    if logo_horizontal.is_file() and logo_horizontal.stat().st_size > 1000:
        logo_path = logo_horizontal
    elif logo_final.is_file() and logo_final.stat().st_size > 1000:
        logo_path = logo_final
    else:
        logo_path = None
        for candidate in (
            "logo_horizontal.png",
            "AILogoFinal.png",
            "AI-Logo---Final.png",
            "Logo-and-Text-ONLY.png",
            "3G_Heli_Prep_Logo-A3.png",
        ):
            for match in REPO_ROOT.rglob(candidate):
                if match.is_file() and match.stat().st_size > 1000:
                    logo_path = match
                    break
            if logo_path:
                break
        if not logo_path:
            print("  Warning: logo asset missing — logo will be skipped")

    return logo_path, watermark_path  # type: ignore[return-value]


def section_by_id(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["section_id"]: s for s in spec.get("sections") or [] if s.get("section_id")}


def find_item_value(items: list[dict[str, Any]], *patterns: str) -> str | None:
    for pattern in patterns:
        pl = pattern.lower()
        for item in items:
            label = str(item.get("label", "")).lower()
            if pl in label:
                return str(item.get("value", ""))
    return None


def truncate_value(value: str, max_len: int = 12) -> str:
    value = value.strip()
    if len(value) <= max_len:
        return value
    if "see poh" in value.lower():
        return "See POH"
    return value[: max_len - 1] + "…"


def extract_quick_reference(spec: dict[str, Any]) -> list[tuple[str, str]]:
    sections = section_by_id(spec)
    lim_items = sections.get("limitations", {}).get("items") or []
    inst_items = sections.get("instrument_markings", {}).get("items") or []
    sys_items = sections.get("systems", {}).get("items") or []

    refs: list[tuple[str, str]] = []

    vne = find_item_value(lim_items, "vne")
    if vne:
        refs.append((truncate_value(vne), "VNE"))

    mgw = find_item_value(lim_items, "max gross weight", "maximum gross weight")
    if mgw:
        refs.append((truncate_value(mgw), "Max Gross Wt"))

    fuel = find_item_value(lim_items, "fuel capacity", "usable fuel")
    if fuel:
        refs.append((truncate_value(fuel), "Fuel Cap."))

    engine = find_item_value(lim_items, "engine power", "takeoff power", "max power")
    if not engine:
        engine = find_item_value(lim_items, "engine", "turbine")
    if not engine:
        engine = find_item_value(sys_items, "engine", "powerplant")
    if engine:
        label = "Engine Pwr" if any(k in engine.lower() for k in ("hp", "shp", "kw")) else "Engine"
        refs.append((truncate_value(engine), label))

    mda = find_item_value(lim_items, "max density altitude", "maximum density altitude")
    if not mda:
        mda = find_item_value(lim_items, "max operating altitude", "maximum operating altitude", "service ceiling")
    if mda:
        refs.append((truncate_value(mda), "Max DA"))

    nr_val = find_item_value(inst_items, "rotor rpm green (power on)", "nr green", "power-on rpm", "power on")
    if not nr_val:
        nr_val = find_item_value(lim_items, "power-on rpm", "power on rpm", "nr range")
    if nr_val:
        refs.append((truncate_value(f"NR: {nr_val.replace('NR', '').strip()}", 14), "NR Range"))

    return refs[:6]


def parse_emergency_steps(value: str) -> list[tuple[str, str]]:
    parts = STEP_RE.split(value)
    numbers = STEP_RE.findall(value)
    steps: list[tuple[str, str]] = []
    for num, text in zip(numbers, parts[1:], strict=False):
        cleaned = text.strip().strip("-").strip()
        if cleaned:
            steps.append((num.rstrip("."), cleaned))
    if not steps and value.strip():
        steps.append(("1", value.strip()))
    return steps


def build_aircraft_data_items(spec: dict[str, Any]) -> list[dict[str, Any]]:
    sections = section_by_id(spec)
    systems = sections.get("systems", {})
    lim_items = sections.get("limitations", {}).get("items") or []
    sys_items = list(systems.get("items") or [])

    extras: list[dict[str, Any]] = []
    for label_key, patterns in (
        ("max gross weight", ("max gross weight", "maximum gross weight")),
        ("min gross weight", ("min gross weight", "minimum gross weight")),
        ("fuel capacity", ("fuel capacity usable", "fuel capacity", "usable fuel")),
    ):
        val = find_item_value(lim_items, *patterns)
        if val:
            extras.append({"label": label_key.title(), "value": val})

    engine = find_item_value(lim_items, "engine power", "takeoff power", "engine model", "engine")
    if engine:
        extras.append({"label": "Engine", "value": engine})

    combined = sys_items + extras
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in combined:
        key = str(item.get("label", "")).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def prepare_sections(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = section_by_id(spec)
    col_a: list[dict[str, Any]] = []
    col_b: list[dict[str, Any]] = []

    for sid in COL_A_SECTIONS:
        if sid in by_id:
            col_a.append(by_id[sid])

    for sid in COL_B_SECTIONS:
        if sid not in by_id:
            continue
        sec = dict(by_id[sid])
        if sid == "systems":
            sec = {
                **sec,
                "section_title": "AIRCRAFT DATA",
                "items": build_aircraft_data_items(spec),
            }
        col_b.append(sec)

    return col_a, col_b


def row_height(item: dict[str, Any], spacing: Spacing) -> float:
    return spacing.row_height_note if item.get("note") else spacing.row_height


def emergency_block_height(item: dict[str, Any], spacing: Spacing) -> float:
    steps = parse_emergency_steps(str(item.get("value", "")))
    return spacing.emergency_proc_h + len(steps) * spacing.emergency_step_h


def section_block_height(section: dict[str, Any], col_width: float, spacing: Spacing) -> float:
    sid = section.get("section_id", "")
    h = SECTION_HEADER_H + 0.5 + spacing.post_header_gap
    for idx, item in enumerate(section.get("items") or []):
        if sid == "emergency_procedures":
            h += emergency_block_height(item, spacing)
        else:
            h += row_height(item, spacing)
    return h


def _column_list(page: PageLayout, col: str) -> list[PlacedItem]:
    return page.col_a if col == "a" else page.col_b


def _item_bottom(item: PlacedItem, spacing: Spacing) -> float:
    if item.kind == "section_header":
        return item.y_top - SECTION_HEADER_H - 0.5 - spacing.post_header_gap
    if item.kind == "emergency_proc" and item.item:
        return item.y_top - emergency_block_height(item.item, spacing)
    if item.kind == "row" and item.item:
        return item.y_top - row_height(item.item, spacing)
    return item.y_top


def _page_lowest(page: PageLayout, spacing: Spacing) -> float:
    bottoms = [_item_bottom(i, spacing) for i in page.col_a + page.col_b]
    return min(bottoms) if bottoms else CONTENT_BOTTOM_Y


def layout_column(
    sections: list[dict[str, Any]],
    col_key: str,
    sections_start_y: float,
    spacing: Spacing,
) -> tuple[list[PageLayout], float]:
    col_w = COL_A_W if col_key == "a" else COL_B_W
    pages: list[PageLayout] = [PageLayout()]
    page_idx = 0
    y = sections_start_y
    global_lowest = sections_start_y

    def new_page() -> None:
        nonlocal page_idx, y
        page_idx += 1
        pages.append(PageLayout())
        y = sections_start_y

    def target() -> list[PlacedItem]:
        return _column_list(pages[page_idx], col_key)

    for sec_idx, section in enumerate(sections):
        if sec_idx > 0:
            y -= spacing.section_gap

        block_h = section_block_height(section, col_w, spacing)
        if y - block_h < CONTENT_BOTTOM_Y:
            new_page()

        title = section.get("section_title", "")
        sid = section.get("section_id", "")
        target().append(
            PlacedItem(kind="section_header", y_top=y, section_id=sid, section_title=title)
        )
        y -= SECTION_HEADER_H + 0.5 + spacing.post_header_gap

        for row_idx, item in enumerate(section.get("items") or []):
            if sid == "emergency_procedures":
                eh = emergency_block_height(item, spacing)
                if y - eh < CONTENT_BOTTOM_Y:
                    new_page()
                steps = parse_emergency_steps(str(item.get("value", "")))
                target().append(
                    PlacedItem(
                        kind="emergency_proc",
                        y_top=y,
                        section_id=sid,
                        item=item,
                        steps=steps,
                    )
                )
                y -= eh
            else:
                rh = row_height(item, spacing)
                if y - rh < CONTENT_BOTTOM_Y:
                    new_page()
                target().append(
                    PlacedItem(
                        kind="row",
                        y_top=y,
                        section_id=sid,
                        item=item,
                        row_index=row_idx,
                    )
                )
                y -= rh

        global_lowest = min(global_lowest, y)

    for pg in pages:
        pg.lowest_y = _page_lowest(pg, spacing)

    return pages, global_lowest


def merge_pages(pages_a: list[PageLayout], pages_b: list[PageLayout]) -> list[PageLayout]:
    count = max(len(pages_a), len(pages_b), 1)
    merged: list[PageLayout] = []
    for i in range(count):
        pa = pages_a[i] if i < len(pages_a) else PageLayout()
        pb = pages_b[i] if i < len(pages_b) else PageLayout()
        merged.append(
            PageLayout(
                col_a=pa.col_a,
                col_b=pb.col_b,
                lowest_y=min(pa.lowest_y, pb.lowest_y),
            )
        )
    return merged


def logo_draw_height(logo_path: Path | None) -> float:
    if logo_path and logo_path.is_file():
        try:
            with PILImage.open(logo_path) as img:
                iw, ih = img.size
            scale = min(LOGO_MAX_W / iw, LOGO_MAX_H / ih)
            return ih * scale
        except Exception:
            pass
    return LOGO_MAX_H


def header_y_positions(logo_path: Path | None) -> tuple[float, float]:
    """Return (content_start_y, sections_start_y) without drawing."""
    logo_h = logo_draw_height(logo_path)
    logo_bottom = LOGO_TOP_Y - logo_h
    name_y = logo_bottom - 5 - 16
    sub_y = name_y - 3 - 7
    rule_y = sub_y - 6
    content_start_y = rule_y
    sections_start_y = content_start_y - 4 - QR_BAND_H - 6 - 0.5
    return content_start_y, sections_start_y


def draw_header(
    c: canvas.Canvas,
    spec: dict[str, Any],
    logo_path: Path | None,
) -> tuple[float, float]:
    """Draw header block; return (content_start_y, sections_start_y)."""
    aircraft_name = spec.get("aircraft_name", "Aircraft")
    logo_bottom = LOGO_TOP_Y

    if logo_path and logo_path.is_file():
        try:
            with PILImage.open(logo_path) as img:
                iw, ih = img.size
            scale = min(LOGO_MAX_W / iw, LOGO_MAX_H / ih)
            draw_w = iw * scale
            draw_h = ih * scale
            logo_x = (PAGE_W - draw_w) / 2
            logo_y = LOGO_TOP_Y - draw_h
            c.drawImage(
                ImageReader(str(logo_path)),
                logo_x,
                logo_y,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            logo_bottom = logo_y
        except Exception as e:
            print(f"  Warning: logo skipped — {e}")
    else:
        print("  Warning: logo skipped — asset not found")

    name_y = logo_bottom - 5 - 16
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 16)
    name_w = c.stringWidth(aircraft_name, "Helvetica-Bold", 16)
    c.drawString((PAGE_W - name_w) / 2, name_y, aircraft_name)

    subtitle = "By the author of the ASA Helicopter Oral Exam Guide"
    sub_y = name_y - 3 - 7
    c.setFillColor(GRAY_SUBTITLE)
    c.setFont("Helvetica-Oblique", 7)
    sub_w = c.stringWidth(subtitle, "Helvetica-Oblique", 7)
    c.drawString((PAGE_W - sub_w) / 2, sub_y, subtitle)

    rule_y = sub_y - 6
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, rule_y, MARGIN_LEFT + CONTENT_WIDTH, rule_y)

    sections_start_y = rule_y - 4 - QR_BAND_H - 6 - 0.5
    return rule_y, sections_start_y


def draw_quick_reference(
    c: canvas.Canvas,
    spec: dict[str, Any],
    content_start_y: float,
) -> float:
    band_top = content_start_y - 4 - QR_BAND_H
    band_x = MARGIN_LEFT
    c.setFillColor(GRAY_LIGHT)
    c.roundRect(band_x, band_top, CONTENT_WIDTH, QR_BAND_H, QR_BAND_RADIUS, stroke=0, fill=1)

    refs = extract_quick_reference(spec)
    if not refs:
        sections_start_y = band_top - 6 - 0.5
        c.setStrokeColor(GRAY_RULE)
        c.setLineWidth(0.5)
        c.line(MARGIN_LEFT, sections_start_y, MARGIN_LEFT + CONTENT_WIDTH, sections_start_y)
        return sections_start_y

    n = len(refs)
    slot_w = CONTENT_WIDTH / n
    for i, (value, label) in enumerate(refs):
        cx = band_x + slot_w * i + slot_w / 2
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 8.5)
        vw = c.stringWidth(value, "Helvetica-Bold", 8.5)
        c.drawString(cx - vw / 2, band_top + QR_BAND_H - 10, value)

        c.setFillColor(GRAY_LABEL)
        c.setFont("Helvetica", 6)
        lw = c.stringWidth(label, "Helvetica", 6)
        c.drawString(cx - lw / 2, band_top + 3, label)

        if i > 0:
            div_x = band_x + slot_w * i
            c.setStrokeColor(GRAY_RULE)
            c.setLineWidth(0.5)
            c.line(div_x, band_top + 3, div_x, band_top + QR_BAND_H - 3)

    sections_start_y = band_top - 6 - 0.5
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, sections_start_y, MARGIN_LEFT + CONTENT_WIDTH, sections_start_y)
    return sections_start_y


def draw_section_header(
    c: canvas.Canvas,
    x: float,
    width: float,
    y_top: float,
    title: str,
) -> None:
    y_bottom = y_top - SECTION_HEADER_H
    c.setFillColor(ORANGE)
    c.rect(x, y_bottom, ACCENT_BAR_W, SECTION_HEADER_H, stroke=0, fill=1)

    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 8)
    text = title.upper()
    text_y = y_bottom + (SECTION_HEADER_H - 8) / 2
    c.drawString(x + ACCENT_BAR_W + 5, text_y, text)

    rule_y = y_bottom - 0.5
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(0.5)
    c.line(x, rule_y, x + width, rule_y)


def draw_standard_row(
    c: canvas.Canvas,
    x: float,
    width: float,
    y_top: float,
    item: dict[str, Any],
    row_index: int,
    spacing: Spacing,
    use_blue_tint: bool = False,
) -> None:
    has_note = bool(item.get("note"))
    rh = spacing.row_height_note if has_note else spacing.row_height
    y_bottom = y_top - rh

    if use_blue_tint:
        bg = BLUE_TINT if row_index % 2 == 0 else WHITE
    else:
        bg = WHITE if row_index % 2 == 0 else GRAY_LIGHT
    c.setFillColor(bg)
    c.rect(x, y_bottom, width, rh, stroke=0, fill=1)

    pad = 8
    label_x = x + pad
    label_col_w = width * 0.35 - pad
    value_right = x + width - 4

    label = str(item.get("label", ""))
    value = str(item.get("value", ""))
    note = item.get("note")

    if has_note:
        text_y = y_top - 7
    else:
        text_y = y_bottom + (rh - 7.5) / 2

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(label_x, text_y, label)

    c.setFont("Helvetica", 7.5)
    vw = c.stringWidth(value, "Helvetica", 7.5)
    c.drawString(value_right - vw, text_y, value)

    if note:
        c.setFillColor(GRAY_NOTE)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(label_x + 6, text_y - 9, str(note))


def draw_emergency_block(
    c: canvas.Canvas,
    x: float,
    width: float,
    y_top: float,
    item: dict[str, Any],
    steps: list[tuple[str, str]],
    spacing: Spacing,
) -> None:
    proc_h = spacing.emergency_proc_h
    y_proc_bottom = y_top - proc_h
    c.setFillColor(GRAY_LIGHT)
    c.rect(x, y_proc_bottom, width, proc_h, stroke=0, fill=1)

    label = str(item.get("label", ""))
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 8, y_proc_bottom + (proc_h - 7.5) / 2, label)

    step_y = y_proc_bottom
    pad = 8
    for num, text in steps:
        step_y -= spacing.emergency_step_h
        c.setFillColor(WHITE)
        c.rect(x, step_y, width, spacing.emergency_step_h, stroke=0, fill=1)

        c.setFillColor(STEP_ORANGE)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x + pad + 4, step_y + 2, num)

        c.setFillColor(BLACK)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + pad + 18, step_y + 2, text)


def draw_footer(
    c: canvas.Canvas,
    spec: dict[str, Any],
    page_num: int,
    total_pages: int,
) -> None:
    c.setStrokeColor(GRAY_RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, FOOTER_RULE_Y, MARGIN_LEFT + CONTENT_WIDTH, FOOTER_RULE_Y)

    c.setFillColor(GRAY_FOOTER)
    c.setFont("Helvetica", 6)
    c.drawString(MARGIN_LEFT, FOOTER_TEXT_Y, "3GHeliPrep.com")

    aircraft = spec.get("aircraft_name", "Aircraft")
    center = f"{aircraft} | Helicopter Study Sheet"
    if total_pages > 1:
        center += f" — Page {page_num} of {total_pages}"
    cw = c.stringWidth(center, "Helvetica", 6)
    c.drawString((PAGE_W - cw) / 2, FOOTER_TEXT_Y, center)

    right = "© 2026 3GSI LLC. All rights reserved."
    rw = c.stringWidth(right, "Helvetica", 6)
    c.drawString(MARGIN_LEFT + CONTENT_WIDTH - rw, FOOTER_TEXT_Y, right)


def layout_spec(
    spec: dict[str, Any],
    spacing: Spacing,
    logo_path: Path | None,
) -> tuple[list[PageLayout], float, float]:
    _content_start_y, sections_start_y = header_y_positions(logo_path)

    col_a_secs, col_b_secs = prepare_sections(spec)
    pages_a, low_a = layout_column(col_a_secs, "a", sections_start_y, spacing)
    pages_b, low_b = layout_column(col_b_secs, "b", sections_start_y, spacing)
    pages = merge_pages(pages_a, pages_b)

    lowest = min(low_a, low_b)
    if len(pages) == 1:
        lowest = pages[0].lowest_y
    available = sections_start_y - MARGIN_BOTTOM
    used = sections_start_y - lowest
    fill_ratio = used / available if available > 0 else 1.0
    return pages, fill_ratio, sections_start_y


def column_total_height(sections: list[dict[str, Any]], col_w: float, spacing: Spacing) -> float:
    if not sections:
        return 0.0
    total = 0.0
    for idx, section in enumerate(sections):
        if idx > 0:
            total += spacing.section_gap
        total += section_block_height(section, col_w, spacing)
    return total


def try_fit_spacing(
    spec: dict[str, Any],
    logo_path: Path | None,
    spacing: Spacing,
) -> Spacing:
    """Tighten spacing slightly so borderline sheets fit on one page."""
    _, sections_start_y = header_y_positions(logo_path)
    available = sections_start_y - CONTENT_BOTTOM_Y
    col_a_secs, col_b_secs = prepare_sections(spec)
    col_w_a = COL_A_W
    col_w_b = COL_B_W

    for _ in range(8):
        pages, _, _ = layout_spec(spec, spacing, logo_path)
        if len(pages) == 1:
            return spacing
        h_a = column_total_height(col_a_secs, col_w_a, spacing)
        h_b = column_total_height(col_b_secs, col_w_b, spacing)
        overflow = max(h_a, h_b) - available
        if overflow <= 0 or overflow > 80:
            return spacing
        factor = max(0.92, (available - 4) / max(h_a, h_b))
        spacing = Spacing(
            section_gap=max(2.0, spacing.section_gap * factor),
            row_height=max(11.5, spacing.row_height * factor),
            row_height_note=max(16.0, spacing.row_height_note * factor),
            post_header_gap=max(1.0, spacing.post_header_gap * factor),
            emergency_step_h=max(9.5, spacing.emergency_step_h * factor),
            emergency_proc_h=max(11.0, spacing.emergency_proc_h * factor),
        )
    return spacing


def count_layout_units(spec: dict[str, Any]) -> tuple[int, int, int]:
    col_a_secs, col_b_secs = prepare_sections(spec)
    section_gaps = max(0, len(col_a_secs) + len(col_b_secs) - 2)
    rows = 0
    for sec in col_a_secs + col_b_secs:
        if sec.get("section_id") != "emergency_procedures":
            rows += len(sec.get("items") or [])
    return section_gaps, rows, len(col_a_secs) + len(col_b_secs)


def auto_adjust_spacing(
    spacing: Spacing,
    fill_ratio: float,
    sections_start_y: float,
    lowest_y: float,
    spec: dict[str, Any],
) -> Spacing:
    if fill_ratio >= 0.88:
        return spacing

    available = sections_start_y - MARGIN_BOTTOM
    used = sections_start_y - lowest_y
    extra = (available - used) * 0.85
    section_gaps, rows, n_sections = count_layout_units(spec)

    s = Spacing(
        section_gap=spacing.section_gap,
        row_height=spacing.row_height,
        row_height_note=spacing.row_height_note,
        post_header_gap=spacing.post_header_gap,
        emergency_step_h=spacing.emergency_step_h,
        emergency_proc_h=spacing.emergency_proc_h,
    )
    if section_gaps:
        s.section_gap += (extra * 0.40) / section_gaps
    if rows:
        row_add = min((18.0 - s.row_height), (extra * 0.35) / rows)
        s.row_height += row_add
        s.row_height_note = min(24.0, s.row_height_note + row_add)
    if n_sections:
        s.post_header_gap += (extra * 0.25) / n_sections
    return s


def render_page_content(
    c: canvas.Canvas,
    spec: dict[str, Any],
    page: PageLayout,
    spacing: Spacing,
) -> None:
    for item in page.col_a:
        if item.kind == "section_header":
            draw_section_header(c, COL_A_X, COL_A_W, item.y_top, item.section_title)
        elif item.kind == "row" and item.item:
            use_tint = item.section_id == "systems"
            draw_standard_row(c, COL_A_X, COL_A_W, item.y_top, item.item, item.row_index, spacing, use_tint)
        elif item.kind == "emergency_proc" and item.item:
            draw_emergency_block(c, COL_A_X, COL_A_W, item.y_top, item.item, item.steps, spacing)

    for item in page.col_b:
        if item.kind == "section_header":
            draw_section_header(c, COL_B_X, COL_B_W, item.y_top, item.section_title)
        elif item.kind == "row" and item.item:
            use_tint = item.section_id == "systems"
            draw_standard_row(c, COL_B_X, COL_B_W, item.y_top, item.item, item.row_index, spacing, use_tint)
        elif item.kind == "emergency_proc" and item.item:
            draw_emergency_block(c, COL_B_X, COL_B_W, item.y_top, item.item, item.steps, spacing)


# ---------------------------------------------------------------------------
# General knowledge-domain sheets (FAA handbook JSON + hardcoded FAR/NTSB)
# ---------------------------------------------------------------------------

FAR_61_91_ITEMS: list[dict[str, str]] = [
    {"label": "PIC Responsibility", "value": "91.3 — PIC directly responsible for safe operation"},
    {"label": "Student Pilot Min Age", "value": "61.103 — 16 years (rotorcraft category)"},
    {"label": "Private Pilot Min Age", "value": "61.103 — 17 years"},
    {"label": "Private Pilot — Total Time", "value": "61.109 — 40 hours minimum"},
    {"label": "Private Pilot — Dual", "value": "61.109 — 20 hours flight training"},
    {"label": "Private Pilot — Solo", "value": "61.109 — 10 hours solo (3 cross-country)"},
    {"label": "Passenger Currency", "value": "61.57 — 3 takeoffs/landings in 90 days (same category/class)"},
    {"label": "Night Passenger Currency", "value": "61.57 — 3 full-stop night T/O & Ldg in 90 days"},
    {"label": "Flight Review", "value": "61.56 — Flight review every 24 calendar months"},
    {"label": "Preflight Action", "value": "91.103 — PIC must become familiar with all available info"},
    {"label": "VFR Fuel Reserve (Day)", "value": "91.151 — 30 min reserve at normal cruise"},
    {"label": "VFR Fuel Reserve (Night)", "value": "91.151 — 45 min reserve at normal cruise"},
    {"label": "VFR Min — Class G Day (<1,200 AGL)", "value": "91.155 — 1 SM visibility, clear of clouds"},
    {"label": "VFR Min — Class G Night (<1,200 AGL)", "value": "91.155 — 1 SM, 1,000 ft ceiling, clear of clouds"},
    {"label": "VFR Min — Class E Day (<10,000 MSL)", "value": "91.155 — 3 SM, 500 below/1,000 above/2,000 horizontal"},
    {"label": "VFR Min — Class E Night (<10,000 MSL)", "value": "91.155 — 3 SM, 1,000 ft ceiling, 500/1,000/2,000"},
    {"label": "A TOMATO FLAMES (Day VFR)", "value": "91.205 — Altimeter, Tach, Oil temp, Manifold, Airspeed, Temperature, Oil pressure, Fuel, Landing gear, Anti-collision, Manifold, ELT, Seat belts"},
    {"label": "Required Documents (ARROW)", "value": "91.203 — Airworthiness cert, Registration, Radio (if req), Operating limitations, Weight & balance"},
]

NTSB_830_ITEMS: list[dict[str, str]] = [
    {"label": "Accident Definition", "value": "830.2 — Occurrence involving death/serious injury OR substantial aircraft damage"},
    {"label": "Serious Injury", "value": "830.2 — Hospitalization >48 hrs, fracture, severe hemorrhage, nerve/muscle/tendon damage, internal organ injury, 2nd/3rd degree burns >5%"},
    {"label": "Substantial Damage", "value": "830.2 — Damage affecting structural strength, performance, or flight characteristics; requires major repair"},
    {"label": "Immediate Notification", "value": "830.5 — Fatal/serious injury, substantial damage, or missing aircraft"},
    {"label": "Report Within 10 Days", "value": "830.15 — Written NTSB Form 6120.1/2 when requested or for serious injury/substantial damage"},
    {"label": "Preserve Wreckage", "value": "830.10 — Preserve all evidence; do not disturb before NTSB/authorized party takes custody"},
    {"label": "Annual Inspection", "value": "91.409 — Every 12 calendar months by IA; return to service entry required"},
    {"label": "100-Hour Inspection", "value": "91.409 — Required if aircraft used for hire OR flight instruction for hire"},
    {"label": "Progressive Inspection", "value": "91.409 — FAA-approved program; each segment at 100-hr or per program"},
    {"label": "MEL Operations", "value": "91.213 — FAA-approved MEL + LOA required; mandatory when issued"},
    {"label": "91.213(d) Deferral", "value": "Part 91 without MEL — placard INOPERATIVE; repair before further flight (not in-flight)"},
    {"label": "Form 337", "value": "43.9/43 Appendix B — Major repair or alteration record; filed with FAA"},
    {"label": "Airworthiness Directives", "value": "91.403 — AD compliance mandatory; no person may operate unless complied with"},
    {"label": "Preventive Maintenance", "value": "Part 43 App A — Pilot may perform limited items on owned aircraft (not rotorcraft in all cases — verify 43.3)"},
]

_FAA_CACHE: dict[str, dict[str, Any]] = {}


def _load_faa_json(filename: str, faa_data_dir: Path) -> dict[str, Any]:
    if filename not in _FAA_CACHE:
        path = faa_data_dir / filename
        if not path.is_file():
            print(f"  Warning: FAA JSON not found — {path}")
            _FAA_CACHE[filename] = {}
        else:
            with open(path, encoding="utf-8") as f:
                _FAA_CACHE[filename] = json.load(f)
    return _FAA_CACHE[filename]


def _topics_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {t["id"]: t for t in data.get("topics") or [] if t.get("id")}


def _get_acs_task(acs: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for area in acs.get("areas_of_operation") or []:
        for task in area.get("tasks") or []:
            if task.get("id") == task_id:
                return task
    return None


def _matches_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    tl = text.lower()
    return any(kw in tl for kw in keywords)


def _filter_terms(
    terms: list[dict[str, str]],
    keywords: tuple[str, ...],
) -> list[dict[str, str]]:
    return [t for t in terms if _matches_keywords(t.get("term", "") + " " + t.get("definition", ""), keywords)]


def _filter_points(points: list[str], keywords: tuple[str, ...]) -> list[str]:
    return [p for p in points if _matches_keywords(p, keywords)]


def _format_key_value(kv: dict[str, Any]) -> str:
    val = kv.get("value")
    unit = str(kv.get("unit") or "").strip()
    notes = str(kv.get("notes") or "").strip()
    parts: list[str] = []
    if val is not None and str(val).strip() not in ("", "None"):
        parts.append(f"{val}{(' ' + unit) if unit else ''}")
    elif unit:
        parts.append(unit)
    if notes:
        parts.append(notes)
    return " — ".join(parts) if parts else str(kv.get("item", ""))


def _terms_to_items(terms: list[dict[str, str]], max_items: int = 50) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for t in terms[:max_items]:
        items.append({"label": t.get("term", ""), "value": t.get("definition", "")})
    return items


def _points_to_items(points: list[str], max_items: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, p in enumerate(points[:max_items]):
        label = p.split("—")[0].split(":")[0].strip()
        if len(label) > 45:
            label = f"Key Point {i + 1}"
        items.append({"label": label, "value": p})
    return items


def _key_values_to_items(key_values: list[dict[str, Any]], max_items: int = 20) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for kv in key_values[:max_items]:
        items.append({"label": str(kv.get("item", "")), "value": _format_key_value(kv)})
    return items


def _acs_knowledge_items(task: dict[str, Any] | None, max_items: int = 25) -> list[dict[str, Any]]:
    if not task:
        return []
    items: list[dict[str, Any]] = []
    for line in (task.get("knowledge") or [])[:max_items]:
        text = str(line)
        if ".K" in text[:12]:
            text = text.split(" ", 1)[-1] if " " in text else text
        label = text[:50] + "…" if len(text) > 50 else text
        items.append({"label": label, "value": text})
    return items


def _expand_acs_subitems(knowledge_lines: list[str], code_prefix: str) -> list[dict[str, Any]]:
    """Split ACS knowledge bullets (e.g. K2/K3 with a. b. c.) into study-sheet rows."""
    items: list[dict[str, Any]] = []
    for line in knowledge_lines:
        text = str(line)
        if code_prefix not in text:
            continue
        body = text.split(" ", 1)[-1] if " " in text else text
        if " such as:" in body.lower():
            head, rest = body.split(" such as:", 1)
            items.append({"label": head.strip()[:45], "value": head.strip()})
            parts = re.split(r";\s*([a-l])\.\s*", rest)
            if len(parts) > 1:
                for i in range(1, len(parts), 2):
                    letter = parts[i]
                    content = parts[i + 1].strip().rstrip(".")
                    items.append({"label": f"({letter})", "value": content})
            else:
                items.append({"label": "Details", "value": rest.strip()})
        else:
            items.append({"label": body[:45], "value": body})
    return items


def _acs_rm_items(task: dict[str, Any] | None, max_items: int = 10) -> list[dict[str, Any]]:
    if not task:
        return []
    items: list[dict[str, Any]] = []
    for line in (task.get("risk_management") or [])[:max_items]:
        text = str(line)
        if ".R" in text[:12]:
            text = text.split(" ", 1)[-1] if " " in text else text
        items.append({"label": "Risk Factor", "value": text})
    return items


def _topic_items(
    topic: dict[str, Any] | None,
    *,
    term_keywords: tuple[str, ...] = (),
    point_keywords: tuple[str, ...] = (),
    include_all_terms: bool = False,
    include_summary: bool = True,
    max_items: int = 45,
) -> list[dict[str, Any]]:
    if not topic:
        return []
    items: list[dict[str, Any]] = []
    if include_summary and topic.get("summary"):
        items.append({"label": "Overview", "value": str(topic["summary"])})
    terms = topic.get("key_terms") or []
    if term_keywords:
        terms = _filter_terms(terms, term_keywords)
    elif not include_all_terms:
        terms = terms[:20]
    items.extend(_terms_to_items(terms, max_items=max_items))
    points = topic.get("key_points") or []
    if point_keywords:
        points = _filter_points(points, point_keywords)
    remaining = max(0, max_items - len(items))
    if remaining and points:
        items.extend(_points_to_items(points, max_items=remaining))
    kv = topic.get("key_values") or []
    remaining = max(0, max_items - len(items))
    if remaining and kv:
        items.extend(_key_values_to_items(kv, max_items=remaining))
    for m in (topic.get("mnemonics") or [])[:5]:
        items.append(
            {
                "label": str(m.get("mnemonic", "Mnemonic")),
                "value": str(m.get("meaning", "")),
                "note": str(m.get("notes", "")) or None,
            }
        )
    return items[:max_items]


def _merge_items(*groups: list[dict[str, Any]], max_items: int = 50) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            key = str(item.get("label", "")).strip().lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= max_items:
                return merged
    return merged


def build_general_sections(faa_data_dir: Path) -> list[dict[str, Any]]:
    hfh = _load_faa_json(HFH_JSON, faa_data_dir)
    wba = _load_faa_json(WBA_JSON, faa_data_dir)
    ifh = _load_faa_json(IFH_JSON, faa_data_dir)
    acs = _load_faa_json(ACS_PRIVATE_JSON, faa_data_dir)
    ht = _topics_index(hfh)
    wt = _topics_index(wba)
    it = _topics_index(ifh)

    weather_task = _get_acs_task(acs, "weather_information")
    airspace_task = _get_acs_task(acs, "national_airspace_system")
    flight_plan_task = _get_acs_task(acs, "cross_country_flight_planning")
    human_factors_task = _get_acs_task(acs, "human_factors")
    airport_markings_task = _get_acs_task(acs, "runway_taxiway_heliport_helipad_signs_markings_lighting")
    traffic_pattern_task = _get_acs_task(acs, "traffic_patterns")

    sections: list[dict[str, Any]] = []

    sections.append(
        {
            "section_id": "helicopter_systems",
            "section_title": "Helicopter Systems",
            "items": _merge_items(
                _topic_items(
                    ht.get("helicopter_components_sections_systems"),
                    term_keywords=(
                        "rotor", "engine", "electrical", "fuel", "transmission", "drivetrain",
                        "turbine", "carburetor", "hydraulic", "clutch", "freewheel", "swash",
                        "antitorque", "tail rotor", "notar", "fenestron", "bearing", "mast",
                    ),
                    include_summary=True,
                    max_items=40,
                ),
                _topic_items(
                    ht.get("introduction_to_helicopter"),
                    term_keywords=("rotor", "engine", "turbine", "main rotor", "antitorque"),
                    include_summary=False,
                    max_items=10,
                ),
            ),
        }
    )

    sections.append(
        {
            "section_id": "instruments_avionics",
            "section_title": "Instruments & Avionics",
            "items": _merge_items(
                _topic_items(it.get("flight_instruments"), include_all_terms=True, max_items=25),
                _topic_items(it.get("gyroscopic_instruments"), include_all_terms=True, max_items=15),
                _topic_items(it.get("magnetic_compass"), include_all_terms=True, max_items=12),
                _topic_items(it.get("airspeed_indicator"), include_all_terms=True, max_items=10),
                _topic_items(
                    ht.get("helicopter_components_sections_systems"),
                    term_keywords=("tachometer", "instrument", "rpm", "itt", "egt", "torque"),
                    include_summary=False,
                    max_items=8,
                ),
            ),
        }
    )

    aero = ht.get("aerodynamics_of_flight") or {}
    hazards = ht.get("helicopter_emergencies_hazards") or {}
    sections.append(
        {
            "section_id": "aerodynamics_basics",
            "section_title": "Aerodynamics Basics",
            "items": _topic_items(
                aero,
                term_keywords=(
                    "airfoil", "angle of attack", "aoa", "chord", "relative wind", "incidence",
                    "resultant", "induced flow", "downwash", "pitch", "feather", "coning",
                ),
                include_summary=True,
                max_items=35,
            ),
        }
    )

    sections.append(
        {
            "section_id": "four_aerodynamic_forces",
            "section_title": "Four Aerodynamic Forces",
            "items": _merge_items(
                _topic_items(
                    aero,
                    term_keywords=(
                        "lift", "weight", "thrust", "drag", "bernoulli", "newton",
                        "profile drag", "induced drag", "parasite",
                    ),
                    include_summary=False,
                    max_items=25,
                ),
                _points_to_items(
                    _filter_points(
                        aero.get("key_points") or [],
                        ("lift", "drag", "thrust", "weight", "bernoulli"),
                    ),
                    max_items=8,
                ),
            ),
        }
    )

    sections.append(
        {
            "section_id": "aerodynamic_principles",
            "section_title": "Aerodynamic Principles",
            "items": _merge_items(
                _topic_items(
                    aero,
                    term_keywords=(
                        "ground effect", "translational lift", "etl", "dissymmetry", "translating",
                        "coriolis", "precession", "pendular", "flapping", "vortex",
                    ),
                    include_summary=False,
                    max_items=30,
                ),
                _topic_items(
                    ht.get("helicopter_flight_controls"),
                    term_keywords=("cyclic", "collective", "pedal", "control", "swash", "feather"),
                    include_summary=True,
                    max_items=12,
                ),
            ),
        }
    )

    sections.append(
        {
            "section_id": "aerodynamic_hazards",
            "section_title": "Aerodynamic Hazards",
            "items": _topic_items(
                hazards,
                term_keywords=(
                    "vortex ring", "lte", "dynamic rollover", "retreating blade", "mast bump",
                    "low-g", "ground resonance", "overpitch", "vrs", "settling",
                ),
                include_summary=True,
                max_items=35,
            ),
        }
    )

    auto_points = _filter_points(
        hazards.get("key_points") or [],
        ("autorotation", "freewheel", "touchdown", "rpm"),
    )
    sections.append(
        {
            "section_id": "autorotations",
            "section_title": "Autorotations",
            "items": _merge_items(
                _topic_items(
                    hazards,
                    term_keywords=("autorotation", "freewheel", "power recovery", "touchdown", "overpitch"),
                    include_summary=False,
                    max_items=25,
                ),
                _topic_items(
                    ht.get("basic_flight_maneuvers"),
                    term_keywords=("autorotation", "power-off", "glide"),
                    include_summary=False,
                    max_items=10,
                ),
                _points_to_items(auto_points, max_items=10),
            ),
        }
    )

    weather_theory_items = _expand_acs_subitems(weather_task.get("knowledge") or [] if weather_task else [], "PH.I.C.K3")
    sections.append(
        {
            "section_id": "weather_theory",
            "section_title": "Weather Theory",
            "items": weather_theory_items or [{"label": "Meteorology", "value": "See ACS PH.I.C.K3 — atmospheric science topics"}],
        }
    )

    weather_info_items = _merge_items(
        _expand_acs_subitems(weather_task.get("knowledge") or [] if weather_task else [], "PH.I.C.K2"),
        _acs_knowledge_items(weather_task, max_items=4),
        _acs_rm_items(weather_task, max_items=6),
    )
    weather_info_items = [i for i in weather_info_items if "K3" not in i.get("value", "")]
    sections.append(
        {
            "section_id": "weather_information",
            "section_title": "Weather Information",
            "items": weather_info_items,
        }
    )

    sections.append(
        {
            "section_id": "weight_balance",
            "section_title": "Weight & Balance",
            "items": _merge_items(
                _topic_items(wt.get("weight_balance_control_fundamentals"), include_all_terms=True, max_items=15),
                _topic_items(wt.get("weight_balance_theory"), include_all_terms=True, max_items=20),
                _topic_items(wt.get("helicopter_weight_balance"), include_all_terms=True, max_items=15),
                _topic_items(wt.get("key_formulas_summary"), include_all_terms=True, max_items=10),
                _topic_items(ht.get("weight_and_balance"), include_all_terms=True, max_items=10),
            ),
        }
    )

    sections.append(
        {
            "section_id": "navigation",
            "section_title": "Navigation",
            "items": _merge_items(
                _topic_items(it.get("navigation_systems"), include_all_terms=True, max_items=25),
                _topic_items(it.get("magnetic_compass"), include_all_terms=True, max_items=10),
                _acs_knowledge_items(flight_plan_task, max_items=8),
            ),
        }
    )

    sections.append(
        {
            "section_id": "flight_planning",
            "section_title": "Flight Planning",
            "items": _merge_items(
                _acs_knowledge_items(flight_plan_task, max_items=15),
                _acs_rm_items(flight_plan_task, max_items=8),
                _topic_items(
                    hazards,
                    term_keywords=("lost", "four c", "climb", "communicate"),
                    include_summary=False,
                    max_items=5,
                ),
                _acs_knowledge_items(traffic_pattern_task, max_items=8),
            ),
        }
    )

    sections.append(
        {
            "section_id": "airspace",
            "section_title": "Airspace",
            "items": _merge_items(
                _topic_items(
                    it.get("national_airspace_system"),
                    term_keywords=("class ", "airspace", "special use", "tfr", "prohibited", "restricted", "moa", "warning"),
                    include_summary=True,
                    max_items=30,
                ),
                _acs_knowledge_items(airspace_task, max_items=10),
                _acs_rm_items(airspace_task, max_items=5),
            ),
        }
    )

    sections.append(
        {
            "section_id": "airport_operations",
            "section_title": "Airport Operations",
            "items": _merge_items(
                _acs_knowledge_items(airport_markings_task, max_items=10),
                _acs_knowledge_items(traffic_pattern_task, max_items=8),
                _topic_items(
                    ht.get("night_flight_operations"),
                    term_keywords=("light", "beacon", "marking", "vasi", "papi", "runway", "taxiway", "sign"),
                    include_summary=False,
                    max_items=12,
                ),
                _topic_items(
                    ht.get("night_operations"),
                    term_keywords=("light", "beacon", "marking", "navigation light"),
                    include_summary=False,
                    max_items=8,
                ),
            ),
        }
    )

    sections.append(
        {
            "section_id": "aeromedical_factors",
            "section_title": "Aeromedical Factors",
            "items": _merge_items(
                _acs_knowledge_items(human_factors_task, max_items=15),
                _topic_items(
                    ht.get("night_operations"),
                    term_keywords=("hypoxia", "vision", "disorientation", "illusion", "fatigue", "adaptation", "myopia"),
                    include_summary=True,
                    max_items=15,
                ),
                [{"label": "IMSAFE", "value": "Illness, Medication, Stress, Alcohol, Fatigue, Emotion — personal fitness checklist"}],
            ),
        }
    )

    sections.append(
        {
            "section_id": "aeronautical_decision_making",
            "section_title": "Aeronautical Decision Making",
            "items": _topic_items(
                ht.get("aeronautical_decision_making"),
                term_keywords=("pave", "3p", "5p", "decide", "ooda", "crm", "srm", "hazardous", "attitude", "complacency", "automation", "risk", "situational"),
                include_summary=True,
                max_items=40,
            ),
        }
    )

    sections.append(
        {
            "section_id": "far_61_91",
            "section_title": "FAR Parts 61 & 91 Key Sections",
            "items": [{"label": i["label"], "value": i["value"]} for i in FAR_61_91_ITEMS],
        }
    )

    sections.append(
        {
            "section_id": "ntsb_830_inspections",
            "section_title": "NTSB 830 & Required Inspections",
            "items": [{"label": i["label"], "value": i["value"]} for i in NTSB_830_ITEMS],
        }
    )

    for sec in sections:
        if not sec.get("items"):
            sec["items"] = [{"label": "Content pending", "value": "Source data unavailable — verify against FAA publications"}]

    return sections


def _wrap_text_lines(c: canvas.Canvas, text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _general_row_height(c: canvas.Canvas, item: dict[str, Any], col_width: float, spacing: Spacing) -> float:
    pad = 8
    label_col_w = col_width * 0.32 - pad
    value_col_w = col_width * 0.64
    label = str(item.get("label", ""))
    value = str(item.get("value", ""))
    note = item.get("note")
    label_lines = _wrap_text_lines(c, label, "Helvetica-Bold", 7.5, label_col_w)
    value_lines = _wrap_text_lines(c, value, "Helvetica", 7.5, value_col_w)
    line_count = max(len(label_lines), len(value_lines), 1)
    h = 6 + line_count * 9
    if note:
        h += 10
    return max(spacing.row_height, h)


def _general_section_height(c: canvas.Canvas, section: dict[str, Any], col_width: float, spacing: Spacing) -> float:
    h = SECTION_HEADER_H + 0.5 + spacing.post_header_gap
    for item in section.get("items") or []:
        h += _general_row_height(c, item, col_width, spacing)
    return h


def layout_general_pages(
    sections: list[dict[str, Any]],
    sections_start_y: float,
    spacing: Spacing,
    c: canvas.Canvas,
) -> list[PageLayout]:
    col_w = CONTENT_WIDTH
    pages: list[PageLayout] = [PageLayout()]
    page_idx = 0
    y = sections_start_y

    def new_page() -> None:
        nonlocal page_idx, y
        page_idx += 1
        pages.append(PageLayout())
        y = sections_start_y

    for sec_idx, section in enumerate(sections):
        if sec_idx > 0:
            y -= spacing.section_gap + 2

        block_h = _general_section_height(c, section, col_w, spacing)
        if y - block_h < CONTENT_BOTTOM_Y:
            new_page()

        title = section.get("section_title", "")
        sid = section.get("section_id", "")
        pages[page_idx].col_a.append(
            PlacedItem(kind="section_header", y_top=y, section_id=sid, section_title=title)
        )
        y -= SECTION_HEADER_H + 0.5 + spacing.post_header_gap

        for row_idx, item in enumerate(section.get("items") or []):
            rh = _general_row_height(c, item, col_w, spacing)
            if y - rh < CONTENT_BOTTOM_Y:
                new_page()
                pages[page_idx].col_a.append(
                    PlacedItem(kind="section_header", y_top=y, section_id=sid, section_title=title)
                )
                y -= SECTION_HEADER_H + 0.5 + spacing.post_header_gap
            pages[page_idx].col_a.append(
                PlacedItem(kind="general_row", y_top=y, section_id=sid, item=item, row_index=row_idx)
            )
            y -= rh

    for pg in pages:
        pg.lowest_y = _page_lowest(pg, spacing)

    return pages


def draw_general_row(
    c: canvas.Canvas,
    x: float,
    width: float,
    y_top: float,
    item: dict[str, Any],
    row_index: int,
    spacing: Spacing,
) -> None:
    pad = 8
    label_col_w = width * 0.32 - pad
    value_col_w = width * 0.64
    value_x = x + width * 0.34
    label = str(item.get("label", ""))
    value = str(item.get("value", ""))
    note = item.get("note")

    label_lines = _wrap_text_lines(c, label, "Helvetica-Bold", 7.5, label_col_w)
    value_lines = _wrap_text_lines(c, value, "Helvetica", 7.5, value_col_w)
    line_count = max(len(label_lines), len(value_lines), 1)
    rh = max(spacing.row_height, 6 + line_count * 9 + (10 if note else 0))
    y_bottom = y_top - rh

    bg = GRAY_LIGHT if row_index % 2 == 0 else WHITE
    c.setFillColor(bg)
    c.rect(x, y_bottom, width, rh, stroke=0, fill=1)

    text_y = y_top - 8
    c.setFillColor(BLACK)
    for i, line in enumerate(label_lines):
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x + pad, text_y - i * 9, line)
    for i, line in enumerate(value_lines):
        c.setFont("Helvetica", 7.5)
        c.drawString(value_x, text_y - i * 9, line)

    if note:
        c.setFillColor(GRAY_NOTE)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + pad + 4, y_bottom + 2, str(note))


def draw_compact_header(
    c: canvas.Canvas,
    spec: dict[str, Any],
    logo_path: Path | None,
) -> float:
    """Logo + aircraft name + rule; return sections_start_y (no QR band)."""
    aircraft_name = spec.get("aircraft_name", "Aircraft")
    logo_bottom = LOGO_TOP_Y

    if logo_path and logo_path.is_file():
        try:
            with PILImage.open(logo_path) as img:
                iw, ih = img.size
            scale = min(LOGO_MAX_W / iw, LOGO_MAX_H / ih)
            draw_w = iw * scale
            draw_h = ih * scale
            logo_x = (PAGE_W - draw_w) / 2
            logo_y = LOGO_TOP_Y - draw_h
            c.drawImage(
                ImageReader(str(logo_path)),
                logo_x,
                logo_y,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            logo_bottom = logo_y
        except Exception:
            pass

    name_y = logo_bottom - 5 - 14
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 14)
    name_w = c.stringWidth(aircraft_name, "Helvetica-Bold", 14)
    c.drawString((PAGE_W - name_w) / 2, name_y, aircraft_name)

    subtitle = "General Knowledge — Study Sheets"
    sub_y = name_y - 3 - 7
    c.setFillColor(GRAY_SUBTITLE)
    c.setFont("Helvetica-Oblique", 7)
    sub_w = c.stringWidth(subtitle, "Helvetica-Oblique", 7)
    c.drawString((PAGE_W - sub_w) / 2, sub_y, subtitle)

    rule_y = sub_y - 6
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(MARGIN_LEFT, rule_y, MARGIN_LEFT + CONTENT_WIDTH, rule_y)

    return rule_y - 8


def render_general_page_content(
    c: canvas.Canvas,
    page: PageLayout,
    spacing: Spacing,
) -> None:
    for item in page.col_a:
        if item.kind == "section_header":
            draw_section_header(c, MARGIN_LEFT, CONTENT_WIDTH, item.y_top, item.section_title)
        elif item.kind == "general_row" and item.item:
            draw_general_row(c, MARGIN_LEFT, CONTENT_WIDTH, item.y_top, item.item, item.row_index, spacing)


def compact_sections_start_y(logo_path: Path | None) -> float:
    logo_h = logo_draw_height(logo_path)
    logo_bottom = LOGO_TOP_Y - logo_h
    name_y = logo_bottom - 5 - 14
    sub_y = name_y - 3 - 7
    rule_y = sub_y - 6
    return rule_y - 8


def render_general_sheets(
    c: canvas.Canvas,
    spec: dict[str, Any],
    faa_data_dir: Path,
    logo_path: Path | None,
    watermark_path: Path | None,
    spacing: Spacing,
    aircraft_page_count: int,
) -> tuple[list[PageLayout], Spacing]:
    """Layout general knowledge sections; caller renders pages after aircraft pages."""
    general_spacing = Spacing(
        section_gap=6.0,
        row_height=12.0,
        row_height_note=18.0,
        post_header_gap=2.0,
        emergency_step_h=spacing.emergency_step_h,
        emergency_proc_h=spacing.emergency_proc_h,
    )
    sections = build_general_sections(faa_data_dir)
    start_y = compact_sections_start_y(logo_path)
    pages = layout_general_pages(sections, start_y, general_spacing, c)
    return pages, general_spacing


def render_pdf(
    spec_path: Path,
    output_dir: Path,
    logo_path: Path | None,
    watermark_path: Path | None,
) -> Path:
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    aircraft_id = spec.get("aircraft_id", spec_path.stem.split("_")[0])
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{aircraft_id}_study_sheet.pdf"

    spacing = Spacing()
    spacing = try_fit_spacing(spec, logo_path, spacing)
    pages, fill_ratio, sections_start_y = layout_spec(spec, spacing, logo_path)

    if len(pages) == 1 and fill_ratio < 0.88:
        lowest = pages[0].lowest_y
        spacing = auto_adjust_spacing(spacing, fill_ratio, sections_start_y, lowest, spec)
        pages, fill_ratio, sections_start_y = layout_spec(spec, spacing, logo_path)

    pdf = canvas.Canvas(str(out_path), pagesize=(PAGE_W, PAGE_H))
    general_pages, general_spacing = render_general_sheets(
        pdf,
        spec,
        FAA_DATA_DIR,
        logo_path,
        watermark_path,
        spacing,
        len(pages),
    )
    aircraft_page_count = len(pages)
    total_pages = aircraft_page_count + len(general_pages)

    for page_num, page in enumerate(pages, start=1):
        if watermark_path and watermark_path.is_file():
            draw_watermark(pdf, str(watermark_path), PAGE_W, PAGE_H)

        content_start_y, _sections_start_y = draw_header(pdf, spec, logo_path)
        draw_quick_reference(pdf, spec, content_start_y)

        render_page_content(pdf, spec, page, spacing)
        draw_footer(pdf, spec, page_num, total_pages)

        if page_num < total_pages:
            pdf.showPage()

    for g_idx, g_page in enumerate(general_pages):
        page_num = aircraft_page_count + g_idx + 1
        if watermark_path and watermark_path.is_file():
            draw_watermark(pdf, str(watermark_path), PAGE_W, PAGE_H)

        sections_start_y = draw_compact_header(pdf, spec, logo_path)
        # Recompute y positions for this page relative to compact header
        y_offset = sections_start_y - compact_sections_start_y(logo_path)
        shifted = PageLayout(
            col_a=[
                PlacedItem(
                    kind=pi.kind,
                    y_top=pi.y_top + y_offset,
                    section_id=pi.section_id,
                    section_title=pi.section_title,
                    item=pi.item,
                    row_index=pi.row_index,
                    steps=pi.steps,
                )
                for pi in g_page.col_a
            ],
            col_b=[],
            lowest_y=g_page.lowest_y + y_offset,
        )
        render_general_page_content(pdf, shifted, general_spacing)
        draw_footer(pdf, spec, page_num, total_pages)

        if page_num < total_pages:
            pdf.showPage()

    pdf.save()
    rel = out_path.relative_to(REPO_ROOT)
    print(
        f"Rendered {rel} ({total_pages} page(s): {aircraft_page_count} aircraft + "
        f"{len(general_pages)} general, fill {fill_ratio:.0%})"
    )
    return out_path


def discover_specs(aircraft: str | None) -> list[Path]:
    if not SPECS_DIR.is_dir():
        print(f"Specs directory not found: {SPECS_DIR}", file=sys.stderr)
        sys.exit(1)

    patterns = ("*_study_sheet.json", "*_private_study_sheet.json")
    seen: dict[str, Path] = {}
    for pattern in patterns:
        for path in sorted(SPECS_DIR.glob(pattern)):
            aid = path.stem.split("_")[0]
            if aid not in seen:
                seen[aid] = path

    paths = sorted(seen.values(), key=lambda p: p.name)
    if aircraft:
        needle = aircraft.lower()
        paths = [p for p in paths if p.stem.startswith(f"{needle}_")]
        if not paths:
            print(f"No spec found for aircraft '{aircraft}' in {SPECS_DIR}", file=sys.stderr)
            sys.exit(1)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Render branded PDF study sheets (v2) from spec JSON.")
    ap.add_argument("--aircraft", default=None, help="Aircraft slug (e.g. r22). Default: all specs.")
    ap.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)})",
    )
    args = ap.parse_args()

    logo_path, watermark_path = resolve_assets()
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
