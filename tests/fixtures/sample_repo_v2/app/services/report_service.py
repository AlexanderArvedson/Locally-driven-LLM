from __future__ import annotations

from app.models.report import TaskReport
from app.models.task import Task
from app.utils.date_helpers import format_due_date, is_overdue
from app.utils.formatting import format_report_header, format_task_line, format_totals_line
from app.utils.validators import normalize_task_record


class ReportService:
    def build_report(self, tasks: list[Task], *, title: str = "Task Maintenance Report") -> TaskReport:
        report = TaskReport(title=title, generated_on=format_due_date("2026-05-26"))
        open_count = 0
        overdue_count = 0

        for task in tasks:
            normalized = normalize_task_record(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "due_date": task.due_date,
                    "priority": task.priority,
                    "status": task.status,
                    "tags": task.tags,
                    "owner": task.owner,
                }
            )
            normalized_task = Task(
                task_id=str(normalized["task_id"]),
                title=str(normalized["title"]),
                due_date=str(normalized["due_date"]),
                priority=int(normalized["priority"]),
                status=str(normalized["status"]),
                tags=list(normalized["tags"]),
                owner=str(normalized["owner"]),
            )
            report.add_line(format_task_line(normalized_task))
            if normalized_task.is_open():
                open_count += 1
            if is_overdue(normalized_task.due_date):
                overdue_count += 1

        report.totals = {
            "open": open_count,
            "overdue": overdue_count,
            "all": len(tasks),
        }
        return report

    def render_report(self, report: TaskReport) -> str:
        lines = [format_report_header(report.title, report.generated_on)]
        lines.extend(report.lines)
        lines.append(format_totals_line(report))
        if report.totals.get("all", 0) == 0:
            lines.append("No tasks were supplied.")
        return "\n".join(lines)