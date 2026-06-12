"""Markdown renderers for the embedding and description integrity section."""

from __future__ import annotations


def render_embedding_integrity(
    embed_ok: int,
    embed_chunked: int,
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
    chunked_functions: list[dict],
) -> list[str]:
    """Section 3 — embedding and description coverage tables."""
    lines: list[str] = [
        "## Embedding Integrity",
        "",
        "### Code Embedding Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| OK | {embed_ok} |",
        f"| Chunked (mean-pooled) | {embed_chunked} |",
        f"| Timeout | {embed_timeout} |",
        f"| Error | {embed_error} |",
        f"| Skipped | {embed_skipped} |",
        f"| Unchanged (not re-embedded) | {embed_unchanged} |",
        f"| **Failed total** | **{embed_failed}** |",
        "",
        "### Description Coverage",
        "",
        "| Status | Count |",
        "|---|---|",
        f"| OK | {desc_ok} |",
        f"| Invalid JSON response | {desc_invalid} |",
        f"| Timeout | {desc_timeout} |",
        f"| Error | {desc_error} |",
        f"| Skipped | {desc_skipped} |",
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

    if chunked_functions:
        lines += [
            "### Chunked Functions",
            "",
            "> These functions exceeded the embedding context threshold and were embedded via"
            " mean-pooled chunk averaging. Similarity results may be coarser than for single-pass embeddings.",
            "",
            "| Function | File |",
            "|---|---|",
        ]
        for row in chunked_functions:
            lines.append(f"| `{row['name']}` | {row['file']} |")
        lines.append("")

    lines += ["---", ""]
    return lines
