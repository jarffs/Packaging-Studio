"""Convert PDF dielines to SVG so they enter the same processing pipeline.

PyMuPDF (``fitz``) is imported lazily; PDF support is optional and only
required at runtime when importing a ``.pdf`` file.
"""

from __future__ import annotations


def pdf_page_count(filepath):
    """Return the number of pages in a PDF file."""
    import fitz

    doc = fitz.open(filepath)
    try:
        return len(doc)
    finally:
        doc.close()


def pdf_to_svg(filepath, page_number=0):
    """Return the SVG representation of a single PDF page."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - depends on runtime wheels
        raise RuntimeError(
            "PDF import requires PyMuPDF (fitz). Install the wheel to enable "
            "PDF support, or convert the dieline to SVG first."
        ) from exc

    doc = fitz.open(filepath)
    try:
        if page_number < 0 or page_number >= len(doc):
            page_number = 0
        page = doc[page_number]
        return page.get_svg_image()
    finally:
        doc.close()
