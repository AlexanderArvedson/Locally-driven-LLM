from __future__ import annotations

from copy import deepcopy

from app.models.task import Task
from app.utils.date_helpers import REFERENCE_DATE, format_due_date, parse_due_date


ALLOWED_STATUSES = {"open", "done", "blocked", "archived"}


def validate_task_payload(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for field_name in ("task_id", "title", "due_date"):
        if not payload.get(field_name):
            errors.append(f"missing {field_name}")

    status = str(payload.get("status", "open")).strip().lower()
    if status not in ALLOWED_STATUSES:
        errors.append(f"unsupported status: {status}")

    priority = payload.get("priority", 3)
    try:
        priority_value = int(priority)
    except (TypeError, ValueError):
        errors.append("priority must be an integer")
    else:
        if priority_value < 0:
            errors.append("priority must be non-negative")

    due_date = payload.get("due_date")
    if due_date:
        try:
            parse_due_date(str(due_date))
        except ValueError:
            errors.append("due_date must use YYYY-MM-DD")

    return errors


def normalize_task_payload(payload: dict[str, object]) -> dict[str, object]:
    data = deepcopy(payload)
    data["task_id"] = str(data.get("task_id", "")).strip()
    data["title"] = " ".join(str(data.get("title", "")).split())
    data["due_date"] = format_due_date(str(data.get("due_date", REFERENCE_DATE.isoformat())))
    data["priority"] = int(data.get("priority", 3))
    data["status"] = str(data.get("status", "open")).strip().lower()
    data["tags"] = [str(tag).strip() for tag in data.get("tags", []) if str(tag).strip()]
    data["owner"] = str(data.get("owner", "unassigned")).strip() or "unassigned"
    return data


def normalize_task_record(record: dict[str, object]) -> dict[str, object]:
    normalized = normalize_task_payload(record)
    normalized["title"] = str(normalized["title"]).title()
    return normalized


def normalize_task(record: dict[str, object]) -> Task:
    normalized = normalize_task_payload(record)
    return Task(
        task_id=str(normalized["task_id"]),
        title=str(normalized["title"]),
        due_date=str(normalized["due_date"]),
        priority=int(normalized["priority"]),
        status=str(normalized["status"]),
        tags=list(normalized["tags"]),
        owner=str(normalized["owner"]),
    )