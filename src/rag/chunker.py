import re


DEFAULT_CHUNK_SIZE = 1400
DEFAULT_OVERLAP = 250


def clean_text(text: str) -> str:
    """Clean and normalize extracted document text."""

    if not text:
        return ""

    text = str(text)

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize tabs and repeated spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove spaces around line breaks
    text = re.sub(r" *\n *", "\n", text)

    return text.strip()


def _find_good_break(text: str, start: int, target_end: int) -> int:
    """
    Try to end a chunk at a natural boundary instead of
    cutting through a sentence.
    """

    if target_end >= len(text):
        return len(text)

    search_start = max(start, target_end - 250)

    # Prefer paragraph boundary
    paragraph_break = text.rfind("\n\n", search_start, target_end)

    if paragraph_break > start:
        return paragraph_break

    # Then sentence boundary
    sentence_matches = list(
        re.finditer(
            r"[.!?]\s+",
            text[search_start:target_end],
        )
    )

    if sentence_matches:
        last_match = sentence_matches[-1]
        return search_start + last_match.end()

    # Then line boundary
    line_break = text.rfind("\n", search_start, target_end)

    if line_break > start:
        return line_break

    return target_end


def create_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """
    Create overlapping chunks while trying to preserve
    sentence and paragraph boundaries.
    """

    text = clean_text(text)

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative"
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        target_end = min(
            start + chunk_size,
            text_length,
        )

        end = _find_good_break(
            text,
            start,
            target_end,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = end - overlap

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks