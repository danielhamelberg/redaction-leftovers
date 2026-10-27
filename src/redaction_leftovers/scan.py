"""Run every check against one PDF."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from redaction_leftovers.checks import CHECKS, PageCache
from redaction_leftovers.findings import Finding, Severity
from redaction_leftovers.revisions import compare_revisions


class ScanError(Exception):
    """The file could not be scanned (not a PDF, damaged, or encrypted)."""


@dataclass
class Report:
    path: str
    pages: int
    revisions: int
    findings: list[Finding] = field(default_factory=list)

    def worst(self) -> Severity | None:
        return max((f.severity for f in self.findings), default=None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "pages": self.pages,
            "revisions": self.revisions,
            "findings": [f.to_dict() for f in self.findings],
        }


def _revision_findings(data: bytes) -> tuple[int, list[Finding]]:
    report = compare_revisions(data)
    findings = [
        Finding(
            check="earlier-revision",
            severity=Severity.HIGH,
            message=(
                f"Saved revision {r.revision} of {report.revisions} still contains {r.words} word(s) "
                f"({r.characters} characters) that the final version does not show. Anyone can "
                "recover that revision by cutting the file at its end marker."
            ),
            pages=r.pages,
            count=r.words,
            details={"revision": r.revision, "characters": r.characters},
        )
        for r in report.removed
    ]
    return report.revisions, findings


def scan_bytes(data: bytes, path: str = "<bytes>") -> Report:
    """Scan PDF bytes and return a report. Raises ScanError if unreadable."""
    if not data.lstrip()[:5].startswith(b"%PDF-"):
        raise ScanError(f"{path}: not a PDF file")
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ScanError(f"{path}: encrypted; decrypt it first (e.g. qpdf --decrypt)")
        pages = len(reader.pages)
    except ScanError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as exc:
        raise ScanError(f"{path}: cannot be read as a PDF ({exc})") from exc

    revisions, findings = _revision_findings(data)
    cache = PageCache(reader)
    for check in CHECKS.values():
        findings.extend(check(cache))
    findings.sort(key=lambda f: (-f.severity, f.check))
    return Report(path=path, pages=pages, revisions=revisions, findings=findings)


def scan_file(path: str | Path) -> Report:
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise ScanError(f"{p}: {exc.strerror or exc}") from exc
    return scan_bytes(data, str(p))
