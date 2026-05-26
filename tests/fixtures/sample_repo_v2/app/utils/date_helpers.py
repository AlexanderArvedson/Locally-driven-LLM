from __future__ import annotations

from datetime import date, datetime


REFERENCE_DATE = date(2026, 5, 26)


def parse_due_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_due_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return parse_due_date(value).isoformat()


def is_overdue(due_date: str, today: date | None = None) -> bool:
    reference = today or REFERENCE_DATE
    return parse_due_date(due_date) < reference


def days_until(due_date: str, today: date | None = None) -> int:
    reference = today or REFERENCE_DATE
    return (parse_due_date(due_date) - reference).days


def due_window_label(due_date: str, today: date | None = None) -> str:
    remaining = days_until(due_date, today=today)
    if remaining < 0:
        return "overdue"
    if remaining == 0:
        return "due today"
    if remaining <= 3:
        return "due soon"
    return "planned"