"""Individual checks. Each takes an open reader and returns findings."""

from __future__ import annotations

from typing import Any, Callable

from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

from redaction_leftovers.content import TextRun, page_text_runs
from redaction_leftovers.findings import Finding, Severity

Rect = tuple[float, float, float, float]
# Annotation types that carry no author-written text of their own.
_SILENT_ANNOTS = {"/Link", "/Widget", "/Popup", "/Redact"}
# Info keys written by software rather than by the author.
_SOFTWARE_KEYS = {"/Producer", "/Creator", "/CreationDate", "/ModDate", "/Trapped"}


def _resolve(obj: Any) -> Any:
    while isinstance(obj, IndirectObject):
        obj = obj.get_object()
    return obj


def _rect(value: Any) -> Rect | None:
    value = _resolve(value)
    if not isinstance(value, ArrayObject) or len(value) != 4:
        return None
    x0, y0, x1, y1 = (float(v) for v in value)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _inside(run: TextRun, rect: Rect, tolerance: float = 0.5) -> bool:
    x0, y0, x1, y1 = rect
    return x0 - tolerance <= run.x <= x1 + tolerance and y0 - tolerance <= run.y <= y1 + tolerance


def _annotations(page: Any) -> list[DictionaryObject]:
    annots = _resolve(page.get("/Annots"))
    if not isinstance(annots, ArrayObject):
        return []
    result = []
    for annot in annots:
        annot = _resolve(annot)
        if isinstance(annot, DictionaryObject):
            result.append(annot)
    return result


class PageCache:
    """Parse each page's content stream once and share it between checks."""

    def __init__(self, reader: PdfReader) -> None:
        self.reader = reader
        self._runs: dict[int, list[TextRun]] = {}

    def runs(self, index: int) -> list[TextRun]:
        if index not in self._runs:
            try:
                self._runs[index] = page_text_runs(self.reader.pages[index], self.reader)
            except Exception:  # noqa: BLE001 - one damaged page must not hide others
                self._runs[index] = []
        return self._runs[index]


def unapplied_redactions(cache: PageCache) -> list[Finding]:
    """Redaction annotations that were marked but never applied."""
    findings = []
    for index, page in enumerate(cache.reader.pages):
        for annot in _annotations(page):
            if annot.get("/Subtype") != "/Redact":
                continue
            rect = _rect(annot.get("/Rect"))
            glyphs = 0
            if rect is not None:
                glyphs = sum(r.glyphs for r in cache.runs(index) if _inside(r, rect))
            findings.append(
                Finding(
                    check="unapplied-redaction",
                    severity=Severity.HIGH,
                    message=(
                        "A redaction is marked but was never applied; the content "
                        f"under it is still in the file (~{glyphs} characters of text start inside it)."
                    ),
                    pages=(index + 1,),
                    count=glyphs,
                )
            )
    return findings


def invisible_text(cache: PageCache) -> list[Finding]:
    """Text drawn with an invisible rendering mode (3 or 7)."""
    pages, total = [], 0
    for index in range(len(cache.reader.pages)):
        glyphs = sum(r.glyphs for r in cache.runs(index) if r.invisible)
        if glyphs:
            pages.append(index + 1)
            total += glyphs
    if not total:
        return []
    return [
        Finding(
            check="invisible-text",
            severity=Severity.MEDIUM,
            message=(
                f"~{total} characters of text are drawn invisibly. This is normal for the OCR "
                "layer of a scanned page, but if the scan was redacted only in the image, the "
                "OCR text still contains what was blacked out."
            ),
            pages=tuple(pages),
            count=total,
        )
    ]


def text_outside_page(cache: PageCache) -> list[Finding]:
    """Text whose origin lies outside the visible crop box."""
    pages, total = [], 0
    for index, page in enumerate(cache.reader.pages):
        box = page.cropbox
        rect = (float(box.left), float(box.bottom), float(box.right), float(box.top))
        glyphs = sum(r.glyphs for r in cache.runs(index) if not _inside(r, rect, tolerance=1.0))
        if glyphs:
            pages.append(index + 1)
            total += glyphs
    if not total:
        return []
    return [
        Finding(
            check="text-outside-page",
            severity=Severity.MEDIUM,
            message=(
                f"~{total} characters of text start outside the visible page area. Viewers do not "
                "show it, but copy, search and text extraction do."
            ),
            pages=tuple(pages),
            count=total,
        )
    ]


def annotation_text(cache: PageCache) -> list[Finding]:
    """Comments, notes, highlights and other annotations that carry text."""
    pages, total = [], 0
    for index, page in enumerate(cache.reader.pages):
        found = 0
        for annot in _annotations(page):
            if annot.get("/Subtype") in _SILENT_ANNOTS:
                continue
            if str(annot.get("/Contents") or "").strip() or annot.get("/RC"):
                found += 1
        if found:
            pages.append(index + 1)
            total += found
    if not total:
        return []
    return [
        Finding(
            check="annotation-text",
            severity=Severity.MEDIUM,
            message=f"{total} annotation(s) such as comments or notes carry text of their own.",
            pages=tuple(pages),
            count=total,
        )
    ]


def form_values(cache: PageCache) -> list[Finding]:
    """Form fields that hold a value."""
    try:
        fields = cache.reader.get_fields() or {}
    except Exception:  # noqa: BLE001
        fields = {}
    filled = 0
    for value in fields.values():
        v = value.get("/V") if hasattr(value, "get") else None
        if v not in (None, "", "/Off"):
            filled += 1
    if not filled:
        return []
    return [
        Finding(
            check="form-values",
            severity=Severity.MEDIUM,
            message=(
                f"{filled} form field(s) hold a value, which stays in the file even if the field is hidden."
            ),
            count=filled,
        )
    ]


def embedded_files(cache: PageCache) -> list[Finding]:
    """Attached files, at document level or as file-attachment annotations."""
    try:
        names = list(cache.reader.attachments.keys())
    except Exception:  # noqa: BLE001
        names = []
    count = len(names)
    pages = []
    for index, page in enumerate(cache.reader.pages):
        if any(a.get("/Subtype") == "/FileAttachment" for a in _annotations(page)):
            pages.append(index + 1)
            count += sum(1 for a in _annotations(page) if a.get("/Subtype") == "/FileAttachment")
    if not count:
        return []
    return [
        Finding(
            check="embedded-files",
            severity=Severity.MEDIUM,
            message=f"{count} file(s) are attached; attachments are not redacted with the pages.",
            pages=tuple(pages),
            count=count,
        )
    ]


def _outline_size(items: Any) -> int:
    total = 0
    for item in items:
        total += _outline_size(item) if isinstance(item, list) else 1
    return total


def outline(cache: PageCache) -> list[Finding]:
    """Bookmarks, whose titles often repeat headings that were redacted."""
    try:
        count = _outline_size(cache.reader.outline)
    except Exception:  # noqa: BLE001
        count = 0
    if not count:
        return []
    return [
        Finding(
            check="outline",
            severity=Severity.LOW,
            message=f"{count} bookmark(s) exist; check that their titles do not repeat redacted text.",
            count=count,
        )
    ]


def metadata(cache: PageCache) -> list[Finding]:
    """Author-written document metadata and XMP packets."""
    info = cache.reader.metadata or {}
    keys = sorted(k for k, v in info.items() if k not in _SOFTWARE_KEYS and str(v).strip())
    findings = []
    if keys:
        findings.append(
            Finding(
                check="metadata",
                severity=Severity.LOW,
                message="Document properties are filled in: " + ", ".join(k.lstrip("/") for k in keys) + ".",
                count=len(keys),
                details={"keys": [k.lstrip("/") for k in keys]},
            )
        )
    root = _resolve(cache.reader.trailer.get("/Root"))
    if isinstance(root, DictionaryObject) and root.get("/Metadata") is not None:
        findings.append(
            Finding(
                check="xmp-metadata",
                severity=Severity.LOW,
                message=(
                    "An XMP metadata packet is present; it can hold an older title, author or edit history."
                ),
                count=1,
            )
        )
    return findings


CHECKS: dict[str, Callable[[PageCache], list[Finding]]] = {
    "unapplied-redaction": unapplied_redactions,
    "invisible-text": invisible_text,
    "text-outside-page": text_outside_page,
    "annotation-text": annotation_text,
    "form-values": form_values,
    "embedded-files": embedded_files,
    "outline": outline,
    "metadata": metadata,
}
