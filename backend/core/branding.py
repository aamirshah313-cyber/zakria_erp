"""MZS logo placement shared by PDF, Excel and image reports.

The logo is generated from branding/mzs-logo.svg by branding/build_assets.py.
CSV exports cannot carry images and stay plain.
"""
from functools import lru_cache
from pathlib import Path

LOGO = Path(__file__).resolve().parents[1] / 'resources' / 'branding' / 'mzs-logo.png'
# Space reserved above report content for the logo, in PDF points.
PDF_LOGO_HEIGHT = 38
PDF_HEADER_SPACE = 58
XLSX_BANNER_ROWS = 4


@lru_cache(maxsize=1)
def logo_size():
    from PIL import Image
    with Image.open(LOGO) as image:
        return image.size


def draw_pdf_logo(canvas, page_width, page_height, margin, accent):
    """Logo at the top-left of every page with a rule beneath it."""
    from reportlab.lib.utils import ImageReader
    width, height = logo_size()
    drawn_width = PDF_LOGO_HEIGHT * width / height
    top = page_height - 14
    canvas.drawImage(ImageReader(str(LOGO)), margin, top - PDF_LOGO_HEIGHT, drawn_width, PDF_LOGO_HEIGHT, mask='auto')
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(1)
    canvas.line(margin, top - PDF_LOGO_HEIGHT - 6, page_width - margin, top - PDF_LOGO_HEIGHT - 6)


def add_xlsx_banner(sheet):
    """Reserve logo rows on an empty sheet; content appended afterwards starts
    at row XLSX_BANNER_ROWS + 1. Returns that first content row."""
    from openpyxl.drawing.image import Image as SheetImage
    # Inspect stored cells directly: reading sheet['A1'] would create a row.
    if sheet._cells:
        raise ValueError('Add the logo banner before writing sheet content.')
    for row in range(1, XLSX_BANNER_ROWS + 1):
        sheet.append([])
        sheet.row_dimensions[row].height = 18
    image = SheetImage(str(LOGO))
    width, height = logo_size()
    image.height = 64
    image.width = round(64 * width / height)
    sheet.add_image(image, 'A1')
    return XLSX_BANNER_ROWS + 1


def logo_image(height):
    from PIL import Image
    with Image.open(LOGO) as image:
        logo = image.convert('RGBA')
    return logo.resize((round(height * logo.width / logo.height), height), Image.LANCZOS)
