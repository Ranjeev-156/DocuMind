from io import BytesIO
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF."""
    reader = PdfReader(BytesIO(file_bytes))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages)


def extract_text(file_bytes: bytes) -> str:
    """Extract text from TXT or Markdown files."""
    return file_bytes.decode("utf-8", errors="replace")


def extract_csv(file_bytes: bytes) -> str:
    """Extract CSV data as readable text."""
    dataframe = pd.read_csv(BytesIO(file_bytes))

    return dataframe.to_csv(
        index=False
    )


def extract_xlsx(file_bytes: bytes) -> str:
    """Extract Excel workbook data as readable text."""
    workbook = pd.ExcelFile(BytesIO(file_bytes))

    sections = []

    for sheet_name in workbook.sheet_names:
        dataframe = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
        )

        sections.append(
            f"Sheet: {sheet_name}\n"
            f"{dataframe.to_csv(index=False)}"
        )

    return "\n\n".join(sections)


def extract_document(filename: str, file_bytes: bytes) -> str:
    """Extract text based on the document type."""
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        return extract_pdf(file_bytes)

    if extension in {".txt", ".md"}:
        return extract_text(file_bytes)

    if extension == ".csv":
        return extract_csv(file_bytes)

    if extension == ".xlsx":
        return extract_xlsx(file_bytes)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )