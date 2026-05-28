"""Centralized configuration values for the project.

Read configuration from environment variables with sensible defaults so
hardcoded values are avoided throughout the codebase.
"""

from __future__ import annotations

import os
from typing import Final


# Ollama API base URL. Supports both OLLAMA_BASE_URL and legacy OLLAMA_HOST.
OLLAMA_BASE_URL: Final[str] = (
    os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
)

# Default model used by coder nodes; can be overridden with OLLAMA_MODEL.
CODER_MODEL: Final[str] = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# How many iterations the workflow should allow before bailing out.
MAX_ITERATIONS = 3
