from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal


TaskType = Literal["passive", "active"]


@dataclass(slots=True)
class Task:
    id: str
    type: TaskType
    payload: Dict[str, Any]
    created_at: float
