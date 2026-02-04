#!/usr/bin/env python3
"""
Audit Report MVP
- Hardcoded assessment data
- 3 radar charts (Operations / Users / Devices)
- PDF output with ReportLab
"""

from __future__ import annotations

import os
from dataclasses import dataclass
import json
import re
from datetime import date
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ----------------------------
# Hardcoded “style guide” knobs
# ----------------------------
BRAND = {
    "company_name": "Backslash Designs",
    "report_title": "IT Systems Audit Snapshot",
    "primary_color": colors.HexColor("#0F172A"),   # slate-ish
    "accent_color": colors.HexColor("#2563EB"),    # blue-ish
    "muted_color": colors.HexColor("#64748B"),
}

PAGE = {
    "size": LETTER,
    "margin": 0.75 * inch,
    "header_h": 0.55 * inch,
    "footer_h": 0.45 * inch,
}

OUTPUT_PDF = "audit-report-mvp.pdf"
CHART_DIR = "charts"
OUTPUT_ROOT = "output"
DATA_FILE = os.path.join("data", "client_data.json")


# ----------------------------
# Sample assessment data (fallback)
# ----------------------------
# Scores: 0–5 where 5 = best
DEFAULT_ASSESSMENT: Dict[str, Dict[str, int]] = {
    "Operations": {
        "Backups & Recovery": 2,
        "Patch Management": 3,
        "Monitoring & Alerting": 2,
        "Change Management": 1,
        "Documentation": 3,
        "Vendor Management": 2,
    },
    "Users": {
        "MFA Adoption": 3,
        "Access Reviews": 1,
        "Security Training": 2,
        "Password Hygiene": 3,
        "On/Offboarding": 2,
        "Privileged Access": 1,
    },
    "Devices": {
        "Endpoint Protection": 3,
        "Disk Encryption": 2,
        "OS Compliance": 2,
        "MDM / Policy": 1,
        "Asset Inventory": 2,
        "Local Admin Control": 1,
    },
}

DEFAULT_FINDINGS: List[Tuple[str, str]] = [
    ("High Risk", "Access Reviews are not performed on a defined schedule (Users: Access Reviews = 1)."),
    ("High Risk", "Change Management is ad-hoc and not documented (Operations: Change Management = 1)."),
    ("Quick Win", "Improve Monitoring & Alerting coverage for endpoints and key services (Operations: 2)."),
    ("Quick Win", "Implement MDM baselines for device compliance and policy enforcement (Devices: 1)."),
]

def load_client_data(path: str) -> Tuple[str, Dict[str, Dict[str, int]], List[Tuple[str, str]]]:
    """Load client name, assessment, and findings from JSON if available; otherwise use defaults."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        client_name = data.get("client_name", "Client (Sample)")
        assessment = data.get("assessment", DEFAULT_ASSESSMENT)
        findings_raw = data.get("findings", [])
        findings: List[Tuple[str, str]] = [tuple(item) for item in findings_raw] if findings_raw else DEFAULT_FINDINGS
        return client_name, assessment, findings
    # Fallback
    return "Northwind Family Ministries (Sample)", DEFAULT_ASSESSMENT, DEFAULT_FINDINGS


# ----------------------------
# Helpers
# ----------------------------
@dataclass(frozen=True)
class RadarData:
    title: str
    labels: List[str]
    values: List[float]
    max_value: float = 5.0


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def mean_score(scores: Dict[str, int]) -> float:
    vals = list(scores.values())
    return round(sum(vals) / max(len(vals), 1), 2)


def maturity_label(score_0_to_5: float) -> str:
    # Simple mapping (tweak later)
    if score_0_to_5 >= 4.25:
        return "Optimized"
    if score_0_to_5 >= 3.25:
        return "Managed"
    if score_0_to_5 >= 2.25:
        return "Developing"
    if score_0_to_5 >= 1.25:
        return "Basic"
    return "At Risk"


def build_radar(category: str, subcats: Dict[str, int]) -> RadarData:
    labels = list(subcats.keys())
    values = [float(v) for v in subcats.values()]
    return RadarData(title=category, labels=labels, values=values, max_value=5.0)


def save_radar_chart_png(radar: RadarData, out_path: str) -> None:
    # Radar plot via polar axes
    N = len(radar.labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()

    # Close the loop
    values = radar.values + radar.values[:1]
    angles = angles + angles[:1]

    fig = plt.figure(figsize=(6, 6), dpi=150)
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar.labels, fontsize=8)

    ax.set_ylim(0, radar.max_value)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=8)

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.15)

    ax.set_title(radar.title, fontsize=12, pad=16)

    fig.tight_layout()
    fig.savefig(out_path, transparent=False)
    plt.close(fig)


# ----------------------------
# PDF layout
# ----------------------------
def draw_header(c: canvas.Canvas, page_w: float, page_h: float, client_name: str) -> None:
    margin = PAGE["margin"]
    header_h = PAGE["header_h"]

    # Header band
    c.setFillColor(BRAND["primary_color"])
    c.rect(0, page_h - header_h, page_w, header_h, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, page_h - header_h + 0.20 * inch, BRAND["company_name"])

    c.setFont("Helvetica", 10)
    c.drawRightString(page_w - margin, page_h - header_h + 0.22 * inch, f"Client: {client_name}")


def draw_footer(c: canvas.Canvas, page_w: float, page_h: float, page_num: int) -> None:
    margin = PAGE["margin"]
    footer_h = PAGE["footer_h"]

    c.setStrokeColor(colors.lightgrey)
    c.line(margin, footer_h, page_w - margin, footer_h)

    c.setFillColor(BRAND["muted_color"])
    c.setFont("Helvetica", 9)
    c.drawString(margin, 0.22 * inch, f"{BRAND['report_title']} • {date.today().isoformat()}")
    c.drawRightString(page_w - margin, 0.22 * inch, f"Page {page_num}")


def draw_title_block(c: canvas.Canvas, page_w: float, page_h: float, y_top: float, client_name: str) -> float:
    margin = PAGE["margin"]

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, y_top, BRAND["report_title"])

    c.setFont("Helvetica", 12)
    c.setFillColor(BRAND["muted_color"])
    c.drawString(margin, y_top - 0.28 * inch, f"{client_name} • Assessment Date: {date.today().isoformat()}")

    return y_top - 0.6 * inch


def draw_exec_summary(c: canvas.Canvas, page_w: float, y_top: float, overall: float, per_cat: Dict[str, float]) -> float:
    margin = PAGE["margin"]

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y_top, "Executive Summary")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)

    text = c.beginText(margin, y_top - 0.22 * inch)
    text.setLeading(14)
    text.textLine(f"Overall maturity score: {overall:.2f} / 5.00 ({maturity_label(overall)})")
    text.textLine("Category scores:")
    for k, v in per_cat.items():
        text.textLine(f"  • {k}: {v:.2f} / 5.00 ({maturity_label(v)})")
    c.drawText(text)

    return y_top - 1.15 * inch


def draw_findings_table(
    c: canvas.Canvas,
    page_w: float,
    y_top: float,
    findings: List[Tuple[str, str]],
) -> float:
    margin = PAGE["margin"]
    row_h = 0.28 * inch
    table_w = page_w - 2 * margin

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, y_top, "Key Findings")

    y = y_top - 0.2 * inch

    # Header row
    c.setFillColor(BRAND["accent_color"])
    c.rect(margin, y - row_h, table_w, row_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 0.12 * inch, y - 0.2 * inch, "Type")
    c.drawString(margin + 1.3 * inch, y - 0.2 * inch, "Finding")

    y -= row_h

    c.setFont("Helvetica", 9)
    for i, (ftype, ftext) in enumerate(findings):
        # alternating fill
        if i % 2 == 0:
            c.setFillColor(colors.whitesmoke)
            c.rect(margin, y - row_h, table_w, row_h, stroke=0, fill=1)

        c.setFillColor(colors.black)
        c.drawString(margin + 0.12 * inch, y - 0.2 * inch, ftype)

        # simple wrap (basic MVP)
        max_chars = 95
        line = ftext if len(ftext) <= max_chars else (ftext[: max_chars - 3] + "...")
        c.drawString(margin + 1.3 * inch, y - 0.2 * inch, line)

        y -= row_h

        # Page break guard (minimal)
        if y < (PAGE["footer_h"] + PAGE["margin"] + 1.2 * inch):
            return y

    return y - 0.2 * inch


def draw_charts_page(c: canvas.Canvas, page_w: float, page_h: float, chart_paths: Dict[str, str]) -> None:
    margin = PAGE["margin"]

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(margin, page_h - PAGE["header_h"] - margin, "Radar Charts")

    # Layout: 3 charts stacked
    usable_h = page_h - PAGE["header_h"] - PAGE["footer_h"] - 2 * margin
    chart_h = usable_h / 3.0
    chart_w = page_w - 2 * margin

    y_top = page_h - PAGE["header_h"] - margin - 0.3 * inch

    for idx, cat in enumerate(["Operations", "Users", "Devices"]):
        path = chart_paths[cat]
        img = ImageReader(path)

        y = y_top - (idx + 1) * chart_h + 0.15 * inch
        c.drawImage(img, margin, y, width=chart_w, height=chart_h - 0.25 * inch, preserveAspectRatio=True, anchor="c")


def generate_pdf(client_name: str, chart_paths: Dict[str, str], assessment: Dict[str, Dict[str, int]], findings: List[Tuple[str, str]], output_pdf_path: str) -> str:
    page_w, page_h = PAGE["size"]
    c = canvas.Canvas(output_pdf_path, pagesize=PAGE["size"])

    # Page 1: Summary + Findings
    page_num = 1
    draw_header(c, page_w, page_h, client_name)

    y = page_h - PAGE["header_h"] - PAGE["margin"]
    y = draw_title_block(c, page_w, page_h, y, client_name)

    per_cat_scores = {k: mean_score(v) for k, v in assessment.items()}
    overall = round(sum(per_cat_scores.values()) / 3.0, 2)

    y = draw_exec_summary(c, page_w, y, overall, per_cat_scores)
    y = draw_findings_table(c, page_w, y, findings)

    draw_footer(c, page_w, page_h, page_num)
    c.showPage()

    # Page 2: Charts
    page_num = 2
    draw_header(c, page_w, page_h, client_name)
    draw_charts_page(c, page_w, page_h, chart_paths)
    draw_footer(c, page_w, page_h, page_num)
    c.showPage()

    c.save()
    return output_pdf_path


def main() -> None:
    client_name, assessment, findings = load_client_data(DATA_FILE)

    # Client-specific output directory
    client_slug = slugify(client_name)
    client_dir = os.path.join(OUTPUT_ROOT, client_slug)
    ensure_dir(client_dir)

    # Generate radar charts to client folder
    chart_paths: Dict[str, str] = {}
    for category, subcats in assessment.items():
        radar = build_radar(category, subcats)
        out_png = os.path.join(client_dir, f"radar_{category.lower()}.png")
        save_radar_chart_png(radar, out_png)
        chart_paths[category] = out_png

    # Generate PDF to client folder
    pdf_path = os.path.join(client_dir, OUTPUT_PDF)
    pdf_path = generate_pdf(client_name, chart_paths, assessment, findings, pdf_path)
    print(f"Generated: {pdf_path}")
    print(f"Outputs saved in: {client_dir}/")


if __name__ == "__main__":
    main()