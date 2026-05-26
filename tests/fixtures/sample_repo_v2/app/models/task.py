from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Task:
    task_id: str
    title: str
    due_date: str
    priority: int = 3
    status: str = "open"
    tags: list[str] = field(default_factory=list)
    owner: str = "unassigned"

    def is_open(self) -> bool:
        return self.status in {"open", "blocked"}

    def sort_key(self) -> tuple[int, str]:
        return (-self.priority, self.title.lower())

    def display_name(self) -> str:
        return f"{self.task_id}: {self.title}".strip()