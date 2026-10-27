"""Minimal content-stream walker that records where text is drawn.

It tracks only what the checks need: the current transformation matrix, the
text matrix, the text rendering mode, and the number of glyph codes each
text-showing operator draws. Positions are the origin of each text-showing
operation in default user space, which is precise enough to decide whether
text sits inside a rectangle or outside the page, but it does not compute
per-glyph advances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from pypdf.generic import ContentStream, DictionaryObject, IndirectObject

Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
INVISIBLE_MODES = {3, 7}
MAX_FORM_DEPTH = 8


def multiply(m: Matrix, n: Matrix) -> Matrix:
    """Return m x n using the PDF row-vector convention."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + b * c2,
        a * b2 + b * d2,
        c * a2 + d * c2,
        c * b2 + d * d2,
        e * a2 + f * c2 + e2,
        e * b2 + f * d2 + f2,
    )


@dataclass(frozen=True)
class TextRun:
    """One text-showing operation: where it starts, how many glyphs, how drawn."""

    x: float
    y: float
    glyphs: int
    render_mode: int

    @property
    def invisible(self) -> bool:
        return self.render_mode in INVISIBLE_MODES


def _resolve(obj: Any) -> Any:
    while isinstance(obj, IndirectObject):
        obj = obj.get_object()
    return obj


def _glyph_count(raw: Any, two_byte: bool) -> int:
    if isinstance(raw, str):
        data = raw.encode("latin-1", errors="replace")
    elif isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
    else:
        try:
            data = bytes(raw.original_bytes)
        except AttributeError:
            data = str(raw).encode("utf-8", errors="replace")
    return len(data) // 2 if two_byte else len(data)


def _font_is_two_byte(resources: DictionaryObject | None, name: Any) -> bool:
    if resources is None:
        return False
    fonts = _resolve(resources.get("/Font"))
    if not isinstance(fonts, DictionaryObject):
        return False
    font = _resolve(fonts.get(name))
    return isinstance(font, DictionaryObject) and font.get("/Subtype") == "/Type0"


def text_runs(
    contents: Any,
    resources: DictionaryObject | None,
    reader: Any,
    ctm: Matrix = IDENTITY,
    depth: int = 0,
) -> Iterator[TextRun]:
    """Yield every text-showing operation in a content stream and its forms."""
    if contents is None or depth > MAX_FORM_DEPTH:
        return
    stream = ContentStream(contents, reader)
    stack: list[tuple[Matrix, int]] = []
    render_mode = 0
    tm: Matrix = IDENTITY
    tlm: Matrix = IDENTITY
    leading = 0.0
    two_byte = False

    for operands, operator in stream.operations:
        op = operator if isinstance(operator, bytes) else bytes(operator)
        if op == b"q":
            stack.append((ctm, render_mode))
        elif op == b"Q":
            if stack:
                ctm, render_mode = stack.pop()
        elif op == b"cm" and len(operands) == 6:
            ctm = multiply(tuple(float(v) for v in operands), ctm)  # type: ignore[arg-type]
        elif op == b"BT":
            tm = tlm = IDENTITY
        elif op == b"Tr" and operands:
            render_mode = int(operands[0])
        elif op == b"TL" and operands:
            leading = float(operands[0])
        elif op == b"Tf" and operands:
            two_byte = _font_is_two_byte(resources, operands[0])
        elif op == b"Tm" and len(operands) == 6:
            tm = tlm = tuple(float(v) for v in operands)  # type: ignore[assignment]
        elif op in (b"Td", b"TD") and len(operands) == 2:
            tx, ty = float(operands[0]), float(operands[1])
            if op == b"TD":
                leading = -ty
            tm = tlm = multiply((1.0, 0.0, 0.0, 1.0, tx, ty), tlm)
        elif op == b"T*":
            tm = tlm = multiply((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
        elif op in (b"Tj", b"'", b'"', b"TJ"):
            if op in (b"'", b'"'):
                tm = tlm = multiply((1.0, 0.0, 0.0, 1.0, 0.0, -leading), tlm)
            if op == b"TJ":
                items = operands[0] if operands else []
                glyphs = sum(
                    _glyph_count(item, two_byte) for item in items if not isinstance(item, (int, float))
                )
            else:
                glyphs = _glyph_count(operands[-1], two_byte) if operands else 0
            if glyphs:
                x, y = _origin(tm, ctm)
                yield TextRun(x, y, glyphs, render_mode)
        elif op == b"Do" and operands and resources is not None:
            yield from _form_runs(operands[0], resources, reader, ctm, depth)


def _origin(tm: Matrix, ctm: Matrix) -> tuple[float, float]:
    m = multiply(tm, ctm)
    return m[4], m[5]


def _form_runs(
    name: Any, resources: DictionaryObject, reader: Any, ctm: Matrix, depth: int
) -> Iterator[TextRun]:
    xobjects = _resolve(resources.get("/XObject"))
    if not isinstance(xobjects, DictionaryObject):
        return
    xobj = _resolve(xobjects.get(name))
    if xobj is None or xobj.get("/Subtype") != "/Form":
        return
    matrix = xobj.get("/Matrix")
    form_ctm = ctm
    if matrix is not None and len(matrix) == 6:
        form_ctm = multiply(tuple(float(v) for v in matrix), ctm)  # type: ignore[arg-type]
    form_resources = _resolve(xobj.get("/Resources")) or resources
    yield from text_runs(xobj, form_resources, reader, form_ctm, depth + 1)


def page_text_runs(page: Any, reader: Any) -> list[TextRun]:
    """Return all text runs on a page, including text inside form XObjects."""
    resources = _resolve(page.get("/Resources"))
    contents = page.get_contents()
    if not isinstance(resources, DictionaryObject):
        resources = None
    return list(text_runs(contents, resources, reader))
