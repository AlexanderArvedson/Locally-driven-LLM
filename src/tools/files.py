# File handling tools for the project. Provides functions to read and write files.
from pathlib import Path


# Reads file content and returns it as a string. Uses UTF-8 encoding.
def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _detect_crlf(path: str) -> bool:
    """Return True if the file contains CRLF line endings."""
    try:
        return b"\r\n" in Path(path).read_bytes()
    except OSError:
        return False


# Writes the given content to a file, preserving the original file's line
# endings to avoid spurious per-line diffs in git. New files default to LF.
def write_file(path: str, content: str) -> None:
    use_crlf = _detect_crlf(path)
    # Normalise to LF first, then re-apply the target ending.
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    if use_crlf:
        content = content.replace("\n", "\r\n")
    Path(path).write_bytes(content.encode("utf-8"))
