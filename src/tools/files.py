# File handling tools for the project. Provides functions to read and write files.
from pathlib import Path

# Reads file content and returns it as a string. Uses UTF-8 encoding.
def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

# Writes the given content to a file at the specified path. Uses UTF-8 encoding.
def write_file(path: str, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")
