"""Shared helper(s) for PDF receipts.

This module exists to keep ReportLab banner rendering consistent across
invoice/bill/receipt generators while using correct static asset paths.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


BILL_HEADER_PATH = (
    Path(__file__).resolve().parents[1] / "static" / "img" / "bill-header.jpeg"
)


def draw_bill_header(pdf: canvas.Canvas, width: float, height: float) -> float:
    """Draw the branded bill header at the top and return next y position."""
    header_width = width - 40 * mm
    header_height = header_width * (156 / 682)
    header_bottom = height - 18 * mm - header_height

    if BILL_HEADER_PATH.exists() and BILL_HEADER_PATH.is_file():
        pdf.drawImage(
            str(BILL_HEADER_PATH),
            20 * mm,
            header_bottom,
            width=header_width,
            height=header_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        return header_bottom - 10 * mm

    # Fallback: keep layout stable if image is missing.
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(20 * mm, height - 25 * mm, "Vishal Bharat Furniture Works")
    return height - 45 * mm

