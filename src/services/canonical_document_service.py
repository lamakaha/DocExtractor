import io
import os
import textwrap
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


class CanonicalDocumentService:
    """
    Builds a canonical PDF artifact for supported source documents.
    """

    TEXTUAL_MIME_TYPES = {"text/plain", "text/html", "text/csv"}
    IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}

    def build_canonical_pdf(
        self,
        content: bytes,
        mime_type: str,
        filename: str = "",
        extracted_text: Optional[str] = None,
    ) -> bytes:
        if mime_type == "application/pdf":
            return content
        if mime_type in self.IMAGE_MIME_TYPES:
            return self._image_to_pdf(content)
        if mime_type in self.TEXTUAL_MIME_TYPES:
            text = extracted_text or content.decode("utf-8", errors="ignore")
            return self._text_to_pdf(text, title=filename or "document")
        raise ValueError(f"Unsupported canonical PDF source mime type: {mime_type}")

    def canonical_filename(self, filename: str) -> str:
        stem, _ = os.path.splitext(filename)
        safe_stem = stem or "document"
        return f"{safe_stem}.canonical.pdf"

    def _image_to_pdf(self, content: bytes) -> bytes:
        image = Image.open(io.BytesIO(content)).convert("RGB")
        output = io.BytesIO()
        image.save(output, format="PDF")
        return output.getvalue()

    def _text_to_pdf(self, text: str, title: str) -> bytes:
        pages = self._render_text_pages(text or "", title=title)
        output = io.BytesIO()
        first_page, *rest = pages
        first_page.save(output, format="PDF", save_all=True, append_images=rest)
        return output.getvalue()

    def _render_text_pages(self, text: str, title: str) -> list[Image.Image]:
        font = ImageFont.load_default()
        page_width = 1654
        page_height = 2339
        margin = 80
        line_height = 22
        header_gap = 40
        max_chars = 110
        body_top = margin + header_gap + line_height
        max_lines = max(1, (page_height - body_top - margin) // line_height)

        wrapped_lines: list[str] = []
        if title:
            wrapped_lines.extend(textwrap.wrap(title, width=max_chars) or [title])
            wrapped_lines.append("")

        for raw_line in text.splitlines() or [""]:
            wrapped_lines.extend(textwrap.wrap(raw_line, width=max_chars) or [""])

        if not wrapped_lines:
            wrapped_lines = [""]

        pages: list[Image.Image] = []
        for start in range(0, len(wrapped_lines), max_lines):
            page = Image.new("RGB", (page_width, page_height), "white")
            draw = ImageDraw.Draw(page)
            y = margin
            if title:
                draw.text((margin, y), title, fill="black", font=font)
                y = body_top

            for line in wrapped_lines[start : start + max_lines]:
                draw.text((margin, y), line, fill="black", font=font)
                y += line_height
            pages.append(page)

        return pages
