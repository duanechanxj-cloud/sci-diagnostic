from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from src.ai_analysis import prepare_anonymous_class_evidence
from src.reporting import FONT_REGULAR, FONT_BOLD, _safe_filename, short_topic_label


def _safe(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TeacherTitle", parent=styles["Title"], fontName=FONT_BOLD,
        fontSize=16, leading=18, alignment=TA_CENTER, spaceAfter=5,
    )
    h2 = ParagraphStyle(
        "TeacherH2", parent=styles["Heading2"], fontName=FONT_BOLD,
        fontSize=10.5, leading=12.5, spaceBefore=7, spaceAfter=3,
    )
    body = ParagraphStyle(
        "TeacherBody", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=9.5, leading=11.5, spaceAfter=2,
    )
    body_bold = ParagraphStyle("TeacherBodyBold", parent=body, fontName=FONT_BOLD)
    bullet = ParagraphStyle(
        "TeacherBullet", parent=body, leftIndent=10, firstLineIndent=-6, spaceAfter=2,
    )
    footer = ParagraphStyle(
        "TeacherFooter", parent=body, fontSize=8.5, leading=10,
        textColor=colors.HexColor("#555555"),
    )
    return title, h2, body, body_bold, bullet, footer


def _topic_table(evidence: dict, body, body_bold):
    rows = [[Paragraph("Topic", body_bold), Paragraph("Pupils", body_bold), Paragraph("Responses", body_bold), Paragraph("Correct", body_bold)]]
    for item in sorted(evidence.get("topic_evidence", []), key=lambda x: x.get("percent_correct", 0)):
        label = short_topic_label(item.get("Topic_Code", ""), item.get("Official Topic", ""))
        rows.append([
            Paragraph(escape(label), body),
            Paragraph(str(item.get("students", "")), body),
            Paragraph(str(item.get("responses", "")), body),
            Paragraph(f"{float(item.get('percent_correct', 0)):.0f}%", body),
        ])
    table = Table(rows, colWidths=[78*mm, 25*mm, 28*mm, 28*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F2F2F7")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D2D2D7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return table


def _gap_table(analysis, body, body_bold):
    rows = [[
        Paragraph("Priority", body_bold),
        Paragraph("Severity", body_bold),
        Paragraph("Learning gap", body_bold),
        Paragraph("Evidence / interpretation", body_bold),
    ]]
    for gap in analysis.learning_gaps[:6]:
        evidence = f"{gap.evidence} {gap.interpretation}".strip()
        rows.append([
            Paragraph(str(gap.rank), body),
            Paragraph(escape(gap.severity), body),
            Paragraph(escape(gap.concept), body),
            Paragraph(escape(evidence), body),
        ])
    table = Table(rows, colWidths=[17*mm, 25*mm, 51*mm, 75*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F2F2F7")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D2D2D7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return table


def generate_teacher_class_pdf(
    class_scored_rows: pd.DataFrame,
    output_path,
    *,
    analysis,
    report_title: str = "Primary Science Diagnostic — Teacher Report",
    checkpoint_label: str = "",
):
    if class_scored_rows.empty:
        raise ValueError("Class question evidence is required for a teacher report.")
    if analysis is None:
        raise ValueError("AI class analysis is required for the teacher report.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title, h2, body, body_bold, bullet, footer = _styles()

    class_name = _safe(class_scored_rows["Class_Name"].iloc[0]) if "Class_Name" in class_scored_rows.columns else "Class"
    level = _safe(class_scored_rows["Level"].iloc[0]) if "Level" in class_scored_rows.columns else ""
    evidence = prepare_anonymous_class_evidence(class_scored_rows)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=13*mm, leftMargin=13*mm, topMargin=12*mm, bottomMargin=12*mm,
        title=report_title,
    )

    story = [
        Paragraph(escape(report_title), title),
        Paragraph(
            f"<b>Class:</b> {escape(class_name)}"
            + (f" &nbsp;&nbsp; <b>Level:</b> {escape(level)}" if level else "")
            + f" &nbsp;&nbsp; <b>Pupils represented:</b> {int(evidence.get('class_size', 0))}",
            body,
        ),
    ]
    if checkpoint_label:
        story.append(Paragraph(f"<b>Checkpoint:</b> {escape(checkpoint_label)}", body))

    story.extend([
        Paragraph("Class performance snapshot", h2),
        _topic_table(evidence, body, body_bold),
        Paragraph("Class-level analysis", h2),
        Paragraph(escape(analysis.class_level_analysis), body),
    ])

    if analysis.learning_gaps:
        story.extend([
            Paragraph("Learning gaps ranked by revision priority", h2),
            _gap_table(analysis, body, body_bold),
        ])

    if analysis.recommended_actions:
        story.append(Paragraph("Recommended next course of action", h2))
        for action in analysis.recommended_actions[:6]:
            story.append(Paragraph("• " + escape(_safe(action)), bullet))

    story.extend([
        Spacer(1, 2*mm),
        Paragraph(
            "This teacher report interprets an anonymous low-stakes diagnostic snapshot. "
            "Use fresh questions or observations to check understanding again after intervention.",
            footer,
        ),
    ])

    doc.build(story)
    return output_path


def teacher_report_filename(class_name: str, checkpoint_label: str = "") -> str:
    base = _safe_filename(class_name)
    checkpoint = _safe_filename(checkpoint_label)
    suffix = f"_{checkpoint}" if checkpoint_label and checkpoint != "Pupil" else ""
    return f"{base}{suffix}_Teacher_Diagnostic_Report.pdf"
