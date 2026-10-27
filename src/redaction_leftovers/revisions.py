"""Detect text that an earlier saved revision of the file still contains.

PDF editors often save changes as an *incremental update*: the new objects are
appended and the original bytes stay in the file. Truncating the file after an
earlier ``%%EOF`` marker gives back that earlier revision, including any text a
later "redaction" removed.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass

from pypdf import PdfReader

_EOF = re.compile(rb"%%EOF[ \t]*(\r\n|\r|\n)?")
_STARTXREF = re.compile(rb"startxref\s+\d+\s*$")
_WORD = re.compile(r"\w+", re.UNICODE)


def revision_ends(data: bytes) -> list[int]:
    """Return the byte offset just past each ``%%EOF`` that closes a revision.

    A marker only counts when a ``startxref`` line precedes it, which filters
    out ``%%EOF`` byte sequences that happen to occur inside binary streams.
    """
    ends = []
    for match in _EOF.finditer(data):
        window = data[max(0, match.start() - 64) : match.start()]
        if _STARTXREF.search(window.rstrip(b"\r\n \t")):
            ends.append(match.end())
    # A linearized ("fast web view") file opens with a first-page section that
    # has its own %%EOF. That section is not a saved revision.
    if len(ends) > 1 and b"/Linearized" in data[:1024]:
        ends = ends[1:]
    return ends


@contextmanager
def _quiet_pypdf():
    """Silence pypdf's repair warnings while reading deliberately truncated files."""
    logger = logging.getLogger("pypdf")
    previous = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        logger.setLevel(previous)


def _words(reader: PdfReader) -> tuple[Counter[str], dict[int, Counter[str]]]:
    total: Counter[str] = Counter()
    per_page: dict[int, Counter[str]] = {}
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - damaged pages must not stop the scan
            text = ""
        words = Counter(w.casefold() for w in _WORD.findall(text))
        per_page[number] = words
        total.update(words)
    return total, per_page


@dataclass(frozen=True)
class RemovedText:
    """Text that revision ``revision`` has and the final file does not."""

    revision: int
    words: int
    characters: int
    pages: tuple[int, ...]


@dataclass(frozen=True)
class RevisionReport:
    revisions: int
    unreadable: tuple[int, ...]
    removed: tuple[RemovedText, ...]


def compare_revisions(data: bytes) -> RevisionReport:
    """Compare every earlier revision's text with the final revision's text."""
    ends = revision_ends(data)
    if len(ends) <= 1:
        return RevisionReport(revisions=max(1, len(ends)), unreadable=(), removed=())

    final_words, _ = _words(PdfReader(io.BytesIO(data), strict=False))
    removed: list[RemovedText] = []
    unreadable: list[int] = []
    for index, end in enumerate(ends[:-1], start=1):
        try:
            with _quiet_pypdf():
                earlier = PdfReader(io.BytesIO(data[:end]), strict=False)
                words, per_page = _words(earlier)
        except Exception:  # noqa: BLE001 - e.g. the first part of a linearized file
            unreadable.append(index)
            continue
        missing = words - final_words
        if not missing:
            continue
        pages = tuple(n for n, page_words in per_page.items() if page_words & missing)
        removed.append(
            RemovedText(
                revision=index,
                words=sum(missing.values()),
                characters=sum(len(w) * c for w, c in missing.items()),
                pages=pages,
            )
        )
    return RevisionReport(revisions=len(ends), unreadable=tuple(unreadable), removed=tuple(removed))
