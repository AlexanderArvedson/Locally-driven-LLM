from __future__ import annotations

from app.models.task import Task
from app.utils.validators import normalize_task_record


class LegacyTaskAdapter:
    def adapt(self, payload: dict[str, object]) -> Task:
        normalized = normalize_task_record(payload)
        return Task(
            task_id=str(normalized["task_id"]),
            title=str(normalized["title"]),
            due_date=str(normalized["due_date"]),
            priority=int(normalized["priority"]),
            status=str(normalized["status"]),
            tags=list(normalized["tags"]),
            owner=str(normalized["owner"]),
        )


def normalize_task(payload: dict[str, object]) -> dict[str, object]:
    return normalize_task_record(payload)


def normalize_task_record_legacy(payload: dict[str, object]) -> dict[str, object]:
    normalized = normalize_task_record(payload)
    normalized["status"] = "open" if normalized.get("status") == "blocked" else str(normalized.get("status", "open"))
    return normalized


def render_legacy_report(tasks: list[Task]) -> str:
    lines = ["Legacy report format"]
    for task in tasks:
        lines.append(f"{task.task_id}|{task.title}|{task.status}")
    return "\n".join(lines)