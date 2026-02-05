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
# Use sample by default; can point to client_data.json when available
DATA_FILE = os.path.join("data", "client_data.sample.json")


# ----------------------------
# Sample assessment data (fallback)
# ----------------------------
# Scores: 0–5 where 5 = best
DEFAULT_ASSESSMENT: Dict[str, Dict[str, int]] = {
    # Defaults will be generated dynamically from canonical markdown definitions;
    # these are only used as a fallback if markdown parsing fails.
    "Operations": {
        "Documentation & Knowledge Base": 2,
        "Change Management": 2,
        "Incident & Problem Management": 2,
        "Monitoring & Alerting": 2,
        "Recovery Planning (RTO / RPO)": 2,
        "Disaster Recovery Procedures & Testing": 2,
        "Patch & Update Governance": 2,
        "Asset Lifecycle Management": 2,
        "Vendor & SaaS Governance": 2,
        "Control Auditing & Evidence Collection": 2,
        "Periodic Access & Configuration Reviews": 2,
        "Policy Compliance & Attestation": 2,
        "Third-Party & Security Review Readiness": 2,
    },
    "Users": {
        "User Account Lifecycle (Joiner / Mover / Leaver)": 2,
        "Authentication Controls (MFA, Conditional Access)": 2,
        "Privileged Access Management": 2,
        "Access Reviews & Least Privilege": 2,
        "Password Management (Password Manager Adoption)": 2,
        "Microsoft 365 / Google Workspace Backup": 2,
        "User Data Retention & Recovery": 2,
        "Security Awareness Training": 2,
        "Phishing & Social Engineering Defense": 2,
        "Acceptable Use & IT Policies (User Awareness)": 2,
        "User Support & Enablement": 2,
    },
    "Devices": {
        "Endpoint Protection (AV / EDR)": 2,
        "Disk Encryption": 2,
        "OS & Application Compliance": 2,
        "Endpoint Backups": 2,
        "Endpoint Restore Testing": 2,
        "Device Management Platform (MDM / RMM)": 2,
        "Patch Enforcement (Devices)": 2,
        "Local Admin Control": 2,
        "Asset Inventory Accuracy": 2,
        "BYOD & Personal Devices": 2,
        "Device Lifecycle & Replacement": 2,
    },
}

DEFAULT_FINDINGS: List[Tuple[str, str]] = [
    (
        "High Risk",
        "Access reviews and least privilege are not enforced on a defined schedule (Users: Access Reviews & Least Privilege).",
    ),
    (
        "High Risk",
        "Change Management is ad-hoc and not documented (Operations: Change Management).",
    ),
    (
        "Quick Win",
        "Improve Monitoring & Alerting coverage for endpoints and key services (Operations: Monitoring & Alerting).",
    ),
    (
        "Quick Win",
        "Implement MDM/RMM baselines for device compliance and policy enforcement (Devices: Device Management Platform).",
    ),
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
    ax.set_xticklabels(radar.labels, fontsize=7)

    ax.set_ylim(0, radar.max_value)
    # Keep grid rings but remove numeric labels; color background instead
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels([])

    # Discrete colored rings (1..5): 1=red, 3=yellow, 5=green
    from matplotlib.colors import ListedColormap, BoundaryNorm
    theta = np.linspace(0, 2 * np.pi, 360)
    r_bg = np.linspace(0, radar.max_value, 200)
    T, R = np.meshgrid(theta, r_bg)
    Z = R
    ring_edges = [0, 1, 2, 3, 4, 5]
    ring_colors = [
        "#CC0000",  # 0-1 (1)
        "#FF7F00",  # 1-2 (2)
        "#FFD400",  # 2-3 (3)
        "#7AC943",  # 3-4 (4)
        "#00A000",  # 4-5 (5)
    ]
    cmap = ListedColormap(ring_colors)
    norm = BoundaryNorm(ring_edges, cmap.N)
    ax.pcolormesh(T, R, Z, cmap=cmap, norm=norm, shading="auto", zorder=0)

    ax.plot(angles, values, linewidth=2, zorder=2)
    ax.fill(angles, values, alpha=0.15, zorder=1)

    ax.set_title(radar.title, fontsize=12, pad=16)

    fig.tight_layout()
    fig.savefig(out_path, transparent=False)
    plt.close(fig)


# ----------------------------
# Canonical categories parsing & assessment alignment
# ----------------------------

ALIASES: Dict[str, Dict[str, str]] = {
    "Operations": {
        "Backups & Recovery": "Disaster Recovery Procedures & Testing",
        "Patch Management": "Patch & Update Governance",
        "Monitoring & Alerting": "Monitoring & Alerting",
        "Change Management": "Change Management",
        "Documentation": "Documentation & Knowledge Base",
        "Vendor Management": "Vendor & SaaS Governance",
    },
    "Users": {
        "MFA Adoption": "Authentication Controls (MFA, Conditional Access)",
        "Access Reviews": "Access Reviews & Least Privilege",
        "Security Training": "Security Awareness Training",
        "Password Hygiene": "Password Management (Password Manager Adoption)",
        "On/Offboarding": "User Account Lifecycle (Joiner / Mover / Leaver)",
        "Privileged Access": "Privileged Access Management",
    },
    "Devices": {
        "Endpoint Protection": "Endpoint Protection (AV / EDR)",
        "Disk Encryption": "Disk Encryption",
        "OS Compliance": "OS & Application Compliance",
        "MDM / Policy": "Device Management Platform (MDM / RMM)",
        "Asset Inventory": "Asset Inventory Accuracy",
        "Local Admin Control": "Local Admin Control",
    },
}


def parse_canonical_categories(md_path: str) -> Dict[str, List[str]]:
    """Parse the canonical categories/subcategories from the markdown document."""
    categories: Dict[str, List[str]] = {}
    if not os.path.exists(md_path):
        return {k: list(v.keys()) for k, v in DEFAULT_ASSESSMENT.items()}

    current: str | None = None
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line.startswith("## ") and not line.startswith("###"):
                    h2 = line[3:].strip()
                    if h2 in ("Operations", "Users", "Devices"):
                        current = h2
                        categories[current] = []
                    else:
                        current = None
                elif line.startswith("- ") and current:
                    item = line[2:].strip()
                    # Remove trailing double spaces commonly used in markdown for line breaks
                    item = item.rstrip()
                    categories[current].append(item)
        # Deduplicate while preserving order
        for k, lst in categories.items():
            seen = set()
            categories[k] = [x for x in lst if not (x in seen or seen.add(x))]
    except Exception:
        # Fallback to defaults on any parse error
        return {k: list(v.keys()) for k, v in DEFAULT_ASSESSMENT.items()}
    return categories


def canonicalize_assessment(
    assessment_raw: Dict[str, Dict[str, int]],
    canonical: Dict[str, List[str]],
    default_score: int = 2,
) -> Dict[str, Dict[str, int]]:
    """Map raw assessment data to canonical subcategories, filling gaps with a default score."""
    result: Dict[str, Dict[str, int]] = {}

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    for category in ("Operations", "Users", "Devices"):
        subcats = canonical.get(category, [])
        raw_cat = assessment_raw.get(category, {})
        normalized_raw = {norm(k): v for k, v in raw_cat.items()}
        alias_map = ALIASES.get(category, {})

        mapped: Dict[str, int] = {}
        for sc in subcats:
            score = None
            # Exact match
            if sc in raw_cat:
                score = raw_cat[sc]
            else:
                # Alias mapping
                for old, new in alias_map.items():
                    if new == sc and old in raw_cat:
                        score = raw_cat[old]
                        break
                if score is None:
                    # Normalized match
                    ns = norm(sc)
                    if ns in normalized_raw:
                        score = normalized_raw[ns]
            mapped[sc] = int(score if score is not None else default_score)
        result[category] = mapped
    return result


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
    client_name, assessment_raw, findings = load_client_data(DATA_FILE)

    # Parse canonical categories/subcategories from markdown
    md_path = os.path.join(os.path.dirname(__file__), "aegis-categories-v1.md")
    canonical = parse_canonical_categories(md_path)

    # Align assessment to canonical subcategories; fill gaps with default score
    assessment = canonicalize_assessment(assessment_raw, canonical, default_score=2)

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