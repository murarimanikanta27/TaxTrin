"""TD4 certificate OCR via Tesseract (through the `pytesseract` wrapper).

Scope for this POC: Tesseract is a mature, lightweight, non-ML-framework OCR
engine (no PyTorch/vLLM/GPU needed, unlike the newer Surya OCR models), which
matches the "keep it lite" requirement for a proof-of-concept drag-and-drop
TD4 upload feature. It reads printed text well; it will struggle with messy
handwriting or heavily skewed photos of paper certificates -- acceptable for
this POC's goal of proving the workflow, but a real product would likely
upgrade to a document-specific OCR/LLM model for production accuracy on
photographed (rather than scanned) certificates.

Supported inputs:
  - Images: PNG, JPEG, WEBP, TIFF, BMP (anything Pillow can open) -> OCR'd
    directly with Tesseract.
  - PDFs (single or multi-page): text is extracted natively via `pdfplumber`
    first, since a PDF that already has a text layer (e.g. a TD4 exported
    straight from e-Tax or produced digitally) gives faster, exact text with
    no OCR error at all. Any page that comes back with no/near-no extractable
    text (i.e. it's a scanned image embedded in the PDF, not real text) is
    rendered to a bitmap via `pypdfium2` and OCR'd with Tesseract instead.
    Multi-page PDFs have every page's text concatenated in order.

This module does two things:
  1. Run OCR/extraction on an uploaded file, returning raw text + a
     confidence score.
  2. Heuristically parse TD4-shaped fields (employer/employee names, BIR
     numbers, gross earnings, NIS/PAYE amounts, etc.) out of that raw text
     using label-based regexes, since neither Tesseract nor pdfplumber give
     us semantic field extraction on their own.

The parsed result is intentionally treated as a *starting point* for the
"live manual correction side-by-side" UI the spec calls for, not a final
answer -- every extracted field is expected to be reviewed/edited by the
user before the TD4Input is saved. `ocr_confidence` on the resulting record
reflects the underlying extraction confidence (1.0 for a native PDF text
layer, Tesseract's own mean word confidence for anything OCR'd), not the
accuracy of the field parsing on top of it.
"""
import re
from dataclasses import dataclass, field
from io import BytesIO

import pdfplumber
import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from app.config import get_settings

settings = get_settings()

if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

# A PDF page that extracts fewer than this many non-whitespace characters of
# native text is treated as scanned/image-only and rendered+OCR'd instead.
_MIN_NATIVE_TEXT_CHARS = 20

# DPI-equivalent render scale for OCR fallback on scanned PDF pages. 2.0x the
# default 72 DPI (=144 DPI) is a reasonable accuracy/speed tradeoff for
# printed certificates; pushing higher helps small text but slows OCR down.
_PDF_RENDER_SCALE = 2.0


@dataclass
class OCRResult:
    raw_text: str
    confidence: float  # 0.0-1.0 (1.0 for native PDF text; Tesseract's mean word confidence otherwise)
    fields: dict = field(default_factory=dict)
    page_count: int = 1


def _looks_like_pdf(file_bytes: bytes) -> bool:
    return file_bytes[:5] == b"%PDF-"


def run_ocr(file_bytes: bytes) -> OCRResult:
    """Extract text from an uploaded TD4 certificate file (image or PDF).

    Raises ValueError if the bytes aren't a readable image or PDF, and a
    pytesseract.TesseractNotFoundError (propagated as-is) if the Tesseract
    binary itself isn't installed/configured -- callers should turn both into
    a clean 4xx for the API.
    """
    if _looks_like_pdf(file_bytes):
        return _run_ocr_on_pdf(file_bytes)
    return _run_ocr_on_image(file_bytes)


def _run_ocr_on_image(image_bytes: bytes) -> OCRResult:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except Exception as exc:  # Pillow raises a variety of exception types
        raise ValueError(f"Could not read the uploaded file as an image: {exc}") from exc

    raw_text, confidence = _ocr_image(image)
    return OCRResult(raw_text=raw_text, confidence=confidence, page_count=1)


def _run_ocr_on_pdf(pdf_bytes: bytes) -> OCRResult:
    try:
        plumber_doc = pdfplumber.open(BytesIO(pdf_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read the uploaded file as a PDF: {exc}") from exc

    try:
        page_count = len(plumber_doc.pages)
        if page_count == 0:
            raise ValueError("The uploaded PDF has no pages.")

        pdfium_doc: pdfium.PdfDocument | None = None
        page_texts: list[str] = []
        page_confidences: list[float] = []

        for index, plumber_page in enumerate(plumber_doc.pages):
            native_text = (plumber_page.extract_text() or "").strip()

            if len(re.sub(r"\s", "", native_text)) >= _MIN_NATIVE_TEXT_CHARS:
                # Real text layer present -- use it directly. No OCR error
                # possible here, so treat this page's confidence as perfect.
                page_texts.append(native_text)
                page_confidences.append(1.0)
                continue

            # No usable text layer (scanned page) -- render it to a bitmap
            # and OCR that instead. pdfium is opened lazily/once since most
            # certificates are a single page and many won't need this path.
            if pdfium_doc is None:
                pdfium_doc = pdfium.PdfDocument(BytesIO(pdf_bytes))
            rendered_page = pdfium_doc[index]
            bitmap = rendered_page.render(scale=_PDF_RENDER_SCALE)
            pil_image = bitmap.to_pil()
            ocr_text, ocr_confidence = _ocr_image(pil_image)
            page_texts.append(ocr_text)
            page_confidences.append(ocr_confidence)

        combined_text = "\n\n".join(text for text in page_texts if text)
        mean_confidence = round(sum(page_confidences) / len(page_confidences), 4) if page_confidences else 0.0

        return OCRResult(raw_text=combined_text, confidence=mean_confidence, page_count=page_count)
    finally:
        plumber_doc.close()


def _ocr_image(image: Image.Image) -> tuple[str, float]:
    """Run Tesseract on a single PIL image, returning (text, mean_confidence)."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [
        float(c) for c, w in zip(data.get("conf", []), data.get("text", [])) if w and w.strip() and float(c) >= 0
    ]
    raw_text = "\n".join(_reconstruct_lines(data))
    mean_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return raw_text, round(mean_confidence, 4)


def _reconstruct_lines(data: dict) -> list[str]:
    """Group Tesseract's word-level output back into lines using its own
    (page, block, paragraph, line) grouping keys, since image_to_string alone
    doesn't give us confidence and image_to_data alone gives words, not lines."""
    lines: dict[tuple, list[str]] = {}
    n = len(data.get("text", []))
    for i in range(n):
        word = data["text"][i]
        if not word or not word.strip():
            continue
        key = (data["page_num"][i], data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
    return [" ".join(words) for words in lines.values()]


# ---------------------------------------------------------------------------
# Heuristic field extraction
# ---------------------------------------------------------------------------

_MONEY = r"[\$]?\s*([\d][\d,]*\.\d{2}|[\d][\d,]*)"


def _find_money(text: str, *label_patterns: str) -> float | None:
    """Look for `label ... amount` on the same line, trying each label
    pattern in order and returning the first match. Amounts are parsed with
    commas stripped (e.g. "12,345.67" -> 12345.67)."""
    for label in label_patterns:
        pattern = rf"{label}\s*[:\-]?\s*{_MONEY}"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _find_text(text: str, *label_patterns: str) -> str | None:
    for label in label_patterns:
        pattern = rf"{label}\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9 ,.'\-]{{2,80}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(",")
    return None


def _find_bir_number(text: str, *label_patterns: str) -> str | None:
    """BIR numbers are 7-10 digits, optionally with leading zeros already
    stripped on the printed certificate."""
    for label in label_patterns:
        pattern = rf"{label}\s*[:\-]?\s*(\d{{7,10}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_td4_fields(raw_text: str) -> dict:
    """Best-effort extraction of TD4Input-shaped fields from OCR'd text.

    Every value returned here is a *suggestion*: field names match
    TD4Input's columns so the API can hand them straight to the frontend's
    manual-correction form, but nothing here is saved without the user
    reviewing/editing it first (see TD4Input.manually_corrected).
    """
    text = raw_text

    fields: dict = {
        "employer_name": _find_text(text, "Employer(?:'s)? Name", "Name of Employer"),
        "employer_bir_number": _find_bir_number(text, "Employer(?:'s)? BIR (?:No|Number)", "Employer BIR"),
        "employee_name": _find_text(text, "Employee(?:'s)? Name", "Name of Employee"),
        "employee_bir_number": _find_bir_number(text, "Employee(?:'s)? BIR (?:No|Number)", "Employee BIR"),
        "employee_address": _find_text(text, "Address"),
        "employee_nis_number": _find_bir_number(text, "NIS (?:No|Number)"),
        "remuneration": _find_money(text, "Remuneration"),
        "commission": _find_money(text, "Commission"),
        "gross_earnings": _find_money(text, "Gross (?:Earnings|Emoluments|Income)", "Total Emoluments"),
        "nis_deducted": _find_money(text, "NIS Deducted", "NIS Contribution"),
        "income_tax": _find_money(text, "Income Tax(?: Deducted)?", "PAYE(?: Deducted)?", "Tax Deducted"),
        "health_surcharge_amount": _find_money(text, "Health Surcharge"),
        "total_deductions": _find_money(text, "Total Deductions"),
    }

    return {k: v for k, v in fields.items() if v is not None}
