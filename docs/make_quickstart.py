#!/usr/bin/env python3
"""Generates the one-page 'If you're stuck' card as a printer-friendly PDF."""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, KeepInFrame, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[1]
INK = HexColor("#111111")
GREEN = HexColor("#2E7D12")  # A darker green than the screen palette, so it prints legibly.
RED = HexColor("#C3122A")

pdfmetrics.registerFont(TTFont("Press", str(ROOT / "branding/fonts/PressStart2P-Regular.ttf")))

HEAD = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=GREEN, spaceBefore=9, spaceAfter=3)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=12, leading=15.2, textColor=INK, alignment=TA_LEFT)
WARN = ParagraphStyle("warn", parent=BODY, fontName="Helvetica-Bold", textColor=RED)

SECTIONS = [
    ("1. Start the computer from this USB", [
        "Plug the USB into the computer and turn it on. Immediately tap the boot-menu key: usually <b>F12</b>, <b>F9</b>, <b>F10</b>, <b>F8</b> or <b>Esc</b>. Choose the entry naming your USB drive.",
        "No menu? Enter setup (<b>F2</b> or <b>Del</b>) and put USB first in the boot order.",
    ]),
    ("2. Pick from the skull menu", [
        "<b>Normal</b> is right for most people. It asks for your passphrase so your files are kept.",
        "Blank or garbled screen? Restart and choose <b>Safe graphics</b>.",
        "Do not want to enter a passphrase? Choose <b>Persistence off</b>. Nothing is saved in that mode.",
    ]),
    ("3. Secure Boot error or 'verification failed'", [
        "Enter setup (<b>F2</b> or <b>Del</b>), find <b>Secure Boot</b>, set it to <b>Disabled</b>, save and restart.",
    ]),
    ("4. Use the library", [
        "The Kill-Day Almanac opens by itself after login. Type a few plain words into the big search box. If the browser closes, double-click <b>The Kill-Day Almanac</b> on the desktop.",
    ]),
    ("5. The USB will not boot at all", [
        "Plug it into a working computer and open the drive named <b>KILLDAY_LIB</b>.",
        "<b>Windows:</b> double-click START-WINDOWS. <b>Mac:</b> double-click START-MAC. Keep the small window open.",
        "If those fail, open <b>START-HERE.html</b> for the guides directly. Encyclopedias (the zim folder) open in the free Kiwix app.",
    ]),
    ("6. Wrong passphrase", [
        "Press <b>Y</b> to try again, or <b>N</b> to continue without your saved files. Nobody can recover a forgotten passphrase. The library still works without it.",
    ]),
    ("7. Save battery", [
        "Double-click <b>Battery saver</b> on the desktop. Double-click it again to go back to normal.",
    ]),
]


def main():
    out = ROOT / "docs" / "killday-if-youre-stuck.pdf"
    width, height = letter
    pdf = canvas.Canvas(str(out), pagesize=letter)
    pdf.setTitle("Kill-Day OS: If you're stuck")
    pdf.setFillColor(HexColor("#0B0F0C"))
    pdf.rect(0, height - 1.15 * inch, width, 1.15 * inch, fill=1, stroke=0)
    pdf.drawImage(ImageReader(str(ROOT / "branding/png/killday-skull-256.png")), 0.5 * inch, height - 1.05 * inch, 0.95 * inch, 0.95 * inch, mask="auto")
    x = 1.65 * inch
    y = height - 0.55 * inch
    pdf.setFont("Press", 19)
    for part, colour in (("KILL", "#8CFF5A"), ("-", "#FF3B4E"), ("DAY OS", "#8CFF5A")):
        pdf.setFillColor(HexColor(colour))
        pdf.drawString(x, y, part)
        x += pdfmetrics.stringWidth(part, "Press", 19)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(HexColor("#E6EBE0"))
    pdf.drawString(1.65 * inch, height - 0.86 * inch, "If you're stuck. Corrupted? Still alive.")

    story = [Paragraph("In an emergency, contact emergency services or a qualified professional first if there is any way to do so. "
                       "Everything on this USB is reference material and is not a substitute for professional care.", WARN), Spacer(1, 3)]
    for title, lines in SECTIONS:
        story.append(Paragraph(title, HEAD))
        story += [Paragraph(line, BODY) for line in lines]
    frame = Frame(0.55 * inch, 0.5 * inch, width - 1.1 * inch, height - 1.75 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame.addFromList([KeepInFrame(width - 1.1 * inch, height - 1.75 * inch, story, mode="error")], pdf)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#555555"))
    pdf.drawCentredString(width / 2, 0.32 * inch, "Store this card with the USB. Write your passphrase hint here, not the passphrase: ______________________________")
    pdf.save()


if __name__ == "__main__":
    main()
