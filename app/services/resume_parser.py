"""Extracts raw text from an uploaded resume file (PDF, DOCX, or TXT)."""

import io

# 10MB comfortably covers any real resume (even an image-heavy PDF) while
# bounding how much a single upload can make pypdf/python-docx parse.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def extract_text(filename: str, content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large ({len(content)} bytes) — max {MAX_UPLOAD_BYTES} bytes.")

    lower_name = filename.lower()

    # The filename extension alone is caller-controlled and easy to spoof
    # (rename anything to resume.pdf) — checking each format's magic bytes
    # before handing the content to pypdf/python-docx means a malformed or
    # mislabeled file fails fast with a clear 400 instead of surfacing as an
    # unhandled parser exception (a generic 500) partway through parsing.
    if lower_name.endswith(".pdf"):
        if not content.startswith(b"%PDF-"):
            raise ValueError("File does not look like a valid PDF.")
        return _extract_pdf(content)
    if lower_name.endswith(".docx"):
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("File does not look like a valid DOCX.")
        return _extract_docx(content)
    if lower_name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    raise ValueError(f"Unsupported resume file type: {filename}")


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(content: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
