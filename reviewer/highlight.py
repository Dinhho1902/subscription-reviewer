"""Render a PDF page with evidence quotes highlighted, so a reviewer sees exactly where each
finding comes from. `crop` returns a zoomed strip around specific quotes."""

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


def _rects(textpage, quote: str) -> list[tuple]:
    hit = _find(textpage, quote)
    return [textpage.get_rect(i) for i in range(textpage.count_rects(*hit))] if hit else []


def render(pdf_bytes: bytes, page_index: int, marks: list[tuple[str, str]],
           scale: float = SCALE) -> tuple[Image.Image, int]:
    """marks: [(quote, kind)] with kind in COLORS. Returns the image and how many marks were found."""
    page = pdfium.PdfDocument(pdf_bytes)[page_index]
    _, height = page.get_size()
    image = page.render(scale=scale).to_pil().convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    textpage = page.get_textpage()
    found = 0
    for quote, kind in marks:
        rects = _rects(textpage, quote)
        if not rects:
            continue
        found += 1
        outline, fill = COLORS.get(kind, COLORS["warning"])
        for left, bottom, right, top in rects:
            box = [left * scale - 4, (height - top) * scale - 4, right * scale + 4, (height - bottom) * scale + 4]
            draw.rectangle(box, fill=fill, outline=outline, width=3)
    return Image.alpha_composite(image, overlay).convert("RGB"), found


def crop(pdf_bytes: bytes, page_index: int, quotes: list[str], kind: str = "critical",
         pad_pt: float = 16, scale: float = 2.4) -> Image.Image | None:
    """A zoomed strip of the page around the given quotes, with the quotes highlighted."""
    page = pdfium.PdfDocument(pdf_bytes)[page_index]
    width, height = page.get_size()
    textpage = page.get_textpage()
    rects = [r for q in quotes for r in _rects(textpage, q)]
    if not rects:
        return None
    top, bottom = max(r[3] for r in rects), min(r[1] for r in rects)
    image, _ = render(pdf_bytes, page_index, [(q, kind) for q in quotes], scale=scale)
    left, right = min(r[0] for r in rects), max(r[2] for r in rects)
    box = (int(max(0, left - 14) * scale), int(max(0, height - top - pad_pt) * scale),
           int(min(width, right + 40) * scale), int(min(height, height - bottom + pad_pt) * scale))
    return image.crop(box)
