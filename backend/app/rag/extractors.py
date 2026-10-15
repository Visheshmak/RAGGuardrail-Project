import io
import re
from typing import List, Tuple, Optional
from pypdf import PdfReader
from docx import Document as DocxDocument

class TextExtractionError(Exception):
    pass

class DocumentExtractor:
    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace, remove null characters, and clean artifact characters."""
        if not text:
            return ""
        # Remove null bytes
        text = text.replace("\x00", "")
        # Replace multiple spaces/tabs with single space, but preserve paragraph breaks
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize excessive newlines (more than 2 to 2)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def extract_from_pdf(cls, file_bytes: bytes) -> List[Tuple[str, int]]:
        """Extract text from PDF pages, returning a list of (page_text, page_number) tuples (1-indexed)."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for idx, page in enumerate(reader.pages):
                raw_text = page.extract_text() or ""
                cleaned = cls.clean_text(raw_text)
                if cleaned:
                    pages.append((cleaned, idx + 1))
            return pages
        except Exception as e:
            raise TextExtractionError(f"Failed to parse PDF document: {str(e)}") from e

    @classmethod
    def extract_from_docx(cls, file_bytes: bytes) -> List[Tuple[str, Optional[int]]]:
        """Extract text paragraphs from DOCX document."""
        try:
            doc = DocxDocument(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)
            cleaned = cls.clean_text(full_text)
            return [(cleaned, 1)] if cleaned else []
        except Exception as e:
            raise TextExtractionError(f"Failed to parse DOCX document: {str(e)}") from e

    @classmethod
    def extract_from_text(cls, file_bytes: bytes) -> List[Tuple[str, Optional[int]]]:
        """Extract text from TXT or Markdown file, attempting UTF-8 with fallback decoding."""
        try:
            try:
                raw_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw_text = file_bytes.decode("latin-1")
            cleaned = cls.clean_text(raw_text)
            return [(cleaned, 1)] if cleaned else []
        except Exception as e:
            raise TextExtractionError(f"Failed to read text document: {str(e)}") from e

    @classmethod
    def extract(cls, file_bytes: bytes, file_type: str) -> List[Tuple[str, Optional[int]]]:
        """Dispatch extraction based on file extension / type."""
        ext = file_type.lower().strip(".")
        if ext == "pdf":
            return cls.extract_from_pdf(file_bytes)
        elif ext in ("docx", "doc"):
            return cls.extract_from_docx(file_bytes)
        elif ext in ("txt", "md", "markdown", "text"):
            return cls.extract_from_text(file_bytes)
        else:
            raise TextExtractionError(f"Unsupported file format: .{file_type}")
