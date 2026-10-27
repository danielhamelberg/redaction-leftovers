"""Build small PDFs for tests, so every fixture is reproducible from code."""

from __future__ import annotations

import io

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    TextStringObject,
)

SECRET = "Quixotic Zebrafish Account 991"


def _font() -> DictionaryObject:
    return DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )


def text_ops(text: str, x: float = 72, y: float = 720, mode: int = 0) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 12 Tf {mode} Tr {x} {y} Td ({escaped}) Tj ET\n"


def _set_contents(writer: PdfWriter, page, ops: str) -> None:
    stream = DecodedStreamObject()
    stream.set_data(ops.encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)


def build(pages: list[str], width: float = 612, height: float = 792) -> PdfWriter:
    """Return a writer whose pages draw the given raw content-stream operators."""
    writer = PdfWriter()
    for ops in pages:
        page = writer.add_blank_page(width=width, height=height)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): _font()})}
        )
        _set_contents(writer, page, ops)
    return writer


def to_bytes(writer: PdfWriter) -> bytes:
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def plain(text: str = "Public summary of the decision") -> bytes:
    return to_bytes(build([text_ops(text)]))


def incremental_edit(original: bytes, new_ops: str) -> bytes:
    """Append a revision that replaces page 1's content, like an editor's 'Save'."""
    writer = PdfWriter(io.BytesIO(original), incremental=True)
    _set_contents(writer, writer.pages[0], new_ops)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def black_box(x: float, y: float, w: float, h: float) -> str:
    return f"0 0 0 rg {x} {y} {w} {h} re f\n"


def with_redact_annotation(rect: tuple[float, float, float, float]) -> bytes:
    writer = build([text_ops("Visible words " + SECRET, x=72, y=720)])
    annot = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Redact"),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in rect]),
        }
    )
    writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(annot)])
    return to_bytes(writer)


def with_text_annotation(note: str) -> bytes:
    from pypdf.annotations import Text

    writer = build([text_ops("Body")])
    writer.add_annotation(0, Text(text=note, rect=(50, 550, 200, 650)))
    return to_bytes(writer)


def with_metadata(**fields: str) -> bytes:
    writer = build([text_ops("Body")])
    writer.add_metadata({f"/{k}": TextStringObject(v) for k, v in fields.items()})
    return to_bytes(writer)


def with_attachment(name: str, data: bytes) -> bytes:
    writer = build([text_ops("Body")])
    writer.add_attachment(name, data)
    return to_bytes(writer)


def with_outline(title: str) -> bytes:
    writer = build([text_ops("Body")])
    writer.add_outline_item(title, 0)
    return to_bytes(writer)


def with_form_value(value: str) -> bytes:
    from pypdf.generic import NumberObject

    writer = build([text_ops("Body")])
    field = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Tx"),
            NameObject("/T"): TextStringObject("field1"),
            NameObject("/V"): TextStringObject(value),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (72, 600, 300, 620)]),
            NameObject("/F"): NumberObject(2),
        }
    )
    ref = writer._add_object(field)
    writer.pages[0][NameObject("/Annots")] = ArrayObject([ref])
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject(
        {NameObject("/Fields"): ArrayObject([ref])}
    )
    return to_bytes(writer)
