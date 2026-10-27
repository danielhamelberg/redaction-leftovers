"""Finding and severity types shared by all checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    """How likely a finding is to expose content the author meant to remove."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @classmethod
    def parse(cls, value: str) -> Severity:
        try:
            return cls[value.upper()]
        except KeyError as exc:
            choices = ", ".join(s.name.lower() for s in cls)
            raise ValueError(f"unknown severity {value!r}; choose one of {choices}") from exc


@dataclass(frozen=True)
class Finding:
    """One thing in the file that may still carry removed or hidden content.

    Findings describe *where* and *how much*, never the content itself, so a
    report can be shared without re-leaking what it found.
    """

    check: str
    severity: Severity
    message: str
    pages: tuple[int, ...] = ()
    count: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.name.lower()
        data["pages"] = list(self.pages)
        return data
