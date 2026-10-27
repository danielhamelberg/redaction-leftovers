"""Write demo.pdf: a document "redacted" the way many editors do it.

Version 1 has a sentence with a name in it. The editor then saves a second
version that draws a black box and drops the name from the page, but appends
the change as an incremental update, so version 1 is still in the file.

    python examples/make_demo.py demo.pdf
"""

from __future__ import annotations

import io
import sys

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def _page_stream(writer: PdfWriter, ops: str):
    stream = DecodedStreamObject()
    stream.set_data(ops.encode("latin-1"))
    return writer._add_object(stream)


def main(path: str) -> None:
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Contents")] = _page_stream(
        writer, "BT /F1 12 Tf 72 720 Td (The complaint was filed by Jane Example.) Tj ET\n"
    )
    first = io.BytesIO()
    writer.write(first)

    edit = PdfWriter(io.BytesIO(first.getvalue()), incremental=True)
    edit.pages[0][NameObject("/Contents")] = _page_stream(
        edit,
        "BT /F1 12 Tf 72 720 Td (The complaint was filed by) Tj ET\n0 0 0 rg 232 716 80 14 re f\n",
    )
    with open(path, "wb") as handle:
        edit.write(handle)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo.pdf")
