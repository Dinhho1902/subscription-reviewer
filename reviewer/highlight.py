"""Render a PDF page with evidence quotes highlighted, so a reviewer sees exactly where each
finding comes from."""

import re

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

SCALE = 1.6
COLORS = {  # outline, fill (RGBA)
    "critical": ((185, 28, 28, 255), (254, 202, 202, 110)),
    "warning": ((180, 83, 9, 255), (253, 230, 138, 120)),
    "ok": ((21, 128, 61, 255), (187, 247, 208, 110)),
}


def _find(textpage, quote: str):
    """Search for the quote; fall back to looser variants because PDF text spacing varies."""
    variants = [quote, re.sub(r"\s+", " ", quote), re.sub(r":\s*", ":  ", quote)]
    if ":" in quote:
        variants.append(quote.split(":", 1)[1].strip())
    for v in variants:
        if not v:
            continue
        hit = textpage.search(v, match_case=False).get_next()
        if hit:
            return hit
    return None


def render(pdf_bytes: bytes, page_index: int, marks: list[tuple[str, str]]) -> tuple[Image.Image, int]:
    """marks: [(quote, kind)] with kind in COLORS. Returns the image and how many marks were found."""
    doc = pdfium.PdfDocument(pdf_bytes)
    page = doc[page_index]
    _, height = page.get_size()
    image = page.render(scale=SCALE).to_pil().convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    textpage = page.get_textpage()
    found = 0
    for quote, kind in marks:
        hit = _find(textpage, quote)
        if not hit:
            continue
        found += 1
        outline, fill = COLORS.get(kind, COLORS["warning"])
        for i in range(textpage.count_rects(*hit)):
            left, bottom, right, top = textpage.get_rect(i)
            box = [left * SCALE - 4, (height - top) * SCALE - 4,
                   right * SCALE + 4, (height - bottom) * SCALE + 4]
            draw.rectangle(box, fill=fill, outline=outline, width=3)
    return Image.alpha_composite(image, overlay).convert("RGB"), found
