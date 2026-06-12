"""Tests for the markdown-to-PDF helper."""

from src.pipeline.reporting.pdf import render_pdf


def test_render_pdf_returns_bytes():
    result = render_pdf("# Hello\nworld")
    assert isinstance(result, bytes)


def test_render_pdf_produces_pdf_header():
    result = render_pdf("# Test report\nSome content.")
    assert result[:4] == b"%PDF"


def test_render_pdf_handles_tables():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = render_pdf(md)
    assert result[:4] == b"%PDF"


def test_render_pdf_handles_empty_string():
    result = render_pdf("")
    assert isinstance(result, bytes)
    assert len(result) > 0
