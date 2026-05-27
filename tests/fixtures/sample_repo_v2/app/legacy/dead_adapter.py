from __future__ import annotations


def convert_legacy_payload(payload: dict[str, object]) -> dict[str, object]:
    converted = {
        "task_id": str(payload.get("id", "")),
        "title": str(payload.get("name", "")),
        "status": str(payload.get("state", "open")),
    }
    if converted["status"] == "blocked":
        converted["status"] = "open"
    return converted


def summarize_rows(rows: list[dict[str, object]]) -> list[str]:
    output: list[str] = []
    for row in rows:
        output.append(f"{row.get('id', '')}:{row.get('name', '')}")
    return output