"""LLM prompt templates for function description generation."""

from __future__ import annotations

_PROMPT_TEMPLATE = """\
You are analyzing source code for a code intelligence system.

Describe the following {language} function. Respond with a JSON object ONLY — \
no markdown, no explanation, no code fences.

Required fields:
- summary: one or two sentences describing what the function does
- inputs: list of important parameters or inputs
- outputs: what the function returns or produces
- sideEffects: list of external effects (db writes, network calls, mutations, I/O, logging)
- errors: notable exceptions or error cases handled or raised
- dependencies: important internal or external functions, services, or libraries used

Function metadata:
  Language: {language}
  File: {file_path}
  Name: {qualified_name}

Source code:
{source_code}"""
