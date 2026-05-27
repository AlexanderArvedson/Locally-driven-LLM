from __future__ import annotations

from app.models.report import TaskReport
from app.models.task import Task
from app.utils.date_helpers import due_window_label, format_due_date


def format_task_line(task: Task) -> str:
    label = due_window_label(task.due_date)
    tags = ", ".join(task.tags) if task.tags else "no-tags"
    return (
        f"- {task.task_id} | {task.title} | due {format_due_date(task.due_date)} | "
        f"priority {task.priority} | {label} | {tags}"
    )


def format_report_header(title: str, generated_on: str) -> str:
    return f"{title}\nGenerated on: {generated_on}"


def format_totals_line(report: TaskReport) -> str:
    open_count = report.totals.get("open", 0)
    overdue_count = report.totals.get("overdue", 0)
    return f"Open: {open_count} | Overdue: {overdue_count}"


def format_task_block(task: Task) -> str:
    # This helper is intentionally present even though the main flow does not use it.
    return "\n".join((task.display_name(), task.due_date, task.status))