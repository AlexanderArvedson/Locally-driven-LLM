from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskReport:
    title: str
    generated_on: str
    lines: list[str] = field(default_factory=list)
    totals: dict[str, int] = field(default_factory=dict)

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    def as_text(self) -> str:
        lines = [f"{self.title} ({self.generated_on})"]
        lines.extend(self.lines)
        if self.totals:
            lines.append("")
            lines.append("Totals")
            for key in sorted(self.totals):
                lines.append(f"- {key}: {self.totals[key]}")
        return "\n".join(lines)