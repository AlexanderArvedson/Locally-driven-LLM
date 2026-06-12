"""Converts a markdown string to a PDF byte string using markdown + weasyprint."""

from __future__ import annotations

import markdown
from weasyprint import HTML

_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    max-width: 960px;
    margin: 2em auto;
    padding: 0 1.5em;
    color: #24292e;
}
h1, h2, h3 { border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h1 { font-size: 2em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }
code {
    background: #f6f8fa;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 85%;
    font-family: "SFMono-Regular", Consolas, monospace;
}
pre {
    background: #f6f8fa;
    padding: 1em;
    border-radius: 6px;
    overflow-x: auto;
}
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(even) { background: #f6f8fa; }
blockquote {
    border-left: 4px solid #dfe2e5;
    margin: 0;
    padding: 0 1em;
    color: #6a737d;
}
hr { border: none; border-top: 1px solid #eaecef; margin: 1.5em 0; }
"""


def render_pdf(md_text: str) -> bytes:
    """Convert a markdown string to PDF bytes."""
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code"],
    )
    full_html = (
        "<!DOCTYPE html><html><head>"
        f"<meta charset='utf-8'><style>{_CSS}</style>"
        f"</head><body>{html_body}</body></html>"
    )
    return HTML(string=full_html).write_pdf()
