"""Markdown renderers for the embedding and description integrity section."""

from __future__ import annotations


def render_embedding_integrity(
    embed_ok: int,
    embed_overflow: int,
    embed_timeout: int,
    embed_error: int,
    embed_skipped: int,
    embed_unchanged: int,
    embed_failed: int,
    desc_ok: int,
    desc_invalid: int,
    desc_timeout: int,
    desc_error: int,
    desc_skipped: int,
    embed_failures: list[dict],
) -> list[str]:
    """Section 3 — embedding and description coverage tables."""
    lines: list[str] = [
        "## Embedding Integrity",
        "",
        "### Code Embedding Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {embed_ok} |",
        f"| context_overflow | {embed_overflow} |",
        f"| timeout | {embed_timeout} |",
        f"| error | {embed_error} |",
        f"| skipped | {embed_skipped} |",
        f"| unchanged (null) | {embed_unchanged} |",
        f"| **failed total** | **{embed_failed}** |",
        "",
        "### Description Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| ok | {desc_ok} |",
        f"| invalid_json | {desc_invalid} |",
        f"| timeout | {desc_timeout} |",
        f"| error | {desc_error} |",
        f"| skipped | {desc_skipped} |",
        "",
    ]

    if embed_failures:
        lines += [
            "### Embedding Failure Table",
            "",
            "| Function | File | Stage | Error Type |",
            "|---|---|---|---|",
        ]
        _CODE_ERROR_MAP = {
            "context_overflow": ("embed", "context_limit"),
            "timeout": ("embed", "timeout"),
            "error": ("embed", "model_error"),
        }
        _DESC_ERROR_MAP = {
            "timeout": ("embed(desc)", "timeout"),
            "invalid_json": ("embed(desc)", "serialization_error"),
            "error": ("embed(desc)", "model_error"),
        }
        for row in embed_failures:
            code_s = row.get("code_status") or ""
            desc_s = row.get("desc_status") or ""
            if code_s in _CODE_ERROR_MAP:
                stage, etype = _CODE_ERROR_MAP[code_s]
                lines.append(f"| `{row['name']}` | {row['file']} | {stage} | {etype} |")
            if desc_s in _DESC_ERROR_MAP:
                stage, etype = _DESC_ERROR_MAP[desc_s]
                lines.append(f"| `{row['name']}` | {row['file']} | {stage} | {etype} |")
        lines.append("")
    else:
        lines += ["_No embedding failures detected._", ""]

    lines += ["---", ""]
    return lines
