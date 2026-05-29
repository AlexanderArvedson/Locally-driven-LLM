"""Context window budget allocation.

ContextBudget enforces per-file and total character limits against a ranked
file list. The target file is always included regardless of budget; remaining
files are added in rank order until the file cap or char budget is exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BudgetAllocation:
    """Result of a budget allocation pass."""

    selected_files: list[str]
    chars_used: int
    files_dropped: int


class ContextBudget:
    """Allocates ranked files against char and file-count limits.

    Limits are advisory for the target file (always included) but hard caps
    for all other candidates. This ensures the primary edit target is always
    available to the LLM regardless of budget pressure.
    """

    def __init__(
        self,
        max_files: int = 15,
        max_chars_per_file: int = 3_000,
        max_total_chars: int = 30_000,
    ) -> None:
        self.max_files = max_files
        self.max_chars_per_file = max_chars_per_file
        self.max_total_chars = max_total_chars

    def allocate(
        self,
        ranked_files: list[str],
        target_file: Optional[str] = None,
    ) -> BudgetAllocation:
        """Return the largest prefix of `ranked_files` that fits the budget.

        Target file is forced to the front and always included even if its
        size would exceed `max_chars_per_file`. All other files are dropped
        when the total char budget or file-count cap is reached.
        """
        # Build ordered candidate list: target first, others in rank order.
        ordered: list[str] = []
        if target_file:
            ordered.append(target_file)
        for f in ranked_files:
            if f != target_file and f not in ordered:
                ordered.append(f)

        selected: list[str] = []
        chars_used = 0
        files_dropped = 0

        for path in ordered:
            if len(selected) >= self.max_files:
                files_dropped += len(ordered) - len(selected)
                break

            try:
                file_size = Path(path).stat().st_size
            except OSError:
                file_size = 0

            capped_size = min(file_size, self.max_chars_per_file)

            # Always include target file even if it blows the budget.
            if path == target_file:
                selected.append(path)
                chars_used += capped_size
                continue

            if chars_used + capped_size > self.max_total_chars:
                files_dropped += 1
                continue

            selected.append(path)
            chars_used += capped_size

        return BudgetAllocation(
            selected_files=selected,
            chars_used=chars_used,
            files_dropped=files_dropped,
        )
