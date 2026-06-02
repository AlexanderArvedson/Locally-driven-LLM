# File handling tools for the project. Provides functions to read and write files.
import os
import tempfile
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


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write data to path atomically using a temp file in the same directory.

    Writes to a sibling temp file first, then os.replace() renames it into
    place. os.replace() is atomic on POSIX when src and dst share a filesystem,
    so a crash mid-write cannot leave a partially written file at path.
    """
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# Writes the given content to a file, preserving the original file's line
# endings to avoid spurious per-line diffs in git. New files default to LF.
def write_file(path: str, content: str) -> None:
    use_crlf = _detect_crlf(path)
    # Normalise to LF first, then re-apply the target ending.
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    if use_crlf:
        content = content.replace("\n", "\r\n")
    atomic_write_bytes(Path(path), content.encode("utf-8"))
