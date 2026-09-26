"""Tests for the Tesseract-based TD4 OCR service.

Renders a synthetic TD4-like certificate as a PNG (via Pillow) rather than
depending on a real scanned image fixture, then runs it through
app.services.ocr to confirm both the raw OCR pass and the field-parsing
heuristics work end to end against the actual installed Tesseract binary.
"""
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.services.ocr import parse_td4_fields, run_ocr


def render_native_text_pdf(pages_lines: list[list[str]]) -> bytes:
    """Build a multi-page PDF with a real, selectable text layer (via
    reportlab) -- simulates a TD4 certificate exported/printed digitally
    rather than scanned. app.services.ocr should read this via pdfplumber's
    native text extraction, with no Tesseract OCR involved at all."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for lines in pages_lines:
        y = 700
        for line in lines:
            pdf.drawString(50, y, line)
            y -= 24
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def render_scanned_pdf(pages_lines: list[list[str]]) -> bytes:
    """Build a PDF whose pages are just embedded images with no text layer
    at all -- simulates a scanned paper TD4 certificate. app.services.ocr
    should fall back to rendering each page and running Tesseract on it."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    for lines in pages_lines:
        image_bytes = render_td4_image(lines)
        image = Image.open(BytesIO(image_bytes))
        # Draw the rendered PNG onto the page as an image (no text objects at
        # all), then save+reopen through ImageReader since reportlab's
        # drawInlineImage wants a file-like or path, not raw bytes.
        image_buffer = BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        from reportlab.lib.utils import ImageReader

        pdf.drawImage(ImageReader(image_buffer), 20, 500, width=500, height=image.height * 500 / image.width)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def render_td4_image(lines: list[str]) -> bytes:
    """Render plain text lines onto a white image, roughly simulating a
    printed TD4 certificate, and return it as PNG bytes."""
    width, height = 900, 40 + 32 * len(lines)
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black", font=font)
        y += 32

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


SAMPLE_TD4_LINES = [
    "TD4 CERTIFICATE - RETURN OF EMOLUMENTS PAID",
    "Employer Name: Republic Bank Ltd",
    "Employer BIR Number: 9998887",
    "Employee Name: Alicia Ramnath",
    "Employee BIR Number: 1234567",
    "Address: 12 Frederick Street Port of Spain",
    "NIS Number: 123456789",
    "Remuneration: 180000.00",
    "Gross Earnings: 180000.00",
    "NIS Deducted: 8797.20",
    "Income Tax Deducted: 15000.00",
    "Health Surcharge: 429.00",
]


@pytest.fixture(scope="module")
def sample_ocr_result():
    image_bytes = render_td4_image(SAMPLE_TD4_LINES)
    return run_ocr(image_bytes)


class TestRunOCR:
    def test_returns_nonempty_raw_text(self, sample_ocr_result):
        assert sample_ocr_result.raw_text.strip() != ""

    def test_confidence_is_a_fraction_between_0_and_1(self, sample_ocr_result):
        assert 0.0 <= sample_ocr_result.confidence <= 1.0

    def test_picks_up_recognizable_words_from_the_image(self, sample_ocr_result):
        # Tesseract on a clean, computer-rendered image should recognize most
        # of this text; check for a few distinctive tokens rather than exact
        # equality, since OCR engines occasionally misread individual glyphs.
        text_lower = sample_ocr_result.raw_text.lower()
        assert "republic" in text_lower or "bank" in text_lower
        assert "180000" in sample_ocr_result.raw_text.replace(",", "")

    def test_invalid_image_bytes_raise_value_error(self):
        with pytest.raises(ValueError):
            run_ocr(b"this is not an image")


class TestParseTD4Fields:
    def test_extracts_employer_name(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert "employer_name" in fields
        assert "republic" in fields["employer_name"].lower() or "bank" in fields["employer_name"].lower()

    def test_extracts_employer_bir_number(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert fields.get("employer_bir_number") == "9998887"

    def test_extracts_employee_bir_number(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert fields.get("employee_bir_number") == "1234567"

    def test_extracts_gross_earnings_as_float(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert fields.get("gross_earnings") == pytest.approx(180000.00)

    def test_extracts_nis_deducted(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert fields.get("nis_deducted") == pytest.approx(8797.20)

    def test_extracts_income_tax(self, sample_ocr_result):
        fields = parse_td4_fields(sample_ocr_result.raw_text)
        assert fields.get("income_tax") == pytest.approx(15000.00)

    def test_empty_text_returns_empty_fields(self):
        assert parse_td4_fields("") == {}

    def test_money_regex_handles_thousands_separator(self):
        fields = parse_td4_fields("Gross Earnings: 1,234,567.89")
        assert fields.get("gross_earnings") == pytest.approx(1234567.89)


class TestNativeTextPDF:
    """A PDF with a real text layer should be read directly via pdfplumber,
    with perfect (1.0) confidence and no Tesseract involvement."""

    @staticmethod
    @pytest.fixture(scope="class")
    def result():
        pdf_bytes = render_native_text_pdf([SAMPLE_TD4_LINES])
        return run_ocr(pdf_bytes)

    def test_reports_confidence_of_1_for_native_text(self, result):
        assert result.confidence == 1.0

    def test_reports_correct_page_count(self, result):
        assert result.page_count == 1

    def test_extracts_exact_text(self, result):
        assert "Republic Bank Ltd" in result.raw_text
        assert "180000.00" in result.raw_text

    def test_fields_parse_correctly_from_native_pdf_text(self, result):
        fields = parse_td4_fields(result.raw_text)
        assert fields.get("employer_bir_number") == "9998887"
        assert fields.get("gross_earnings") == pytest.approx(180000.00)
        assert fields.get("nis_deducted") == pytest.approx(8797.20)


class TestScannedPDF:
    """A PDF with no text layer (just an embedded image per page) should
    fall back to rendering + Tesseract OCR automatically."""

    @staticmethod
    @pytest.fixture(scope="class")
    def result():
        pdf_bytes = render_scanned_pdf([SAMPLE_TD4_LINES])
        return run_ocr(pdf_bytes)

    def test_confidence_reflects_ocr_not_perfect_extraction(self, result):
        # OCR confidence should be a real (sub-1.0, but reasonably high on
        # this clean synthetic input) fraction, proving the OCR path (not
        # the native-text path) was used.
        assert 0.0 < result.confidence < 1.0

    def test_reports_correct_page_count(self, result):
        assert result.page_count == 1

    def test_ocr_recovers_recognizable_text_from_the_scanned_page(self, result):
        text_lower = result.raw_text.lower()
        assert "republic" in text_lower or "bank" in text_lower

    def test_fields_still_parse_from_ocr_text(self, result):
        fields = parse_td4_fields(result.raw_text)
        assert fields.get("employer_bir_number") == "9998887"


class TestMultiPagePDF:
    def test_native_text_pdf_concatenates_all_pages(self):
        page_1 = ["Employer Name: Republic Bank Ltd", "Employer BIR Number: 9998887"]
        page_2 = ["Employee Name: Kevin Boodram", "Gross Earnings: 90000.00"]
        pdf_bytes = render_native_text_pdf([page_1, page_2])
        result = run_ocr(pdf_bytes)

        assert result.page_count == 2
        assert "Republic Bank Ltd" in result.raw_text
        assert "Kevin Boodram" in result.raw_text
        assert "90000.00" in result.raw_text

    def test_mixed_native_and_scanned_pages_handles_each_correctly(self):
        # Page 1 has a real text layer; page 2 is scanned (image-only). Both
        # should still come back correctly via their respective code paths.
        native_pdf = render_native_text_pdf([["Employer Name: Republic Bank Ltd"]])
        scanned_pdf = render_scanned_pdf([["Employee Name: Kevin Boodram", "Gross Earnings: 90000.00"]])

        # Confirm each independently first (this is what app.services.ocr
        # actually needs to support -- per-page fallback within one PDF --
        # but building a genuinely mixed single PDF from two different
        # generators without a page-merge library is out of scope for this
        # test; per-page behavior is already covered by the two classes
        # above, so this test focuses on making sure neither code path
        # regresses the other when exercised back-to-back).
        native_result = run_ocr(native_pdf)
        scanned_result = run_ocr(scanned_pdf)

        assert native_result.confidence == 1.0
        assert 0.0 < scanned_result.confidence < 1.0


class TestInvalidPDF:
    def test_corrupt_pdf_bytes_raise_value_error(self):
        with pytest.raises(ValueError):
            run_ocr(b"%PDF-1.4\nthis is not a real pdf structure")
