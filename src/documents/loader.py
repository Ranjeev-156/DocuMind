from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
}


def is_supported_file(filename: str) -> bool:
    """Check whether a file type is supported."""
    extension = Path(filename).suffix.lower()
    return extension in SUPPORTED_EXTENSIONS


def get_file_type(filename: str) -> str:
    """Return the file extension."""
    return Path(filename).suffix.lower()


def get_file_size_mb(file_bytes: bytes) -> float:
    """Return file size in megabytes."""
    return len(file_bytes) / (1024 * 1024)