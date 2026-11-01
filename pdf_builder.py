"""Create a simple PDF containing only reel transcripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer


NAVY = colors.HexColor("#14283F")
INK = colors.HexColor("#263445")


def _text(value: Any) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def build_pdf(
    results: list[dict[str, Any]],
    output_path: Path,
    reel_numbers: list[int] | None = None,
) -> Path:
    """Write each reel's transcript without summaries or other generated fields."""
    if not results:
        raise ValueError("There are no reel transcripts to put in the PDF.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReelTitle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8))
    styles.add(ParagraphStyle(name="Transcript", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, textColor=INK, alignment=TA_LEFT, spaceAfter=0, splitLongWords=True))
    styles.add(ParagraphStyle(name="PageTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, alignment=TA_LEFT, spaceAfter=16))

    doc = BaseDocTemplate(
        str(output_path), pagesize=letter, rightMargin=0.7 * inch,
        leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch,
        title="Reel Transcripts", author="Personal Reel Transcripts",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=[frame]))

    story: list[Any] = [Paragraph("Reel Transcripts", styles["PageTitle"])]
    for index, result in enumerate(results):
        reel_number = reel_numbers[index] if reel_numbers else index + 1
        if index > 0:
            story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph(f"Reel {reel_number}", styles["ReelTitle"]))
        transcript = str(result.get("transcript", "")).strip()
        story.append(Paragraph(_text(transcript) if transcript else "No speech detected.", styles["Transcript"]))
        story.append(Spacer(1, 0.35 * inch))

    doc.build(story)
    return output_path
