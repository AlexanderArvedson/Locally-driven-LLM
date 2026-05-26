from __future__ import annotations

from app.models.task import Task
from app.utils.date_helpers import days_until, is_overdue
from app.utils.validators import normalize_task, normalize_task_payload, validate_task_payload


class TaskService:
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self._tasks = list(tasks or [])

    def load_payloads(self, payloads: list[dict[str, object]]) -> "TaskService":
        tasks: list[Task] = []
        for payload in payloads:
            errors = validate_task_payload(payload)
            if errors:
                continue
            normalized = normalize_task(payload)
            tasks.append(normalized)
        self._tasks = tasks
        return self

    def tasks(self) -> list[Task]:
        return list(self._tasks)

    def sorted_tasks(self) -> list[Task]:
        return sorted(self._tasks, key=lambda task: task.sort_key())

    def open_tasks(self) -> list[Task]:
        return [task for task in self._tasks if task.is_open()]

    def overdue_tasks(self) -> list[Task]:
        return [task for task in self._tasks if is_overdue(task.due_date)]

    def summary(self) -> dict[str, int]:
        open_count = len(self.open_tasks())
        overdue_count = len(self.overdue_tasks())
        soon_count = sum(1 for task in self._tasks if 0 <= days_until(task.due_date) <= 3)
        return {
            "open": open_count,
            "overdue": overdue_count,
            "due_soon": soon_count,
            "total": len(self._tasks),
        }

    def rebuild_from_records(self, payloads: list[dict[str, object]]) -> list[Task]:
        rebuilt: list[Task] = []
        for payload in payloads:
            normalized = normalize_task_payload(payload)
            rebuilt.append(Task(
                task_id=str(normalized["task_id"]),
                title=str(normalized["title"]),
                due_date=str(normalized["due_date"]),
                priority=int(normalized["priority"]),
                status=str(normalized["status"]),
                tags=list(normalized["tags"]),
                owner=str(normalized["owner"]),
            ))
        self._tasks = rebuilt
        return rebuilt