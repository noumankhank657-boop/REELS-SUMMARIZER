"""Create a clean, compact PDF containing only the five requested fields."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle


NAVY = colors.HexColor("#14283F")
TEAL = colors.HexColor("#DDF3EF")
INK = colors.HexColor("#263445")
MUTED = colors.HexColor("#607184")
WHITE = colors.white


def _text(value: Any) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def _items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def build_pdf(results: list[dict[str, Any]], output_path: Path) -> Path:
    """Write a styled reel card for each result, with no extra note fields."""
    if not results:
        raise ValueError("There are no reel results to put in the PDF.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReelCardTitle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=WHITE, alignment=TA_LEFT, spaceAfter=0))
    styles.add(ParagraphStyle(name="SectionBand", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=NAVY, spaceAfter=0))
    styles.add(ParagraphStyle(name="FieldLabel", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=INK, spaceAfter=0))
    styles.add(ParagraphStyle(name="FieldText", parent=styles["BodyText"], fontSize=9, leading=12, textColor=INK, spaceAfter=0))
    styles.add(ParagraphStyle(name="PageTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8))

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Sales Reel Notes",
        author="Personal Sales Learning Notes",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=[frame]))

    story: list[Any] = [_text_paragraph("Reel Notes", styles["PageTitle"])]
    for reel_number, result in enumerate(results, start=1):
        rows: list[list[Paragraph]] = [[Paragraph(f"REEL {reel_number}", styles["ReelCardTitle"])]]

        use_when = str(result.get("use_when", "Not specified in the reel")).strip()
        rows.append([Paragraph(f"<b>Use when:</b> {_text(use_when or 'Not specified in the reel')}", styles["FieldText"])])
        rows.append([Paragraph("CONTENT PART", styles["SectionBand"])])

        content_ideas = _items(result.get("content_ideas")) or ["Not covered"]
        rows.append([Paragraph("<b>1. Content ideas</b>", styles["FieldLabel"])])
        for number, idea in enumerate(content_ideas, start=1):
            rows.append([Paragraph(f"{number}. {_text(idea)}", styles["FieldText"])])

        rows.append([Paragraph(f"<b>2. How the hook works</b><br/>{_text(result.get('hook_mechanics', 'Not covered'))}", styles["FieldText"])])
        rows.append([Paragraph(f"<b>3. Hook pattern</b><br/>{_text(result.get('hook_pattern', 'Not covered'))}", styles["FieldText"])])
        rows.append([Paragraph("SALES PART", styles["SectionBand"])])

        sales_advice = _items(result.get("sales_advice")) or ["Not covered"]
        rows.append([Paragraph("<b>1. Sales advice</b>", styles["FieldLabel"])])
        for number, advice in enumerate(sales_advice, start=1):
            rows.append([Paragraph(f"{number}. {_text(advice)}", styles["FieldText"])])

        card = Table(rows, colWidths=[doc.width], hAlign="LEFT")
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("BACKGROUND", (0, 2), (-1, 2), TEAL),
            ("BACKGROUND", (0, -len(sales_advice)-2), (-1, -len(sales_advice)-2), TEAL),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D4DEE8")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, NAVY),
            ("LEFTPADDING", (0, 0), (-1, -1), 11),
            ("RIGHTPADDING", (0, 0), (-1, -1), 11),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(KeepTogether([card, Spacer(1, 0.18 * inch)]))

    doc.build(story)
    return output_path


def _text_paragraph(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_text(value), style)
