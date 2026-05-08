from dataclasses import dataclass, field
from datetime import date
from typing import Any

@dataclass

class ReportContext:

    report_date: date
    project_id: int | None = None
    author: str = "Daria"
    currency: str = "RUB"
    params: dict[str, Any] = field(default_factory=dict)
