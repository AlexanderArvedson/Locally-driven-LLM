# This module provides tools for generating and applying patches to files using the ndiff format from the difflib library. 
# It includes functions to create an ndiff string that describes the differences between an original and modified version of a file, 
# as well as a function to apply such an ndiff string to reconstruct the modified file and write it to disk.

from pathlib import Path
from difflib import ndiff, restore


# This function takes the original and modified content of a file as strings 
# and returns an ndiff-formatted string that describes the changes needed to transform the original into the modified version.
def generate_ndiff(original: str, modified: str) -> str:
    """Return an ndiff-formatted string describing changes from original -> modified."""
    return "\n".join(ndiff(original.splitlines(), modified.splitlines()))


# This function takes a file path and an ndiff string, applies the changes described in the ndiff to reconstruct the modified content,
def apply_ndiff(path: str, ndiff_str: str) -> None:
    """Apply an ndiff string to reconstruct the modified file and write it to path.

    This uses difflib.restore with which=2 to reconstruct the second sequence (the
    modified content) from an ndiff output.
    """
    lines = list(restore(ndiff_str.splitlines(), 2))
    Path(path).write_text("\n".join(lines), encoding="utf-8")
