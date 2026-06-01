"""Context window budget allocation.

ContextBudget enforces per-file character limits, a total file-count cap,
and a total token budget against a ranked file list. The target file is
always included regardless of budget; remaining files are added in rank
order until the first applicable limit is reached.

Token counting uses the centralized ``TokenCounter`` abstraction so no
provider-specific logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.retrieval.budgeting.token_counter import TokenCounter

if TYPE_CHECKING:
    from src.config_loader import ModelConfig


@dataclass
class BudgetAllocation:
    """Result of a budget allocation pass.

    Attributes:
        selected_files: Ordered list of files that fit within all limits.
        chars_used: Total characters accounted for across selected files
            (capped per file at ``max_chars_per_file``).
        files_dropped: Number of candidate files excluded by any limit.
        candidate_files: Total number of files considered (selected + dropped).
        token_budget_used: Estimated tokens consumed by the selected files.
        limit_hit: ``True`` when any limit (file count or token budget) stopped
            iteration before all candidates were processed.
    """

    selected_files: list[str]
    chars_used: int
    files_dropped: int
    candidate_files: int
    token_budget_used: int
    limit_hit: bool


class ContextBudget:
    """Allocates ranked files against char-per-file, file-count, and token limits.

    Limits are advisory for the target file (always included) but hard caps
    for all other candidates. This ensures the primary edit target is always
    available to the LLM regardless of budget pressure.
    """

    def __init__(
        self,
        max_files: int = 15,
        max_chars_per_file: int = 3_000,
        max_total_chars: int = 30_000,
        max_context_tokens: int = 12_000,
        token_counter: Optional[TokenCounter] = None,
        model_config: Optional["ModelConfig"] = None,
    ) -> None:
        self.max_files = max_files
        self.max_chars_per_file = max_chars_per_file
        self.max_total_chars = max_total_chars
        self.max_context_tokens = max_context_tokens
        self._token_counter = token_counter or TokenCounter()
        self._model_config = model_config

    def allocate(
        self,
        ranked_files: list[str],
        target_file: Optional[str] = None,
    ) -> BudgetAllocation:
        """Return the largest prefix of `ranked_files` that fits within all limits.

        Target file is forced to the front and always included even if its
        size would exceed per-file or token limits. All other files are dropped
        when any limit (file count, total chars, or token budget) is reached.

        Iteration stops at the first limit hit; ``limit_hit`` is set when at
        least one non-target candidate was excluded due to a budget constraint.
        """
        # Build ordered candidate list: target first, others in rank order.
        ordered: list[str] = []
        if target_file:
            ordered.append(target_file)
        for f in ranked_files:
            if f != target_file and f not in ordered:
                ordered.append(f)

        candidate_files = len(ordered)
        selected: list[str] = []
        chars_used = 0
        token_budget_used = 0
        files_dropped = 0
        limit_hit = False

        for path in ordered:
            is_target = path == target_file

            # Hard file-count cap applies to non-target files.
            if not is_target and len(selected) >= self.max_files:
                files_dropped += candidate_files - len(selected)
                limit_hit = True
                break

            try:
                raw_text = Path(path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                raw_text = ""

            capped_text = raw_text[:self.max_chars_per_file]
            capped_size = len(capped_text)
            token_count = self._token_counter.count(capped_text, self._model_config)

            # Target file bypasses all budget checks — always included.
            if is_target:
                selected.append(path)
                chars_used += capped_size
                token_budget_used += token_count
                continue

            # Check total character budget.
            if chars_used + capped_size > self.max_total_chars:
                files_dropped += 1
                limit_hit = True
                continue

            # Check token budget.
            if token_budget_used + token_count > self.max_context_tokens:
                files_dropped += 1
                limit_hit = True
                continue

            selected.append(path)
            chars_used += capped_size
            token_budget_used += token_count

        return BudgetAllocation(
            selected_files=selected,
            chars_used=chars_used,
            files_dropped=files_dropped,
            candidate_files=candidate_files,
            token_budget_used=token_budget_used,
            limit_hit=limit_hit,
        )
