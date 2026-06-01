# This module provides tools for generating and applying patches to files using the ndiff format from the difflib library. 
# It includes functions to create an ndiff string that describes the differences between an original and modified version of a file, 
# as well as a function to apply such an ndiff string to reconstruct the modified file and write it to disk.

from pathlib import Path
from difflib import ndiff, restore, unified_diff
import re


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


# generates a unified diff string that describes the changes from the original to the modified content.
def generate_unified(original: str, modified: str, fromfile: str = "a", tofile: str = "b") -> str:
    """Return a unified diff string describing changes from original -> modified."""
    # Use keepends to preserve newline characters for unified diff clarity
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    ud = unified_diff(orig_lines, mod_lines, fromfile=fromfile, tofile=tofile, lineterm="")
    return "\n".join(list(ud))


# This function takes a file path and a unified diff string, 
# applies the changes described in the unified diff to reconstruct the modified content,
def apply_unified(path: str, unified_str: str) -> None:
    """Apply a unified diff to the file at `path`.

    This is a lightweight unified diff applier that supports typical hunks
    produced by difflib.unified_diff. It does not support every edge case of
    the unified diff format but is sufficient for simple single-file patches.
    """
    if not unified_str.strip():
        return

    orig = Path(path).read_text(encoding="utf-8")
    orig_lines = orig.splitlines(keepends=False)

    out_lines: list[str] = []
    idx = 0
    lines = unified_str.splitlines()

    hunk_re = re.compile(r"^@@ -(?P<a>\d+)(?:,(?P<ac>\d+))? \+(?P<b>\d+)(?:,(?P<bc>\d+))? @@")

    i = 0
    while i < len(lines):
        line = lines[i]
        # skip file header lines
        if line.startswith("---") or line.startswith("+++"):
            i += 1
            continue

        m = hunk_re.match(line)
        if not m:
            i += 1
            continue

        a = int(m.group("a"))
        # b = int(m.group("b"))
        # bc = int(m.group("bc") or "1")

        # copy any untouched lines before this hunk (a is 1-based)
        while idx < a - 1 and idx < len(orig_lines):
            out_lines.append(orig_lines[idx])
            idx += 1

        i += 1
        # process hunk lines
        while i < len(lines) and not lines[i].startswith("@@"):
            h = lines[i]
            if not h:
                # empty line in diff represents an unchanged empty line
                out_lines.append("")
            elif h.startswith(" "):
                # context line: consume from original
                if idx < len(orig_lines):
                    out_lines.append(orig_lines[idx])
                idx += 1
            elif h.startswith("-"):
                # deletion: consume original but do not append
                idx += 1
            elif h.startswith("+"):
                # addition: append the content (without leading +)
                out_lines.append(h[1:])
            else:
                # unknown line, ignore
                pass

            i += 1

    # append any remaining original lines
    while idx < len(orig_lines):
        out_lines.append(orig_lines[idx])
        idx += 1

    # Preserve the original file's trailing-newline behaviour.
    trailing = "\n" if orig.endswith("\n") else ""
    Path(path).write_text("\n".join(out_lines) + trailing, encoding="utf-8")
