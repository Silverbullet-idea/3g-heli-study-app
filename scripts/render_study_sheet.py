#!/usr/bin/env python3
"""
PDF study sheet renderer — limitations (Phase 1).
Uses reportlab canvas for precise layout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --- Page dimensions ---
PAGE_W, PAGE_H = letter  # 612 x 792 points

MARGIN_LEFT = 40
MARGIN_RIGHT = 40
MARGIN_TOP = 36
MARGIN_BOTTOM = 50
CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT

# Brand colors (RGB 0-1)
BLUE = (0.294, 0.369, 0.749)  # #4B5EBF
ORANGE = (0.910, 0.396, 0.039)  # #E8650A
DARK = (0.102, 0.102, 0.102)  # #1A1A1A
MID_GRAY = (0.4, 0.4, 0.4)
LIGHT_GRAY = (0.94, 0.94, 0.94)
RED_WARN = (0.8, 0.133, 0.0)
BLUE_REQ = (0.133, 0.267, 0.667)
WHITE = (1, 1, 1)
ROW_BORDER = (0.9, 0.9, 0.9)
CELL_BORDER = (0.88, 0.88, 0.88)
ZEBRA_ALT = (0.98, 0.98, 0.98)
FIRST_COL_BG = (0.96, 0.96, 0.96)
CAUTION_BROWN = (0.573, 0.451, 0.051)  # #92400E

REPO_ROOT = Path(__file__).resolve().parent.parent


def register_fonts() -> list[str]:
    font_dir = r"C:\Windows\Fonts"
    registered: list[str] = []
    pairs = [
        ("Arial", "arial.ttf"),
        ("Arial-Bold", "arialbd.ttf"),
        ("Arial-Black", "ariblk.ttf"),
        ("Arial-Italic", "ariali.ttf"),
        ("Courier-New", "cour.ttf"),
    ]
    for name, filename in pairs:
        path = os.path.join(font_dir, filename)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
            registered.append(name)
    return registered


REGISTERED = register_fonts()
FONT_BODY = "Arial" if "Arial" in REGISTERED else "Helvetica"
FONT_BOLD = "Arial-Bold" if "Arial-Bold" in REGISTERED else "Helvetica-Bold"
FONT_BLACK = "Arial-Black" if "Arial-Black" in REGISTERED else "Helvetica-Bold"
FONT_ITALIC = "Arial-Italic" if "Arial-Italic" in REGISTERED else "Helvetica-Oblique"
FONT_MONO = "Courier-New" if "Courier-New" in REGISTERED else "Courier"

AIRCRAFT_META = {
    "r22": {
        "full_name": "Robinson R22",
        "engine_type": "piston",
        "engine_model": "Lycoming O-320",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
    "r44": {
        "full_name": "Robinson R44",
        "engine_type": "piston",
        "engine_model": "Lycoming O-360",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
    "r66": {
        "full_name": "Robinson R66",
        "engine_type": "turbine",
        "engine_model": "Rolls-Royce 250-C300/A1",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
    "b505": {
        "full_name": "Bell 505",
        "engine_type": "turbine",
        "engine_model": "Arrius 2R (FADEC)",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
    "b206": {
        "full_name": "Bell 206B3",
        "engine_type": "turbine",
        "engine_model": "Allison 250-C20B/C20J",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
    "b407": {
        "full_name": "Bell 407",
        "engine_type": "turbine",
        "engine_model": "Rolls-Royce 250-C47B",
        "logo_path": "assets/logo_horizontal.png",
        "watermark_path": "assets/heli_icon.png",
    },
}

RATING_LABELS = {
    "private": "Private Pilot",
    "commercial": "Commercial Pilot",
    "instrument": "Instrument",
    "cfi": "Certified Flight Instructor",
}


def resolve_repo_path(rel: str) -> Path:
    return (REPO_ROOT / rel).resolve()


def fmt_field(entry: dict[str, Any] | None, empty: str = "—") -> str:
    if not entry:
        return empty
    val = entry.get("value")
    unit = entry.get("unit") or ""
    if val is None:
        notes = (entry.get("notes") or "").strip()
        return notes if notes else "See POH / placards"
    return f"{val} {unit}".strip()


def wrap_lines(
    text: str, font: str, size: float, max_w: float, c: canvas.Canvas
) -> list[str]:
    if not text.strip():
        return [""]
    words = text.replace("\n", " ").split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        test = " ".join(cur + [w])
        if c.stringWidth(test, font, size) <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_page_header(
    c: canvas.Canvas,
    aircraft_full: str,
    rating_label: str,
    page_num: int,
    total_pages: int,
    logo_path: Path | None,
) -> float:
    cursor_y = PAGE_H - MARGIN_TOP
    if logo_path and logo_path.is_file():
        c.drawImage(
            ImageReader(str(logo_path)),
            MARGIN_LEFT,
            cursor_y - 28,
            width=110,
            height=28,
            mask="auto",
        )
        cursor_y -= 36
    else:
        cursor_y -= 4

    cx = PAGE_W / 2
    y = cursor_y
    s1 = "3G "
    s2 = "Heli"
    s3 = " Prep"
    w1 = c.stringWidth(s1, FONT_BLACK, 14)
    w2 = c.stringWidth(s2, FONT_BLACK, 14)
    w3 = c.stringWidth(s3, FONT_BLACK, 14)
    x = cx - (w1 + w2 + w3) / 2
    c.setFillColorRGB(*BLUE)
    c.setFont(FONT_BLACK, 14)
    c.drawString(x, y - 14, s1)
    c.setFillColorRGB(*ORANGE)
    c.drawString(x + w1, y - 14, s2)
    c.setFillColorRGB(*BLUE)
    c.drawString(x + w1 + w2, y - 14, s3)
    y -= 22

    c.setFillColorRGB(*DARK)
    c.setFont(FONT_BLACK, 13)
    title = f"{aircraft_full} \u2014 Limitations"
    c.drawCentredString(cx, y - 13, title)
    y -= 18

    c.setFillColorRGB(*MID_GRAY)
    c.setFont(FONT_BODY, 7.5)
    sub = (
        f"{rating_label} Study Sheet · Page {page_num} of {total_pages} · "
        "Verify all values against current POH"
    )
    c.drawCentredString(cx, y - 8, sub)
    y -= 12

    c.setStrokeColorRGB(*BLUE)
    c.setLineWidth(1.5)
    c.line(MARGIN_LEFT, y, PAGE_W - MARGIN_RIGHT, y)
    y -= 8
    return y


def draw_section_header(
    c: canvas.Canvas,
    cursor_y: float,
    title: str,
    subtitle: str = "",
    color: tuple[float, float, float] = BLUE,
) -> float:
    bar_h = 14
    y0 = cursor_y - bar_h
    c.setFillColorRGB(*color)
    c.rect(MARGIN_LEFT, y0, CONTENT_W, bar_h, stroke=0, fill=1)
    c.setFillColorRGB(*WHITE)
    c.setFont(FONT_BLACK, 8.5)
    c.drawString(MARGIN_LEFT + 6, y0 + 3.5, title)
    if subtitle:
        c.saveState()
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(0.85)
        c.setFont(FONT_BODY, 7)
        sw = c.stringWidth(subtitle, FONT_BODY, 7)
        c.drawString(PAGE_W - MARGIN_RIGHT - 6 - sw, y0 + 4, subtitle)
        c.restoreState()
    return y0 - 4


def draw_data_row(
    c: canvas.Canvas,
    cursor_y: float,
    label: str,
    value: str,
    value_color: tuple[float, float, float] = DARK,
    zebra: bool = False,
) -> float:
    row_h = 13
    y0 = cursor_y - row_h
    if zebra:
        c.setFillColorRGB(*LIGHT_GRAY)
        c.rect(MARGIN_LEFT, y0, CONTENT_W, row_h, stroke=0, fill=1)
    c.setStrokeColorRGB(*ROW_BORDER)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, y0, PAGE_W - MARGIN_RIGHT, y0)
    c.setFont(FONT_BOLD, 8)
    c.setFillColorRGB(*DARK)
    c.drawString(MARGIN_LEFT + 2, y0 + 3, label)
    c.setFont(FONT_MONO, 8)
    c.setFillColorRGB(*value_color)
    vw = c.stringWidth(value, FONT_MONO, 8)
    c.drawString(PAGE_W - MARGIN_RIGHT - vw - 2, y0 + 3, value)
    c.setFillColorRGB(*DARK)
    return y0


def draw_table(
    c: canvas.Canvas,
    cursor_y: float,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    x0: float | None = None,
) -> float:
    pad_v = 3
    pad_h = 4
    x0 = MARGIN_LEFT if x0 is None else x0
    cw = col_widths
    ncols = len(headers)

    def cell_lines(text: str, col_idx: int, header: bool) -> tuple[list[str], str]:
        font = FONT_BOLD if header else FONT_MONO
        size = 7.5
        w = cw[col_idx] - 2 * pad_h
        if col_idx == 0 and not header:
            font = FONT_BOLD
        lines = wrap_lines(text, font, size, w, c)
        return lines, font

    header_line_blocks: list[list[str]] = []
    header_fonts: list[str] = []
    max_hh = 0
    for i, h in enumerate(headers):
        lines, font = cell_lines(h.upper(), i, True)
        header_line_blocks.append(lines)
        header_fonts.append(font)
        max_hh = max(max_hh, len(lines) * (7.5 + 2))

    header_h = max_hh + 2 * pad_v
    data_heights: list[float] = []
    data_line_info: list[list[tuple[list[str], str, bool]]] = []
    for row in rows:
        line_infos: list[tuple[list[str], str, bool]] = []
        row_max = 0
        for i, cell in enumerate(row):
            is_first = i == 0
            font = FONT_BOLD if is_first else FONT_MONO
            w = cw[i] - 2 * pad_h
            lines = wrap_lines(cell, font, 7.5, w, c)
            line_infos.append((lines, font, is_first))
            row_max = max(row_max, len(lines) * (7.5 + 2))
        data_line_info.append(line_infos)
        data_heights.append(row_max + 2 * pad_v)

    total_h = header_h + sum(data_heights)
    top = cursor_y
    y = top

    c.setStrokeColorRGB(*CELL_BORDER)
    c.setLineWidth(0.5)
    c.setFillColorRGB(*LIGHT_GRAY)
    c.rect(x0, y - header_h, sum(cw), header_h, stroke=1, fill=1)
    xh = x0
    for i, _h in enumerate(headers):
        c.setFont(FONT_BOLD, 7.5)
        c.setFillColorRGB(*DARK)
        yy = y - pad_v - 7.5
        for line in header_line_blocks[i]:
            c.drawString(xh + pad_h, yy, line)
            yy -= 9
        xh += cw[i]

    y -= header_h
    for ri, row in enumerate(rows):
        rh = data_heights[ri]
        x = x0
        bg = WHITE if ri % 2 == 0 else ZEBRA_ALT
        for ci in range(ncols):
            cell_bg = FIRST_COL_BG if ci == 0 else bg
            c.setFillColorRGB(*cell_bg)
            c.rect(x, y - rh, cw[ci], rh, stroke=1, fill=1)
            lines, font, _ = data_line_info[ri][ci]
            c.setFont(font, 7.5)
            c.setFillColorRGB(*DARK)
            yy = y - pad_v - 7.5
            for line in lines:
                c.drawString(x + pad_h, yy, line)
                yy -= 9
            x += cw[ci]
        y -= rh

    return y - 5


def draw_note_box(
    c: canvas.Canvas,
    cursor_y: float,
    text: str,
    style: str = "note",
) -> float:
    pad = 5
    w = CONTENT_W
    x0 = MARGIN_LEFT
    if style == "note":
        border_rgb = ORANGE
        bg = (1.0, 0.973, 0.902)  # #FFF8E6
        lw = 3
        full = False
    elif style == "caution":
        border_rgb = RED_WARN
        bg = (1.0, 0.949, 0.941)  # #FFF2F0
        lw = 3
        full = False
    elif style == "mnemonic":
        border_rgb = BLUE
        bg = (0.969, 0.973, 1.0)  # #F7F8FF
        lw = 1.5
        full = True
    elif style == "mnemonic_orange":
        border_rgb = ORANGE
        bg = (1.0, 0.976, 0.961)  # #FFF9F5
        lw = 1.5
        full = True
    else:
        border_rgb = ORANGE
        bg = (1.0, 0.973, 0.902)
        lw = 3
        full = False

    inner_w = w - 2 * pad - (lw if not full else 0)
    lines = wrap_lines(text, FONT_BODY, 7.5, inner_w, c)
    text_h = len(lines) * 9 + 2 * pad
    box_h = text_h

    y_top = cursor_y
    y0 = y_top - box_h
    c.setFillColorRGB(*bg)
    if full:
        c.setStrokeColorRGB(*border_rgb)
        c.setLineWidth(lw)
        c.rect(x0, y0, w, box_h, stroke=1, fill=1)
    else:
        c.rect(x0, y0, w, box_h, stroke=0, fill=1)
        c.setStrokeColorRGB(*border_rgb)
        c.setLineWidth(lw)
        c.line(x0, y0, x0, y_top)

    c.setFont(FONT_BODY, 7.5)
    c.setFillColorRGB(*DARK)
    yy = y_top - pad - 7.5
    for line in lines:
        c.drawString(x0 + pad + (lw if not full else lw), yy, line)
        yy -= 9

    return y0 - 6


def draw_watermark(c: canvas.Canvas, watermark_path: Path | None) -> None:
    candidates = []
    if watermark_path and watermark_path.is_file():
        candidates.append(watermark_path)
    assets = REPO_ROOT / "assets"
    for name in ("HeliOnlyLarge.png", "BlackLogoHeliOnly.png", "heli_icon.png"):
        p = assets / name
        if p.is_file() and p not in candidates:
            candidates.append(p)
    if not candidates:
        return
    path = candidates[0]
    iw = PAGE_W * 0.35
    c.saveState()
    c.setFillAlpha(0.08)
    c.drawImage(
        ImageReader(str(path)),
        (PAGE_W - iw) / 2,
        (PAGE_H - iw) / 2,
        width=iw,
        height=iw,
        mask="auto",
    )
    c.restoreState()


def draw_page_footer(c: canvas.Canvas, page_num: int) -> None:
    y = MARGIN_BOTTOM
    c.setStrokeColorRGB(*ROW_BORDER)
    c.setLineWidth(0.5)
    c.line(MARGIN_LEFT, y + 14, PAGE_W - MARGIN_RIGHT, y + 14)
    c.setFont(FONT_ITALIC, 7)
    c.setFillColorRGB(*MID_GRAY)
    left = "By the author of the ASA Helicopter Oral Exam Guide — Ryan Dale"
    c.drawString(MARGIN_LEFT, y, left)
    right = f"3gheliprep.com · Page {page_num}"
    rw = c.stringWidth(right, FONT_BODY, 7)
    c.setFont(FONT_BODY, 7)
    c.drawString(PAGE_W - MARGIN_RIGHT - rw, y, right)


def draw_two_column(
    c: canvas.Canvas,
    cursor_y: float,
    left_fn: Callable[..., float],
    right_fn: Callable[..., float],
    gap: float = 12,
) -> float:
    half = (CONTENT_W - gap) / 2
    left_x = MARGIN_LEFT
    right_x = MARGIN_LEFT + half + gap
    yl = left_fn(c, cursor_y, left_x, half)
    yr = right_fn(c, cursor_y, right_x, half)
    return min(yl, yr)


def draw_mnemonic_rotor_bands(
    c: canvas.Canvas,
    cursor_y: float,
    power_on_min: str,
    power_on_max: str,
    power_off_min: str,
    power_off_max: str,
    title: str,
    hook: str,
) -> float:
    pad = 5
    lw = 1.5
    inner_gap = 8
    box_inner_w = CONTENT_W - 2 * pad - 2 * lw
    half_inner = (box_inner_w - inner_gap) / 2
    title_h = 12
    boxes_h = 42
    hook_lines = wrap_lines(hook, FONT_BODY, 7.5, box_inner_w, c)
    hook_h = len(hook_lines) * 9 + 8
    total_h = title_h + boxes_h + hook_h + 2 * pad

    y_top = cursor_y
    y0 = y_top - total_h
    x0 = MARGIN_LEFT
    c.setStrokeColorRGB(*BLUE)
    c.setLineWidth(lw)
    c.setFillColorRGB(0.969, 0.973, 1.0)
    c.rect(x0, y0, CONTENT_W, total_h, stroke=1, fill=1)

    c.setFont(FONT_BLACK, 7.5)
    c.setFillColorRGB(*BLUE)
    c.drawString(x0 + pad + lw, y_top - pad - 7.5, title)

    bx = x0 + pad + lw
    by = y_top - pad - title_h - boxes_h + 8
    c.setStrokeColorRGB(*BLUE)
    c.setLineWidth(1)
    c.setFillColorRGB(0.95, 0.97, 1.0)
    c.rect(bx, by, half_inner, 34, stroke=1, fill=1)
    c.setFont(FONT_BOLD, 7)
    c.setFillColorRGB(*BLUE)
    c.drawString(bx + 4, by + 22, "Power ON")
    c.setFont(FONT_BLACK, 11)
    c.drawString(bx + 4, by + 6, f"{power_on_min}–{power_on_max}%")

    bx2 = bx + half_inner + inner_gap
    c.setStrokeColorRGB(*ORANGE)
    c.setFillColorRGB(1.0, 0.98, 0.96)
    c.rect(bx2, by, half_inner, 34, stroke=1, fill=1)
    c.setFont(FONT_BOLD, 7)
    c.setFillColorRGB(*ORANGE)
    c.drawString(bx2 + 4, by + 22, "Power OFF (Autorotation)")
    c.setFont(FONT_BLACK, 11)
    c.drawString(bx2 + 4, by + 6, f"{power_off_min}–{power_off_max}%")

    hy = by - 8
    c.setFont(FONT_BODY, 7.5)
    c.setFillColorRGB(*DARK)
    for line in hook_lines:
        c.drawString(x0 + pad + lw, hy - 7.5, line)
        hy -= 9

    return y0 - 6


def temp_to_x(temp_c: float, bar_left: float, bar_w: float) -> float:
    tmin, tmax = -20.0, 40.0
    return bar_left + (temp_c - tmin) / (tmax - tmin) * bar_w


def draw_mnemonic_carb_ice(
    c: canvas.Canvas,
    cursor_y: float,
    caution_low_c: float,
    caution_high_c: float,
    title: str,
    hook: str,
) -> float:
    pad = 5
    lw = 1.5
    inner_w = CONTENT_W - 2 * pad - 2 * lw
    bar_h = 14
    label_h = 16
    zone_h = 14
    hook_lines = wrap_lines(hook, FONT_BODY, 7.5, inner_w, c)
    hook_h = len(hook_lines) * 9 + 8
    title_h = 12
    total_h = title_h + label_h + bar_h + zone_h + hook_h + 2 * pad

    y_top = cursor_y
    y0 = y_top - total_h
    x0 = MARGIN_LEFT
    c.setStrokeColorRGB(*ORANGE)
    c.setLineWidth(lw)
    c.setFillColorRGB(1.0, 0.976, 0.961)
    c.rect(x0, y0, CONTENT_W, total_h, stroke=1, fill=1)

    ix = x0 + pad + lw
    iy_top = y_top - pad
    c.setFont(FONT_BLACK, 7.5)
    c.setFillColorRGB(*ORANGE)
    c.drawString(ix, iy_top - 7.5, title)

    bar_y = iy_top - title_h - label_h
    bl = ix
    bw = inner_w
    tmin, tmax = -20.0, 40.0

    x_lo = temp_to_x(caution_low_c, bl, bw)
    x_hi = temp_to_x(caution_high_c, bl, bw)

    c.setFillColorRGB(0.86, 0.92, 0.99)  # cold safe
    c.rect(bl, bar_y - bar_h, max(0, x_lo - bl), bar_h, stroke=0, fill=1)
    c.setFillColorRGB(0.99, 0.95, 0.78)  # caution
    c.rect(x_lo, bar_y - bar_h, max(0, x_hi - x_lo), bar_h, stroke=0, fill=1)
    c.setFillColorRGB(0.96, 0.96, 0.96)  # hot safe
    c.rect(x_hi, bar_y - bar_h, max(0, bl + bw - x_hi), bar_h, stroke=0, fill=1)

    c.saveState()
    c.setDash(3, 2)
    c.setStrokeColorRGB(0.851, 0.467, 0.024)  # #D97706
    c.setLineWidth(1.5)
    c.line(x_lo, bar_y - bar_h, x_lo, bar_y)
    c.line(x_hi, bar_y - bar_h, x_hi, bar_y)
    c.restoreState()

    tick_labels: list[tuple[float, str, bool]] = [
        (-20.0, "−20°C", False),
        (0.0, "0°C", False),
        (caution_low_c, f"{caution_low_c:g}°C", True),
        (caution_high_c, f"{caution_high_c:g}°C", True),
        (40.0, "40°C", False),
    ]
    seen_x: set[int] = set()
    for t, lab, is_bound in tick_labels:
        tx = int(temp_to_x(t, bl, bw))
        if tx in seen_x:
            continue
        seen_x.add(tx)
        c.setFont(FONT_BOLD if is_bound else FONT_MONO, 7)
        c.setFillColorRGB(*(CAUTION_BROWN if is_bound else DARK))
        tw = c.stringWidth(lab, FONT_BOLD if is_bound else FONT_MONO, 7)
        c.drawString(temp_to_x(t, bl, bw) - tw / 2, bar_y + 2, lab)
    c.setFont(FONT_MONO, 7)
    c.setFillColorRGB(*DARK)

    zx = bl
    zw = x_lo - bl
    c.setFont(FONT_BOLD, 7)
    c.setFillColorRGB(*MID_GRAY)
    c.drawCentredString(zx + zw / 2, bar_y - bar_h - 10, "SAFE")
    zw2 = x_hi - x_lo
    c.drawCentredString(x_lo + zw2 / 2, bar_y - bar_h - 10, "⚠ CAUTION")
    zw3 = bl + bw - x_hi
    c.drawCentredString(x_hi + zw3 / 2, bar_y - bar_h - 10, "SAFE (less likely)")

    hy = bar_y - bar_h - zone_h - 4
    c.setFont(FONT_BODY, 7.5)
    c.setFillColorRGB(*DARK)
    for line in hook_lines:
        c.drawString(ix, hy - 7.5, line)
        hy -= 9

    return y0 - 6


def draw_mnemonic_alitics(
    c: canvas.Canvas,
    cursor_y: float,
    letters: list[dict[str, str]],
    title: str,
) -> float:
    pad = 5
    lw = 1.5
    inner_w = CONTENT_W - 2 * pad - 2 * lw
    gap = 10
    col_w = (inner_w - gap) / 2
    n = len(letters)
    left_n = (n + 1) // 2
    left = letters[:left_n]
    right = letters[left_n:]

    def col_height(items: list[dict[str, str]], w: float) -> float:
        h = 0
        for it in items:
            dlines = wrap_lines(it["detail"], FONT_BODY, 8, w - 26, c)
            h += max(22, 8 + len(dlines) * 9) + 4
        return h

    h_left = col_height(left, col_w)
    h_right = col_height(right, col_w)
    body_h = max(h_left, h_right)
    title_h = 14
    total_h = title_h + body_h + 2 * pad

    y_top = cursor_y
    y0 = y_top - total_h
    x0 = MARGIN_LEFT
    c.setStrokeColorRGB(*ORANGE)
    c.setLineWidth(lw)
    c.setFillColorRGB(1.0, 0.976, 0.961)
    c.rect(x0, y0, CONTENT_W, total_h, stroke=1, fill=1)

    ix = x0 + pad + lw
    c.setFont(FONT_BLACK, 7.5)
    c.setFillColorRGB(*ORANGE)
    c.drawString(ix, y_top - pad - 7.5, title)

    def draw_col(items: list[dict[str, str]], cx: float, w: float, start_y: float) -> float:
        y = start_y
        for it in items:
            tile = 18
            c.setFillColorRGB(*BLUE)
            c.rect(cx, y - tile, tile, tile, stroke=0, fill=1)
            c.setFont(FONT_BLACK, 11)
            c.setFillColorRGB(*WHITE)
            c.drawCentredString(cx + tile / 2, y - tile + 4, it["letter"])
            c.setFont(FONT_BOLD, 8)
            c.setFillColorRGB(*DARK)
            c.drawString(cx + tile + 4, y - 8, it["word"])
            dlines = wrap_lines(it["detail"], FONT_BODY, 8, w - tile - 8, c)
            yy = y - 18
            c.setFont(FONT_BODY, 8)
            c.setFillColorRGB(*MID_GRAY)
            for dl in dlines:
                c.drawString(cx + tile + 4, yy, dl)
                yy -= 9
            block = max(tile, 8 + len(dlines) * 9) + 6
            y -= block
        return y

    start_y = y_top - pad - title_h - 4
    draw_col(left, ix, col_w, start_y)
    draw_col(right, ix + col_w + gap, col_w, start_y)
    return y0 - 6


def draw_quick_recall_grid(
    c: canvas.Canvas,
    cursor_y: float,
    cells: list[tuple[str, str]],
    title: str = "QUICK RECALL",
) -> float:
    pad = 5
    lw = 1.5
    inner_w = CONTENT_W - 2 * pad - 2 * lw
    cols = 4
    rows = 2
    gap_x = 6
    gap_y = 6
    cw = (inner_w - gap_x * (cols - 1)) / cols
    rh = 36
    title_h = 14
    total_h = title_h + rows * rh + (rows - 1) * gap_y + 2 * pad

    y_top = cursor_y
    y0 = y_top - total_h
    x0 = MARGIN_LEFT
    c.setStrokeColorRGB(*ORANGE)
    c.setLineWidth(lw)
    c.setFillColorRGB(1.0, 0.976, 0.961)
    c.rect(x0, y0, CONTENT_W, total_h, stroke=1, fill=1)

    ix = x0 + pad + lw
    c.setFont(FONT_BLACK, 7.5)
    c.setFillColorRGB(*ORANGE)
    c.drawString(ix, y_top - pad - 7.5, title)

    idx = 0
    for row in range(rows):
        for col in range(cols):
            if idx >= len(cells):
                break
            val, desc = cells[idx]
            cx = ix + col * (cw + gap_x)
            cy = y_top - pad - title_h - row * (rh + gap_y) - rh
            c.setFillColorRGB(*LIGHT_GRAY)
            c.rect(cx, cy, cw, rh, stroke=0, fill=1)
            c.setFont(FONT_BLACK, 12)
            c.setFillColorRGB(*ORANGE)
            c.drawString(cx + 4, cy + rh - 16, val)
            c.setFont(FONT_BODY, 7)
            c.setFillColorRGB(*DARK)
            dlines = wrap_lines(desc, FONT_BODY, 7, cw - 8, c)
            yy = cy + rh - 22
            for dl in dlines[:2]:
                c.drawString(cx + 4, yy, dl)
                yy -= 8
            idx += 1

    return y0 - 6


def collect_airspeed_notes(airspeed: dict[str, Any]) -> str:
    notes: list[str] = []
    for _k, v in airspeed.items():
        if isinstance(v, dict):
            n = (v.get("notes") or "").strip()
            if n and n not in notes:
                notes.append(n)
    return " ".join(notes) if notes else "Verify VNE and green arc against airspeed indicator and placards."


def build_airspeed_rows(data: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    al = data.get("airspeed_limits") or {}
    headers = ["Parameter", "Value"]
    rows: list[list[str]] = []
    order = [
        ("vne_powered_to_3000ft", "VNE (≤ 3000 ft DA)"),
        ("vne_above_3000ft", "VNE (> 3000 ft DA)"),
        ("airspeed_indicator_green_arc_min", "Green arc (lower limit)"),
        ("airspeed_indicator_red_line", "Red line"),
    ]
    for key, label in order:
        if key in al:
            rows.append([label, fmt_field(al[key])])
    for key, entry in al.items():
        if "door" in key.lower() or "doors" in key.lower():
            rows.append([key.replace("_", " ").title(), fmt_field(entry)])
    return headers, rows


def build_page_1(
    c: canvas.Canvas,
    data: dict[str, Any],
    mnemonics: dict[str, Any],
    aircraft_meta: dict[str, Any],
    page_num: int,
    total_pages: int,
    rating_label: str,
) -> None:
    wm = resolve_repo_path(aircraft_meta.get("watermark_path", ""))
    draw_watermark(c, wm if wm.is_file() else None)

    logo = resolve_repo_path(aircraft_meta["logo_path"])
    cy = draw_page_header(
        c,
        aircraft_meta["full_name"],
        rating_label,
        page_num,
        total_pages,
        logo if logo.is_file() else None,
    )

    cy = draw_section_header(
        c, cy, "AIRSPEED LIMITS", "FAR 27.1505 / POH Sec. 2", BLUE
    )
    note = collect_airspeed_notes(data.get("airspeed_limits") or {})
    cy = draw_note_box(c, cy, note, style="note")

    h, rows = build_airspeed_rows(data)
    cw = [CONTENT_W * 0.52, CONTENT_W * 0.48]
    cy = draw_table(c, cy, h, rows, cw)

    rs = data.get("rotor_speed_limits") or {}
    pon = rs.get("power_on_min") or {}
    pom = rs.get("power_on_max") or {}
    pofn = rs.get("power_off_min") or {}
    pofm = rs.get("power_off_max") or {}

    cy = draw_section_header(
        c, cy, "ROTOR SPEED LIMITS (NR)", "POH Sec. 2", ORANGE
    )

    def left_rotor(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        headers = ["", "Min", "Norm", "Max"]
        rrows = [
            [
                "Power ON",
                fmt_field(pon).replace(" %", "%"),
                "—",
                fmt_field(pom).replace(" %", "%"),
            ],
        ]
        cw2 = [w * 0.28, w * 0.24, w * 0.24, w * 0.24]
        return draw_table(cc, y, headers, rrows, cw2, x0=x)

    def right_rotor(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        headers = ["", "Min", "Norm", "Max"]
        rrows = [
            [
                "Power OFF",
                fmt_field(pofn).replace(" %", "%"),
                "—",
                fmt_field(pofm).replace(" %", "%"),
            ],
        ]
        cw2 = [w * 0.28, w * 0.24, w * 0.24, w * 0.24]
        return draw_table(cc, y, headers, rrows, cw2, x0=x)

    cy = draw_two_column(c, cy, left_rotor, right_rotor, gap=12)

    rband = mnemonics.get("rotor_speed_bands") or {}
    rs_hook = rband.get("hook", "")
    rs_title = rband.get("title", "MEMORY AID — ROTOR SPEED RANGES")
    cy = draw_mnemonic_rotor_bands(
        c,
        cy,
        str(pon.get("value", "")),
        str(pom.get("value", "")),
        str(pofn.get("value", "")),
        str(pofm.get("value", "")),
        rs_title,
        rs_hook,
    )

    low_g = (
        "LOW-G PROHIBITION: Intentional low-G maneuvers (cyclic pushovers) are prohibited — "
        "catastrophic loss of control can result. See POH for full discussion."
    )
    cy = draw_note_box(c, cy, low_g, style="caution")

    cy = draw_section_header(c, cy, "ALTITUDE LIMITS", "", BLUE)
    alt = data.get("altitude_limits") or {}
    for _k, entry in alt.items():
        if isinstance(entry, dict):
            lab = _k.replace("_", " ").title()
            cy = draw_data_row(c, cy, lab, fmt_field(entry))

    draw_page_footer(c, page_num)


def build_weight_rows(data: dict[str, Any]) -> tuple[list[list[str]], list[list[str]]]:
    wl = data.get("weight_limits") or {}
    left: list[list[str]] = []
    right: list[list[str]] = []
    for key in (
        "max_gross_standard_hp",
        "max_gross_alpha_beta_beta_ii",
        "min_gross",
        "min_solo_pilot_weight",
    ):
        if key in wl:
            left.append(
                [key.replace("_", " ").title(), fmt_field(wl[key])]
            )
    if "max_per_baggage_compartment" in wl:
        right.append(
            ["Max baggage compartment", fmt_field(wl["max_per_baggage_compartment"])]
        )
    if "max_per_seat_including_baggage" in wl:
        right.append(["Per seat (incl. baggage)", fmt_field(wl["max_per_seat_including_baggage"])])
    return left, right


def build_engine_left_rows(engine: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    if "cht_max" in engine:
        rows.append(["CHT max", fmt_field(engine["cht_max"])])
    if "oil_temp_max" in engine:
        rows.append(["Oil temp max", fmt_field(engine["oil_temp_max"])])
    if "oil_pressure_min_idle" in engine:
        rows.append(["Oil PSI min (idle)", fmt_field(engine["oil_pressure_min_idle"])])
    if "oil_pressure_min_flight" in engine:
        rows.append(["Oil PSI min (flight)", fmt_field(engine["oil_pressure_min_flight"])])
    if "oil_pressure_max_flight" in engine:
        rows.append(["Oil PSI max (flight)", fmt_field(engine["oil_pressure_max_flight"])])
    if "speed_max_continuous" in engine:
        rows.append(["RPM / % max cont.", fmt_field(engine["speed_max_continuous"])])
    if "speed_max_transient" in engine:
        rows.append(["RPM / % max transient", fmt_field(engine["speed_max_transient"])])
    if "mgt_max" in engine:
        rows.append(["MGT limits (see notes)", fmt_field(engine["mgt_max"])])
    return rows


def build_engine_right_rows(engine: dict[str, Any], piston: bool) -> list[list[str]]:
    rows: list[list[str]] = []
    models = engine.get("approved_models") or []
    if models:
        rows.append(["Approved engine(s)", ", ".join(models)])
    if "oil_quantity_min_takeoff" in engine:
        rows.append(["Min oil quantity", fmt_field(engine["oil_quantity_min_takeoff"])])
    if piston:
        lo = engine.get("carb_air_temp_caution_range_min")
        hi = engine.get("carb_air_temp_caution_range_max")
        if isinstance(lo, dict) and isinstance(hi, dict):
            cl = lo.get("value")
            ch = hi.get("value")
            u = lo.get("unit") or "°C"
            if cl is not None and ch is not None:
                rows.append(["Carb air caution (yellow arc)", f"{cl} to {ch} {u}"])
    return rows


def build_page_2(
    c: canvas.Canvas,
    data: dict[str, Any],
    mnemonics: dict[str, Any],
    aircraft_meta: dict[str, Any],
    page_num: int,
    total_pages: int,
    rating_label: str,
) -> None:
    wm = resolve_repo_path(aircraft_meta.get("watermark_path", ""))
    draw_watermark(c, wm if wm.is_file() else None)
    logo = resolve_repo_path(aircraft_meta["logo_path"])
    cy = draw_page_header(
        c,
        aircraft_meta["full_name"],
        rating_label,
        page_num,
        total_pages,
        logo if logo.is_file() else None,
    )

    cy = draw_section_header(c, cy, "WEIGHT LIMITS", "", BLUE)

    wl, wr = build_weight_rows(data)

    def left_w(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        headers = ["Limit", "Value"]
        cw2 = [w * 0.55, w * 0.45]
        return draw_table(cc, y, headers, wl, cw2, x0=x)

    def right_w(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        if not wr:
            return y
        headers = ["Limit", "Value"]
        cw2 = [w * 0.55, w * 0.45]
        return draw_table(cc, y, headers, wr, cw2, x0=x)

    cy = draw_two_column(c, cy, left_w, right_w, gap=12)

    eng = data.get("engine") or {}
    eng_title = f"ENGINE LIMITS — {aircraft_meta['engine_model']}"
    eng_sub = "Piston" if aircraft_meta["engine_type"] == "piston" else "Turbine"
    cy = draw_section_header(c, cy, eng_title, eng_sub, ORANGE)

    piston = aircraft_meta["engine_type"] == "piston"
    el = build_engine_left_rows(eng)
    er = build_engine_right_rows(eng, piston)

    def left_e(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        headers = ["Parameter", "Value"]
        cw2 = [w * 0.45, w * 0.55]
        return draw_table(cc, y, headers, el, cw2, x0=x)

    def right_e(
        cc: canvas.Canvas, y: float, x: float, w: float
    ) -> float:
        headers = ["Parameter", "Value"]
        cw2 = [w * 0.42, w * 0.58]
        return draw_table(cc, y, headers, er, cw2, x0=x)

    cy = draw_two_column(c, cy, left_e, right_e, gap=12)

    carb = mnemonics.get("carb_ice") or {}
    if piston:
        clo = eng.get("carb_air_temp_caution_range_min") or {}
        chi = eng.get("carb_air_temp_caution_range_max") or {}
        cl = float(clo["value"]) if clo.get("value") is not None else 11.0
        ch = float(chi["value"]) if chi.get("value") is not None else 21.0
        cy = draw_mnemonic_carb_ice(
            c,
            cy,
            cl,
            ch,
            carb.get("title", "MEMORY AID — CARB ICE CAUTION ZONE"),
            carb.get("hook", ""),
        )
    else:
        mgt_note = (
            "Turbine operating limits: observe MGT/TOT and torque limits as published in the POH. "
            "Intentional operation outside continuous limits is prohibited."
        )
        if eng.get("mgt_max"):
            em = eng["mgt_max"]
            extra = (em.get("notes") or "").strip()
            head = fmt_field(em)
            mgt_note = f"{head}. {extra}" if extra else f"{head}. {mgt_note}"
        cy = draw_note_box(c, cy, mgt_note, style="note")

    cy = draw_section_header(c, cy, "FUEL", "", BLUE)
    fuel = data.get("fuel") or {}
    grades = fuel.get("approved_grades") or []
    if grades:
        cy = draw_data_row(
            c,
            cy,
            "Approved fuel grades",
            "; ".join(grades[:6]) + ("…" if len(grades) > 6 else ""),
        )
    cap = fuel.get("capacity_bladder_tanks") or {}
    if cap.get("combined_total"):
        cy = draw_data_row(
            c, cy, "Total capacity", fmt_field(cap["combined_total"])
        )
    if cap.get("combined_usable"):
        cy = draw_data_row(
            c, cy, "Usable capacity", fmt_field(cap["combined_usable"])
        )

    fuel_hook = (
        "Three blues, no reds — verify approved grades against placards and AFM."
        if piston
        else "Jet-A / approved turbine fuels per POH — verify cold-temperature and additive limits."
    )
    cy = draw_note_box(c, cy, fuel_hook, style="note")

    al = data.get("airspeed_limits") or {}
    rs = data.get("rotor_speed_limits") or {}
    wl2 = data.get("weight_limits") or {}
    alt = data.get("altitude_limits") or {}
    pon_v = rs.get("power_on_min") or {}
    pom_v = rs.get("power_on_max") or {}
    pofn_v = rs.get("power_off_min") or {}
    pofm_v = rs.get("power_off_max") or {}
    cells: list[tuple[str, str]] = [
        (
            fmt_field(al.get("vne_powered_to_3000ft")),
            "VNE (≤3000 ft DA)",
        ),
        (
            f"{pon_v.get('value', '—')}–{pom_v.get('value', '—')}%",
            "NR Power ON range",
        ),
        (
            f"{pofn_v.get('value', '—')}–{pofm_v.get('value', '—')}%",
            "NR Power OFF range",
        ),
        (
            fmt_field(wl2.get("max_gross_standard_hp") or wl2.get("max_gross_alpha_beta_beta_ii")),
            "Max gross (see POH variants)",
        ),
    ]
    for _k, entry in alt.items():
        if isinstance(entry, dict):
            cells.append((fmt_field(entry), "Max operating DA"))
            break
    if eng.get("oil_quantity_min_takeoff"):
        cells.append((fmt_field(eng["oil_quantity_min_takeoff"]), "Min oil qty"))
    if piston and eng.get("carb_air_temp_caution_range_min"):
        cells.append(
            (
                f"{fmt_field(eng['carb_air_temp_caution_range_min'])}–{fmt_field(eng['carb_air_temp_caution_range_max'])}",
                "Carb ice caution",
            )
        )
    else:
        cells.append((fmt_field(wl2.get("min_gross")), "Min gross"))
    while len(cells) < 8:
        cells.append(("—", "Reserve"))
    cells = cells[:8]

    cy = draw_quick_recall_grid(c, cy, cells)
    draw_page_footer(c, page_num)


def draw_restriction_line(
    c: canvas.Canvas,
    cursor_y: float,
    status: str,
    item: str,
    notes: str,
) -> float:
    pill_w = 72
    row_h = 14
    if notes:
        extra = wrap_lines(notes, FONT_BODY, 7, CONTENT_W - pill_w - 16, c)
        row_h = max(row_h, 10 + len(extra) * 8)

    y0 = cursor_y - row_h
    if status == "PROHIBITED":
        c.setFillColorRGB(*RED_WARN)
    elif status == "REQUIRED":
        c.setFillColorRGB(*BLUE_REQ)
    else:
        c.setFillColorRGB(*MID_GRAY)
    c.roundRect(MARGIN_LEFT, y0 + 2, pill_w, 12, 3, stroke=0, fill=1)
    c.setFont(FONT_BOLD, 6.5)
    c.setFillColorRGB(*WHITE)
    c.drawString(MARGIN_LEFT + 4, y0 + 5, status[:11])

    c.setFont(FONT_BOLD, 8)
    c.setFillColorRGB(*DARK)
    c.drawString(MARGIN_LEFT + pill_w + 6, y0 + row_h - 10, item)
    if notes:
        c.setFont(FONT_BODY, 7)
        c.setFillColorRGB(*MID_GRAY)
        yy = y0 + row_h - 20
        for line in wrap_lines(notes, FONT_BODY, 7, CONTENT_W - pill_w - 16, c):
            c.drawString(MARGIN_LEFT + pill_w + 6, yy, line)
            yy -= 8
    return y0 - 4


def build_page_3(
    c: canvas.Canvas,
    data: dict[str, Any],
    mnemonics: dict[str, Any],
    aircraft_meta: dict[str, Any],
    page_num: int,
    total_pages: int,
    rating_label: str,
) -> None:
    wm = resolve_repo_path(aircraft_meta.get("watermark_path", ""))
    draw_watermark(c, wm if wm.is_file() else None)
    logo = resolve_repo_path(aircraft_meta["logo_path"])
    cy = draw_page_header(
        c,
        aircraft_meta["full_name"],
        rating_label,
        page_num,
        total_pages,
        logo if logo.is_file() else None,
    )

    cy = draw_section_header(
        c,
        cy,
        "FLIGHT RESTRICTIONS & PROHIBITIONS",
        "POH Sec. 2",
        ORANGE,
    )

    po = mnemonics.get("prohibited_ops") or {}
    cy = draw_mnemonic_alitics(
        c,
        cy,
        po.get("letters") or [],
        po.get("title", "MEMORY AID — ALITICS"),
    )

    for fr in data.get("flight_restrictions") or []:
        cy = draw_restriction_line(
            c,
            cy,
            fr.get("status", ""),
            fr.get("item", ""),
            (fr.get("notes") or "").strip(),
        )

    fad = data.get("faa_ad_95_26_04")
    if isinstance(fad, dict) and fad.get("limitations"):
        cy = draw_note_box(
            c,
            cy,
            (fad.get("note") or "SFAR 73 / awareness limitations may apply.").strip(),
            style="note",
        )
        for fr in fad["limitations"]:
            cy = draw_restriction_line(
                c,
                cy,
                fr.get("status", ""),
                fr.get("item", ""),
                (fr.get("notes") or "").strip(),
            )

    cy = draw_section_header(c, cy, "AIRWORTHINESS REMINDERS", "", BLUE)
    rows = [
        ("Annual inspection", "Every 12 calendar months (14 CFR 91.409)"),
        ("100-hour", "Required if carrying persons for hire or flight instruction for hire"),
        ("Engine / component limits", "Observe TBO and overhaul limits in POH and maintenance records"),
    ]
    for lab, val in rows:
        cy = draw_data_row(c, cy, lab, val)

    tom = (
        "For the full “A TOMATO FLAMES” VFR-day / IFR equipment lists, see your FAR/AIM study sheet "
        "and POH required equipment."
    )
    cy = draw_note_box(c, cy, tom, style="note")

    draw_page_footer(c, page_num)


def render_pdf(
    aircraft: str,
    rating: str,
    section: str,
    output_dir: Path | None,
) -> Path:
    if section != "limitations":
        print(f"Section '{section}' not implemented; only 'limitations' is supported.", file=sys.stderr)
        sys.exit(1)

    if aircraft not in AIRCRAFT_META:
        print(f"Unknown aircraft: {aircraft}", file=sys.stderr)
        sys.exit(1)

    meta = AIRCRAFT_META[aircraft]
    rating_label = RATING_LABELS.get(rating, rating.title())

    data_path = REPO_ROOT / "extracted-data" / "aircraft" / f"{aircraft}_limitations.json"
    if not data_path.is_file():
        print(f"Missing data file: {data_path}", file=sys.stderr)
        sys.exit(1)

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    mn_path = REPO_ROOT / "scripts" / "mnemonics.json"
    with open(mn_path, encoding="utf-8") as f:
        mnemonics = json.load(f)

    out_dir = output_dir or (REPO_ROOT / "study-cards" / rating)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / f"{aircraft}_{rating}_limitations.pdf"

    c = canvas.Canvas(str(out_pdf), pagesize=letter)

    print(f"Rendering: {meta['full_name']} \u2014 Limitations ({rating_label})")
    print(f"Engine type: {meta['engine_type']}")
    print(f"Loading: {data_path.relative_to(REPO_ROOT)}")

    primary = ["Arial", "Arial-Bold", "Arial-Black", "Courier-New"]
    reg_str = ", ".join(n for n in primary if n in REGISTERED)
    print(f"Fonts registered: {reg_str}")

    wm = resolve_repo_path(meta["watermark_path"])
    print(f"Watermark: {meta['watermark_path']}")

    build_page_1(c, data, mnemonics, meta, 1, 3, rating_label)
    c.showPage()
    build_page_2(c, data, mnemonics, meta, 2, 3, rating_label)
    c.showPage()
    build_page_3(c, data, mnemonics, meta, 3, 3, rating_label)
    c.save()

    print("Pages: 3")
    print(f"Output: {out_pdf.relative_to(REPO_ROOT)}")
    print("Done.")
    return out_pdf


def main() -> None:
    ap = argparse.ArgumentParser(description="Render branded limitations study sheet PDF.")
    ap.add_argument("--aircraft", required=True, help="Aircraft slug: r22, r44, r66, b505, b206, b407")
    ap.add_argument("--rating", required=True, help="Rating: private, commercial, instrument, cfi")
    ap.add_argument("--section", default="limitations", help="Section (default: limitations)")
    ap.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: study-cards/{rating}/)",
    )
    args = ap.parse_args()
    od = Path(args.output_dir) if args.output_dir else None
    render_pdf(args.aircraft.lower(), args.rating.lower(), args.section.lower(), od)


if __name__ == "__main__":
    main()
