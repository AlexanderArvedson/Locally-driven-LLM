from __future__ import annotations

from app.models.task import Task
from app.services.report_service import ReportService
from app.services.task_service import TaskService
from app.utils.validators import normalize_task_payload, validate_task_payload


def load_seed_payloads() -> list[dict[str, object]]:
    return [
        {"task_id": "T-001", "title": "refresh weekly report", "due_date": "2026-05-24", "priority": 2, "status": "open", "tags": ["ops", "report"], "owner": "anna"},
        {"task_id": "T-002", "title": "normalize task input", "due_date": "2026-05-26", "priority": 3, "status": "blocked", "tags": ["pipeline"], "owner": "ben"},
        {"task_id": "T-003", "title": "archive stale metrics", "due_date": "2026-05-30", "priority": 1, "status": "done", "tags": ["cleanup"], "owner": "cara"},
        {"task_id": "T-004", "title": "review legacy adapter", "due_date": "2026-05-28", "priority": 4, "status": "open", "tags": ["legacy"], "owner": "drew"},
    ]


def run_task_pipeline(raw_tasks: list[dict[str, object]] | None = None, *, limit: int = 5) -> str:
    source = list(raw_tasks) if raw_tasks is not None else load_seed_payloads()
    valid_payloads: list[dict[str, object]] = []
    rejected: list[str] = []

    for index, payload in enumerate(source):
        if not isinstance(payload, dict):
            rejected.append(f"item {index}: not a mapping")
            continue

        errors = validate_task_payload(payload)
        if errors:
            rejected.append(f"item {index}: {'; '.join(errors)}")
            continue

        normalized = normalize_task_payload(payload)
        valid_payloads.append(normalized)

    task_service = TaskService().load_payloads(valid_payloads)
    tasks = task_service.sorted_tasks()

    bounded_tasks: list[Task] = []
    for task in tasks:
        bounded_tasks.append(task)
        if len(bounded_tasks) >= max(limit, 0):
            break

    report_service = ReportService()
    report = report_service.build_report(bounded_tasks)
    rendered = report_service.render_report(report)

    if rejected:
        rendered = rendered + "\n\nRejected payloads:\n" + "\n".join(f"- {item}" for item in rejected)

    if not bounded_tasks and source:
        rendered = rendered + "\n\nPipeline completed with no eligible tasks."

    return rendered