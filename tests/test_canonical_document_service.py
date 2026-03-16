import io

from PIL import Image

from src.services.canonical_document_service import CanonicalDocumentService


def test_pdf_passthrough():
    service = CanonicalDocumentService()
    pdf_bytes = b"%PDF-1.4\nfake\n%%EOF"

    assert service.build_canonical_pdf(pdf_bytes, "application/pdf", "sample.pdf") == pdf_bytes


def test_image_converts_to_pdf():
    service = CanonicalDocumentService()
    image = Image.new("RGB", (32, 32), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    pdf_bytes = service.build_canonical_pdf(buffer.getvalue(), "image/png", "sample.png")

    assert pdf_bytes.startswith(b"%PDF")


def test_text_converts_to_pdf():
    service = CanonicalDocumentService()

    pdf_bytes = service.build_canonical_pdf(b"hello world", "text/plain", "sample.txt")

    assert pdf_bytes.startswith(b"%PDF")
