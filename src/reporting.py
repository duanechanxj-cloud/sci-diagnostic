from __future__ import annotations

from pathlib import Path
from io import BytesIO
from xml.sax.saxutils import escape
import re

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable,
)


REPORT_BODY_FONT_SIZE = 10
MAX_REPORT_PAGES = 2


def _safe(value):
    if pd.isna(value):
        return ""
    return str(value)


def _register_font_family() -> tuple[str, str, str]:
    """Use Arial when available, then fall back to Helvetica.

    The app never bundles or exports font files. Arial is widely available on
    macOS and Windows, making it a predictable school-report default.
    """
    try:
        family = "Arial"
        regular_path = font_manager.findfont(
            font_manager.FontProperties(family=family, weight="normal"),
            fallback_to_default=False,
        )
        bold_path = font_manager.findfont(
            font_manager.FontProperties(family=family, weight="bold"),
            fallback_to_default=False,
        )
        regular_name = "SD_Arial_Regular"
        bold_name = "SD_Arial_Bold"
        if regular_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(regular_name, regular_path))
        if bold_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
        return regular_name, bold_name, family
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica"


FONT_REGULAR, FONT_BOLD, RESOLVED_FONT_FAMILY = _register_font_family()


_SHORT_TOPIC_LABELS = {
    "P3-DIV-LNL": "Living & Non-Living",
    "P3-DIV-MAT": "Materials",
    "P3-CYC-LC": "Life Cycles",
    "P3-INT-MAG": "Magnets",
}


def short_topic_label(topic_code: str, official_topic: str) -> str:
    """Return a compact display label without changing curriculum metadata."""
    code = _safe(topic_code).strip()
    if code in _SHORT_TOPIC_LABELS:
        return _SHORT_TOPIC_LABELS[code]

    official = _safe(official_topic).strip()
    match = re.search(r"\(([^()]*)\)\s*$", official)
    if match:
        inner = match.group(1).strip()
        if inner and len(inner) <= 30:
            return inner
    if len(official) <= 34:
        return official
    return official[:31].rstrip() + "..."


class PerformanceTrack(Flowable):
    """Thin 0-100 performance line with a dot at the exact percentage."""

    def __init__(self, percent: float, width=42 * mm, height=7 * mm):
        super().__init__()
        self.percent = max(0.0, min(100.0, float(percent)))
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        y = self.height / 2
        canvas.setStrokeColor(colors.HexColor("#C7C7CC"))
        canvas.setLineWidth(1.2)
        canvas.line(1.5, y, self.width - 1.5, y)
        x = 1.5 + (self.width - 3.0) * self.percent / 100.0
        canvas.setFillColor(colors.HexColor("#1F78B4"))
        canvas.circle(x, y, 2.4, fill=1, stroke=0)


def make_topic_performance_chart(topic_rows: pd.DataFrame) -> BytesIO:
    """Backward-compatible compact dot plot; PDFs use the matrix instead."""
    if topic_rows.empty:
        raise ValueError("No topic rows supplied for chart.")
    chart = topic_rows.copy()
    chart["Percent_Correct"] = pd.to_numeric(chart["Percent_Correct"], errors="coerce").fillna(0)
    labels = [
        short_topic_label(row.get("Topic_Code", ""), row.get("Official Topic", ""))
        for _, row in chart.iterrows()
    ]
    height = max(1.8, 0.34 * len(chart) + 0.8)
    fig, ax = plt.subplots(figsize=(6.4, height))
    y = list(range(len(chart)))
    values = chart["Percent_Correct"].tolist()
    ax.hlines(y, 0, 100, linewidth=1.1, alpha=0.35)
    ax.scatter(values, y, s=34)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 50, 100])
    ax.set_xlabel("Correct responses (%)", fontsize=9)
    ax.tick_params(axis="x", labelsize=8)
    for ypos, (_, row) in zip(y, chart.iterrows()):
        pct = float(row["Percent_Correct"])
        correct = int(row["Correct"])
        total = int(row["Questions"])
        ax.text(min(pct + 3, 94), ypos, f"{correct}/{total}", va="center", fontsize=8)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    mem = BytesIO()
    fig.savefig(mem, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    mem.seek(0)
    return mem


def _styles(compact: bool = False):
    styles = getSampleStyleSheet()
    body_leading = 11.3 if compact else 12.0
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName=FONT_BOLD,
        fontSize=16, leading=18, alignment=TA_CENTER, spaceAfter=5,
    )
    h2 = ParagraphStyle(
        "Heading2Custom", parent=styles["Heading2"], fontName=FONT_BOLD,
        fontSize=REPORT_BODY_FONT_SIZE, leading=12, spaceBefore=5 if compact else 7,
        spaceAfter=3,
    )
    body = ParagraphStyle(
        "BodyCustom", parent=styles["BodyText"], fontName=FONT_REGULAR,
        fontSize=REPORT_BODY_FONT_SIZE, leading=body_leading, spaceAfter=1,
    )
    body_bold = ParagraphStyle(
        "BodyBold", parent=body, fontName=FONT_BOLD,
    )
    bullet = ParagraphStyle(
        "BulletCustom", parent=body, leftIndent=9, firstLineIndent=-5,
        spaceAfter=1.5,
    )
    footer = ParagraphStyle(
        "Footer", parent=body, fontSize=REPORT_BODY_FONT_SIZE, leading=11,
        textColor=colors.HexColor("#555555"),
    )
    return title, h2, body, body_bold, bullet, footer


def _topic_matrix(topic_rows: pd.DataFrame, body, body_bold):
    rows = [[
        Paragraph("Topic", body_bold),
        Paragraph("Evidence", body_bold),
        Paragraph("Performance", body_bold),
        Paragraph("0 - 100%", body_bold),
    ]]
    sorted_rows = topic_rows.sort_values([c for c in ["Topic_Code", "Official Topic"] if c in topic_rows.columns])
    for _, row in sorted_rows.iterrows():
        percent = float(row.get("Percent_Correct", 0) or 0)
        correct = int(row.get("Correct", 0) or 0)
        questions = int(row.get("Questions", 0) or 0)
        label = short_topic_label(row.get("Topic_Code", ""), row.get("Official Topic", ""))
        rows.append([
            Paragraph(escape(label), body),
            Paragraph(f"{correct}/{questions}", body),
            Paragraph(f"{percent:.0f}%", body),
            PerformanceTrack(percent),
        ])
    table = Table(rows, colWidths=[55*mm, 24*mm, 25*mm, 48*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F2F2F7")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1D1D1F")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D2D2D7")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return table


def _concept_table(student_lo_rows: pd.DataFrame, body, body_bold, include_score: bool):
    rows = [[
        Paragraph("Topic", body_bold),
        Paragraph("Concept", body_bold),
        Paragraph("Evidence", body_bold),
    ]]
    sort_cols = [c for c in ["Official Topic", "LO_ID"] if c in student_lo_rows.columns]
    frame = student_lo_rows.sort_values(sort_cols) if sort_cols else student_lo_rows
    for _, row in frame.iterrows():
        evidence = f"{int(row['Correct'])} of {int(row['Questions'])} correct"
        if include_score:
            evidence += f" ({float(row['Percent_Correct']):.0f}%)"
        label = short_topic_label(row.get("Topic_Code", ""), row.get("Official Topic", ""))
        rows.append([
            Paragraph(escape(label), body),
            Paragraph(escape(_safe(row.get("Official Learning Outcome", ""))), body),
            Paragraph(escape(evidence), body),
        ])
    table = Table(rows, colWidths=[38*mm, 91*mm, 41*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F2F2F7")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1D1D1F")),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#D2D2D7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return table


def _build_pdf(
    student_lo_rows: pd.DataFrame,
    student_topic_rows: pd.DataFrame,
    output_path: Path,
    report_title: str,
    checkpoint_label: str,
    include_score: bool,
    gemini_analysis,
    compact: bool,
):
    title_style, h2, body, body_bold, bullet, footer = _styles(compact=compact)
    margin = 12*mm if compact else 14*mm
    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4, rightMargin=margin, leftMargin=margin,
        topMargin=11*mm if compact else 13*mm, bottomMargin=11*mm if compact else 13*mm,
        title=report_title,
    )

    class_name = _safe(student_lo_rows["Class_Name"].iloc[0])
    index_number = _safe(student_lo_rows["Index_Number"].iloc[0])
    story = [
        Paragraph(escape(report_title), title_style),
        Paragraph(
            f"<b>Class:</b> {escape(class_name)} &nbsp;&nbsp; <b>Index no.:</b> {escape(index_number)}",
            body,
        ),
    ]
    if checkpoint_label:
        story.append(Paragraph(f"<b>Checkpoint:</b> {escape(checkpoint_label)}", body))

    story.extend([
        Spacer(1, 2.0*mm if compact else 2.8*mm),
        Paragraph("About this diagnostic", h2),
        Paragraph(
            "This low-stakes Science diagnostic identifies concepts that may benefit from further revision. "
            "It is not a Weighted Assessment; the results are evidence to guide learning, not a final judgement of mastery.",
            body,
        ),
        Paragraph("Performance by topic", h2),
        _topic_matrix(student_topic_rows, body, body_bold),
        Paragraph("Concept breakdown", h2),
        _concept_table(student_lo_rows, body, body_bold, include_score),
    ])

    if gemini_analysis is not None:
        ai = gemini_analysis.model_dump() if hasattr(gemini_analysis, "model_dump") else dict(gemini_analysis)
        summary = _safe(ai.get("response_pattern_summary", "")).strip()
        if summary:
            story.extend([
                Paragraph("What the response pattern suggests", h2),
                Paragraph(escape(summary), body),
            ])
        concepts = ai.get("concepts_to_revisit", []) or []
        if concepts:
            story.append(Paragraph("Concepts to revisit", h2))
            for text in concepts[:4]:
                story.append(Paragraph("• " + escape(_safe(text)), bullet))
        next_steps = ai.get("suggested_next_steps", []) or ai.get("how_parents_can_help", []) or []
        if next_steps:
            story.append(Paragraph("Suggested next steps", h2))
            for text in next_steps[:3]:
                story.append(Paragraph("• " + escape(_safe(text)), bullet))

    story.extend([
        Spacer(1, 2.0*mm if compact else 3.0*mm),
        Paragraph(
            "This report is based on a diagnostic snapshot. Understanding should be checked again later using different questions.",
            footer,
        ),
    ])
    doc.build(story)


def _pdf_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception as exc:
        raise RuntimeError("Could not verify the generated PDF page count.") from exc


def generate_student_pdf(
    student_lo_rows: pd.DataFrame,
    student_topic_rows: pd.DataFrame,
    output_path,
    report_title,
    checkpoint_label="",
    include_score=False,
    gemini_analysis=None,
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if student_lo_rows.empty or student_topic_rows.empty:
        raise ValueError("Pupil LO and topic rows are required.")

    _build_pdf(
        student_lo_rows, student_topic_rows, output_path, report_title,
        checkpoint_label, include_score, gemini_analysis, compact=False,
    )
    pages = _pdf_page_count(output_path)
    if pages > MAX_REPORT_PAGES:
        _build_pdf(
            student_lo_rows, student_topic_rows, output_path, report_title,
            checkpoint_label, include_score, gemini_analysis, compact=True,
        )
        pages = _pdf_page_count(output_path)
    if pages > MAX_REPORT_PAGES:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Report exceeded the {MAX_REPORT_PAGES}-page limit even after compact layout. "
            "Reduce report narrative or concept rows before generating again."
        )
    return output_path


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 _-]+", "", str(value or "").strip())
    value = re.sub(r"\s+", "_", value).strip("_-")
    return value or "Pupil"




def combine_pdf_files(input_paths, output_path):
    """Merge report PDFs into one ordered document.

    The input files are not modified. The caller controls ordering.
    """
    from pypdf import PdfReader, PdfWriter

    input_paths = [Path(p) for p in input_paths if Path(p).exists()]
    if not input_paths:
        raise ValueError("At least one PDF is required to build the combined report.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for path in input_paths:
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def combined_report_filename(checkpoint_label: str = "") -> str:
    checkpoint = _safe_filename(checkpoint_label)
    if checkpoint_label and checkpoint != "Pupil":
        return f"science_diagnostic_complete_report_{checkpoint}.pdf"
    return "science_diagnostic_complete_report.pdf"

def report_zip_filename(checkpoint_label: str = "") -> str:
    checkpoint = _safe_filename(checkpoint_label)
    if checkpoint_label and checkpoint != "Pupil":
        return f"science_diagnostic_reports_{checkpoint}.zip"
    return "science_diagnostic_reports.zip"


def generate_reports_for_class(
    student_lo_summary: pd.DataFrame,
    student_topic_summary: pd.DataFrame,
    output_dir,
    report_title,
    checkpoint_label="",
    include_score=False,
    gemini_analyses=None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    gemini_analyses = gemini_analyses or {}
    required = {"Response_ID", "Class_Name", "Index_Number", "Pupil_Key"}
    missing = required - set(student_lo_summary.columns)
    if missing:
        raise ValueError(f"Missing report columns: {sorted(missing)}")

    paths = []
    used_names = {}

    meta = (
        student_lo_summary[["Response_ID", "Class_Name", "Index_Number"]]
        .drop_duplicates(subset=["Response_ID"])
        .copy()
    )
    meta["_ClassSort"] = meta["Class_Name"].astype(str).str.casefold()
    meta["_IndexNumeric"] = pd.to_numeric(meta["Index_Number"], errors="coerce")
    meta["_IndexText"] = meta["Index_Number"].astype(str)
    meta = meta.sort_values(
        ["_ClassSort", "_IndexNumeric", "_IndexText"],
        na_position="last",
        kind="stable",
    )

    for response_id in meta["Response_ID"].astype(str):
        lo_rows = student_lo_summary[
            student_lo_summary["Response_ID"].astype(str).eq(response_id)
        ].copy()
        topic_rows = student_topic_summary[
            student_topic_summary["Response_ID"].astype(str).eq(response_id)
        ].copy()
        class_name = _safe(lo_rows["Class_Name"].iloc[0])
        index_number = _safe(lo_rows["Index_Number"].iloc[0])
        base = _safe_filename(f"{class_name}_{index_number}")
        used_names[base] = used_names.get(base, 0) + 1
        suffix = "" if used_names[base] == 1 else f"_{used_names[base]:02d}"
        path = output_dir / f"{base}{suffix}_Science_Diagnostic.pdf"
        generate_student_pdf(
            lo_rows, topic_rows, path, report_title=report_title,
            checkpoint_label=checkpoint_label, include_score=include_score,
            gemini_analysis=gemini_analyses.get(str(response_id)),
        )
        paths.append(path)
    return paths
