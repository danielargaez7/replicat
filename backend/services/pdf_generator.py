"""
Playbook PDF Generator

Generates a printable remediation playbook from a RemediationPlan.
Designed for air-gapped environments — the PDF is fully self-contained.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.remediation import RemediationItem, RemediationPlan

# ─── Color scheme ───

_CRITICAL = colors.HexColor("#DC2626")
_WARNING = colors.HexColor("#D97706")
_INFO = colors.HexColor("#2563EB")
_DARK = colors.HexColor("#1E1E2E")
_GRAY = colors.HexColor("#6B7280")
_LIGHT_BG = colors.HexColor("#F3F4F6")
_WHITE = colors.white

_SEVERITY_COLORS = {
    "critical": _CRITICAL,
    "warning": _WARNING,
    "info": _INFO,
    "pass": _GRAY,
}

_RISK_LABELS = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}


def generate_playbook_pdf(plan: RemediationPlan) -> bytes:
    """Generate a complete remediation playbook PDF. Returns raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = _build_styles()
    story: list = []

    _add_cover_page(story, styles, plan)
    _add_executive_summary(story, styles, plan)
    _add_checklist(story, styles, plan)
    _add_detail_pages(story, styles, plan)
    _add_footer_note(story, styles, plan)

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ─── Styles ───


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PlaybookTitle",
            parent=base["Title"],
            fontSize=28,
            textColor=_DARK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "PlaybookSubtitle",
            parent=base["Normal"],
            fontSize=12,
            textColor=_GRAY,
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "h1": ParagraphStyle(
            "PlaybookH1",
            parent=base["Heading1"],
            fontSize=18,
            textColor=_DARK,
            spaceBefore=20,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "PlaybookH2",
            parent=base["Heading2"],
            fontSize=14,
            textColor=_DARK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "PlaybookBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=_DARK,
            spaceAfter=6,
            leading=14,
        ),
        "command": ParagraphStyle(
            "PlaybookCommand",
            parent=base["Code"],
            fontSize=9,
            textColor=_DARK,
            backColor=_LIGHT_BG,
            borderPadding=6,
            spaceAfter=4,
            leading=12,
            fontName="Courier",
        ),
        "small": ParagraphStyle(
            "PlaybookSmall",
            parent=base["Normal"],
            fontSize=8,
            textColor=_GRAY,
            spaceAfter=4,
        ),
        "evidence": ParagraphStyle(
            "PlaybookEvidence",
            parent=base["Normal"],
            fontSize=9,
            textColor=_GRAY,
            backColor=_LIGHT_BG,
            borderPadding=6,
            spaceAfter=6,
            leading=12,
        ),
    }


# ─── Cover page ───


def _add_cover_page(story: list, styles: dict, plan: RemediationPlan) -> None:
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("BUNDLESCOPE", styles["title"]))
    story.append(Paragraph("Remediation Playbook", styles["subtitle"]))
    story.append(Spacer(1, 0.5 * inch))

    meta_data = [
        ["Analysis ID:", plan.analysis_id[:12] + "..."],
        ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M UTC")],
        ["Health Score:", f"{plan.health_score}/100"],
        ["Total Remediations:", str(plan.total_items)],
        ["Critical Items:", str(plan.critical_count)],
    ]
    if plan.cluster_version:
        meta_data.insert(2, ["Cluster Version:", plan.cluster_version])

    meta_table = Table(meta_data, colWidths=[2 * inch, 4 * inch])
    meta_table.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), _GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), _DARK),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 1 * inch))
    story.append(Paragraph(
        "This document contains evidence-grounded remediation steps for issues "
        "found in a Kubernetes support bundle analysis. Each item includes the "
        "exact commands to run and rollback procedures if needed.",
        styles["body"],
    ))
    story.append(Paragraph(
        "IMPORTANT: Review each remediation before executing. Items marked as "
        "CRITICAL require explicit approval before proceeding.",
        styles["body"],
    ))


# ─── Executive summary ───


def _add_executive_summary(story: list, styles: dict, plan: RemediationPlan) -> None:
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Executive Summary", styles["h1"]))

    if plan.summary:
        story.append(Paragraph(plan.summary, styles["body"]))

    if plan.root_cause:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("Root Cause", styles["h2"]))
        story.append(Paragraph(plan.root_cause, styles["body"]))


# ─── Checklist table ───


def _add_checklist(story: list, styles: dict, plan: RemediationPlan) -> None:
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Remediation Checklist", styles["h1"]))

    if not plan.items:
        story.append(Paragraph("No actionable remediations found.", styles["body"]))
        return

    header = ["#", "Title", "Severity", "Risk", "Approved"]
    rows = [header]

    for item in plan.items:
        auto = " (auto)" if item.auto_resolves else ""
        rows.append([
            str(item.order),
            _truncate(item.title, 50) + auto,
            item.severity.value.upper(),
            _RISK_LABELS.get(item.risk_level.value, "?"),
            "[ ]",
        ])

    table = Table(rows, colWidths=[0.4 * inch, 3.5 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch])
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), _DARK),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, _GRAY),
        # Alternating rows
        *[
            ("BACKGROUND", (0, i), (-1, i), _LIGHT_BG)
            for i in range(2, len(rows), 2)
        ],
    ]))
    story.append(table)


# ─── Detailed remediation pages ───


def _add_detail_pages(story: list, styles: dict, plan: RemediationPlan) -> None:
    for item in plan.items:
        story.append(Spacer(1, 0.3 * inch))
        _add_item_detail(story, styles, item)


def _add_item_detail(story: list, styles: dict, item: RemediationItem) -> None:
    severity_color = _SEVERITY_COLORS.get(item.severity.value, _GRAY)

    # Title with order number
    title_text = (
        f'<font color="{severity_color.hexval()}">[{item.severity.value.upper()}]</font> '
        f"Fix {item.order}: {_escape(item.title)}"
    )
    story.append(Paragraph(title_text, styles["h2"]))

    # Meta line
    meta_parts = []
    if item.namespace:
        meta_parts.append(f"Namespace: {item.namespace}")
    if item.resource_kind and item.resource_name:
        meta_parts.append(f"{item.resource_kind}: {item.resource_name}")
    meta_parts.append(f"Risk: {_RISK_LABELS.get(item.risk_level.value, '?')}")
    if item.estimated_downtime:
        meta_parts.append(f"Downtime: {item.estimated_downtime}")
    story.append(Paragraph(" | ".join(meta_parts), styles["small"]))

    # Auto-resolve notice
    if item.auto_resolves:
        story.append(Paragraph(
            "This issue may resolve automatically after upstream fixes are applied.",
            styles["evidence"],
        ))

    # Description
    if item.description:
        story.append(Paragraph(_escape(item.description), styles["body"]))

    # Evidence
    if item.evidence_summary:
        story.append(Paragraph("Evidence:", styles["small"]))
        story.append(Paragraph(_escape(item.evidence_summary), styles["evidence"]))

    # Commands
    if item.commands:
        story.append(Paragraph("Commands:", styles["small"]))
        for cmd in item.commands:
            if cmd.description:
                story.append(Paragraph(f"# {_escape(cmd.description)}", styles["small"]))
            story.append(Paragraph(_escape(cmd.command), styles["command"]))

    # Rollback
    if item.rollback_commands:
        story.append(Paragraph("Rollback:", styles["small"]))
        for cmd in item.rollback_commands:
            if cmd.description:
                story.append(Paragraph(f"# {_escape(cmd.description)}", styles["small"]))
            story.append(Paragraph(_escape(cmd.command), styles["command"]))

    # Approval line
    if item.requires_approval:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(
            "Approved by: ______________________  Date: ______________",
            styles["body"],
        ))


# ─── Footer ───


def _add_footer_note(story: list, styles: dict, plan: RemediationPlan) -> None:
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        f"Generated by Bundlescope on {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}. "
        f"Analysis ID: {plan.analysis_id}. "
        f"This document is intended for authorized personnel only.",
        styles["small"],
    ))


# ─── Utilities ───


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def _escape(text: str) -> str:
    """Escape XML special characters for ReportLab paragraphs."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
