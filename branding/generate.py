#!/usr/bin/env python3
"""Generates every Kill-Day OS branding asset from branding/logo/killday-skull.svg."""
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
SVG = ROOT / "logo" / "killday-skull.svg"
FONTS = ROOT / "fonts"
PRESS = FONTS / "PressStart2P-Regular.ttf"
MONO = FONTS / "JetBrainsMono[wght].ttf"

BG = (0x0B, 0x0F, 0x0C)
GREEN = (0x8C, 0xFF, 0x5A)
RED = (0xFF, 0x3B, 0x4E)
BONE = (0xE6, 0xEB, 0xE0)
MUTED = (0x9D, 0xB0, 0x9A)
TAGLINE = "Corrupted? Still alive."


def skull(size):
    out = subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(SVG)],
        check=True, capture_output=True,
    ).stdout
    from io import BytesIO
    return Image.open(BytesIO(out)).convert("RGBA")


def mono(size, weight="Regular"):
    font = ImageFont.truetype(str(MONO), size)
    font.set_variation_by_name(weight)
    return font


def text_image(text, font, fill, pad=6):
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
    img = Image.new("RGBA", (right - left + pad * 2, bottom - top + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - left, pad - top), text, font=font, fill=fill)
    return img


def wordmark(height=96):
    """KILL-DAY OS in Press Start 2P, green with a soft glow and a red hyphen."""
    font = ImageFont.truetype(str(PRESS), height)
    parts = [("KILL", GREEN), ("-", RED), ("DAY OS", GREEN)]
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    width = sum(int(probe.textlength(p, font=font)) for p, _ in parts)
    pad = height // 2
    canvas_img = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas_img)
    x = pad
    for part, colour in parts:
        draw.text((x, pad), part, font=font, fill=colour + (255,))
        x += int(probe.textlength(part, font=font))
    glow = canvas_img.filter(ImageFilter.GaussianBlur(height // 7))
    return Image.alpha_composite(glow, canvas_img)


def glitch(img, rng, strength, slices):
    """Offsets horizontal bands of the skull and splits colour channels at the cuts."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    w, h = img.size
    y = 0
    while y < h:
        band = rng.randint(h // (slices * 2), h // slices)
        offset = rng.randint(-strength, strength) if rng.random() < 0.7 else 0
        out.paste(img.crop((0, y, w, min(h, y + band))), (offset, y))
        y += band
    r, g, b, a = out.split()
    if strength:
        shift = max(1, strength // 5)
        r = ImageChops.offset(r, shift, 0)
        b = ImageChops.offset(b, -shift, 0)
    return Image.merge("RGBA", (r, g, b, a))


def logos():
    target = ROOT / "png"
    target.mkdir(exist_ok=True)
    for size in (16, 32, 64, 128, 256, 512):
        skull(size).save(target / f"killday-skull-{size}.png")
    # Icons need a solid plate: the glitch bars are drawn in the background colour.
    plate = Image.new("RGBA", (256, 256), BG + (255,))
    plate.alpha_composite(skull(256))
    plate.save(ROOT / "png" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    plate.resize((32, 32), Image.LANCZOS).save(ROOT / "png" / "favicon-32.png")
    (ROOT / "wordmark").mkdir(exist_ok=True)
    wordmark().save(ROOT / "wordmark" / "killday-wordmark.png")


def scanlines(img, spacing=4, alpha=38):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, img.size[1], spacing):
        draw.line([(0, y), (img.size[0], y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img, overlay)


def wallpaper(width=2560, height=1440):
    img = Image.new("RGBA", (width, height), BG + (255,))
    mark = skull(int(height * 0.8))
    alpha = mark.getchannel("A").point(lambda v: int(v * 0.13))
    mark.putalpha(alpha)
    img.alpha_composite(mark, ((width - mark.width) // 2, (height - mark.height) // 2))
    img = scanlines(img)
    tag = text_image(TAGLINE, mono(30), MUTED + (150,))
    # Centred, because the desktop crops the sides on narrower screens.
    img.alpha_composite(tag, ((width - tag.width) // 2, height - tag.height - 150))
    (ROOT / "wallpaper").mkdir(exist_ok=True)
    img.convert("RGB").save(ROOT / "wallpaper" / "killday-wallpaper.png", optimize=True)


def grub_theme():
    out = ROOT / "grub" / "theme"
    out.mkdir(parents=True, exist_ok=True)
    width, height = 1024, 768
    img = Image.new("RGBA", (width, height), BG + (255,))
    mark = skull(190)
    img.alpha_composite(mark, ((width - mark.width) // 2, 30))
    word = wordmark(38)
    img.alpha_composite(word, ((width - word.width) // 2, 200))
    img = scanlines(img, spacing=3, alpha=30)
    img.convert("RGB").save(out / "background.png", optimize=True)
    selected = Image.new("RGBA", (8, 8), (0x8C, 0xFF, 0x5A, 56))
    selected.save(out / "select_c.png")
    for name, source, size in (
        ("mono-18", MONO, 18), ("mono-16", MONO, 16), ("mono-14", MONO, 14),
    ):
        subprocess.run(
            ["grub-mkfont", "-s", str(size), "-n", "KillDay Mono", "-o", str(out / f"{name}.pf2"), str(source)],
            check=True,
        )


def plymouth_theme():
    out = ROOT / "plymouth" / "killday"
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1337)
    base = skull(360)
    frame_count = 24
    for index in range(frame_count):
        progress = index / (frame_count - 1)
        strength = int(48 * (1 - progress) ** 1.5)
        frame = glitch(base, rng, strength, 12) if strength else base.copy()
        # A few blackout flickers while the skull is still "corrupted".
        opacity = 0.25 if index in (1, 4, 9) else min(1.0, 0.55 + progress)
        frame.putalpha(frame.getchannel("A").point(lambda v: int(v * opacity)))
        frame.save(out / f"skull-{index:02d}.png", optimize=True)
    base.save(out / "skull-final.png", optimize=True)
    word = wordmark(30)
    word.save(out / "wordmark.png", optimize=True)
    for count in range(0, 4):
        label = f"DAY {-count}" if count else "DAY 0"
        text_image(label, mono(30, "Bold"), (RED if count else GREEN) + (255,)).save(out / f"day-{count}.png")
    text_image("ENTER PASSPHRASE TO UNLOCK YOUR ENCRYPTED STORAGE", mono(22), BONE + (255,)).save(out / "prompt.png")
    Image.new("RGBA", (16, 16), GREEN + (255,)).save(out / "bullet.png")


def usb_label():
    out = ROOT / "label"
    out.mkdir(exist_ok=True)
    pdfmetrics.registerFont(TTFont("Press", str(PRESS)))
    mark_path = ROOT / "png" / "killday-skull-512.png"
    pdf = canvas.Canvas(str(out / "killday-usb-label.pdf"), pagesize=letter)
    pdf.setTitle("Kill-Day OS USB label")
    page_w, page_h = letter
    label_w, label_h = 3.4 * inch, 1.25 * inch
    margin_x = (page_w - 2 * label_w - 0.2 * inch) / 2
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#333333"))
    pdf.drawString(margin_x, page_h - 0.45 * inch, "Print at 100% scale. Cut along the grey lines and tape over the USB stick or its case.")
    for row in range(7):
        for col in range(2):
            x = margin_x + col * (label_w + 0.2 * inch)
            y = page_h - 0.7 * inch - (row + 1) * (label_h + 0.08 * inch)
            pdf.setFillColor(HexColor("#0B0F0C"))
            pdf.setStrokeColor(HexColor("#999999"))
            pdf.rect(x, y, label_w, label_h, fill=1, stroke=1)
            pdf.drawImage(ImageReader(str(mark_path)), x + 0.08 * inch, y + 0.12 * inch,
                          1.0 * inch, 1.0 * inch, mask="auto")
            text_x = x + 1.15 * inch
            pdf.setFont("Press", 12)
            pdf.setFillColor(HexColor("#8CFF5A"))
            pdf.drawString(text_x, y + 0.82 * inch, "KILL")
            word_w = pdfmetrics.stringWidth("KILL", "Press", 12)
            pdf.setFillColor(HexColor("#FF3B4E"))
            pdf.drawString(text_x + word_w, y + 0.82 * inch, "-")
            pdf.setFillColor(HexColor("#8CFF5A"))
            pdf.drawString(text_x + word_w + pdfmetrics.stringWidth("-", "Press", 12), y + 0.82 * inch, "DAY OS")
            pdf.setFont("Helvetica", 9)
            pdf.setFillColor(HexColor("#E6EBE0"))
            pdf.drawString(text_x, y + 0.56 * inch, TAGLINE)
            pdf.setFillColor(HexColor("#9DB09A"))
            pdf.drawString(text_x, y + 0.36 * inch, "Boot this USB, or open START-HERE")
            pdf.drawString(text_x, y + 0.2 * inch, "on the KILLDAY_LIB drive.")
    pdf.save()


if __name__ == "__main__":
    logos()
    wallpaper()
    grub_theme()
    plymouth_theme()
    usb_label()
    print("branding generated")
