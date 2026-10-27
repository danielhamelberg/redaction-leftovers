from __future__ import annotations

import pytest

from redaction_leftovers import Severity, scan_bytes
from redaction_leftovers.revisions import revision_ends
from redaction_leftovers.scan import ScanError
from tests import pdfs


def checks(data: bytes) -> dict[str, list]:
    result: dict[str, list] = {}
    for f in scan_bytes(data).findings:
        result.setdefault(f.check, []).append(f)
    return result


def test_plain_pdf_has_no_medium_or_high_findings():
    report = scan_bytes(pdfs.plain())
    assert report.pages == 1
    assert report.revisions == 1
    assert all(f.severity < Severity.MEDIUM for f in report.findings)


def test_text_removed_in_incremental_save_is_reported_with_page():
    original = pdfs.plain("Decision regarding " + pdfs.SECRET)
    redacted = pdfs.incremental_edit(
        original, pdfs.text_ops("Decision regarding") + pdfs.black_box(190, 715, 200, 15)
    )
    assert len(revision_ends(redacted)) == 2
    [finding] = checks(redacted)["earlier-revision"]
    assert finding.severity is Severity.HIGH
    assert finding.pages == (1,)
    assert finding.count == 4  # Quixotic, Zebrafish, Account, 991
    assert finding.details == {"revision": 1, "characters": len("QuixoticZebrafishAccount991")}


def test_incremental_save_that_only_adds_text_is_not_reported():
    original = pdfs.plain("Decision")
    added = pdfs.incremental_edit(original, pdfs.text_ops("Decision and more"))
    assert len(revision_ends(added)) == 2
    assert "earlier-revision" not in checks(added)


def test_eof_bytes_inside_a_stream_are_not_a_revision():
    writer = pdfs.build([pdfs.text_ops("x") + "% %%EOF inside content\n"])
    data = pdfs.to_bytes(writer)
    assert len(revision_ends(data)) == 1


def test_unapplied_redaction_counts_text_under_it():
    data = pdfs.with_redact_annotation((60, 710, 400, 735))
    [finding] = checks(data)["unapplied-redaction"]
    assert finding.severity is Severity.HIGH
    assert finding.count == len("Visible words " + pdfs.SECRET)


def test_unapplied_redaction_elsewhere_counts_zero_but_is_still_high():
    data = pdfs.with_redact_annotation((300, 100, 400, 150))
    [finding] = checks(data)["unapplied-redaction"]
    assert finding.severity is Severity.HIGH
    assert finding.count == 0


@pytest.mark.parametrize("mode", [3, 7])
def test_invisible_text_is_reported(mode):
    data = pdfs.to_bytes(pdfs.build([pdfs.text_ops(pdfs.SECRET, mode=mode)]))
    [finding] = checks(data)["invisible-text"]
    assert finding.count == len(pdfs.SECRET)


def test_visible_text_in_other_modes_is_not_invisible():
    data = pdfs.to_bytes(pdfs.build([pdfs.text_ops("fill", mode=0) + pdfs.text_ops("stroke", mode=1)]))
    assert "invisible-text" not in checks(data)


def test_render_mode_is_restored_by_Q():
    ops = "q 3 Tr Q " + pdfs.text_ops("seen").replace(" 0 Tr", "")
    data = pdfs.to_bytes(pdfs.build([ops]))
    assert "invisible-text" not in checks(data)


def test_text_outside_page_is_reported():
    data = pdfs.to_bytes(pdfs.build([pdfs.text_ops(pdfs.SECRET, x=-500, y=720)]))
    [finding] = checks(data)["text-outside-page"]
    assert finding.count == len(pdfs.SECRET)


def test_cm_transform_is_applied_to_positions():
    # Text drawn at (72, 720) but translated far off the page.
    ops = "q 1 0 0 1 2000 0 cm " + pdfs.text_ops(pdfs.SECRET) + "Q\n"
    data = pdfs.to_bytes(pdfs.build([ops]))
    assert "text-outside-page" in checks(data)


def test_annotation_with_text_is_reported():
    [finding] = checks(pdfs.with_text_annotation(pdfs.SECRET))["annotation-text"]
    assert finding.severity is Severity.MEDIUM
    assert finding.pages == (1,)


def test_form_value_is_reported():
    [finding] = checks(pdfs.with_form_value(pdfs.SECRET))["form-values"]
    assert finding.count == 1


def test_attachment_is_reported():
    [finding] = checks(pdfs.with_attachment("notes.txt", b"secret"))["embedded-files"]
    assert finding.count == 1


def test_outline_is_reported_as_low():
    [finding] = checks(pdfs.with_outline(pdfs.SECRET))["outline"]
    assert finding.severity is Severity.LOW


def test_author_metadata_is_reported_but_software_keys_are_not():
    [finding] = checks(pdfs.with_metadata(Author="A. Person", Producer="Some tool"))["metadata"]
    assert finding.details == {"keys": ["Author"]}


def test_not_a_pdf_raises():
    with pytest.raises(ScanError):
        scan_bytes(b"hello")


def test_findings_never_contain_document_text():
    samples = [
        pdfs.incremental_edit(pdfs.plain("Decision " + pdfs.SECRET), pdfs.text_ops("Decision")),
        pdfs.with_redact_annotation((60, 710, 400, 735)),
        pdfs.to_bytes(pdfs.build([pdfs.text_ops(pdfs.SECRET, mode=3)])),
        pdfs.with_text_annotation(pdfs.SECRET),
        pdfs.with_form_value(pdfs.SECRET),
        pdfs.with_outline(pdfs.SECRET),
        pdfs.with_metadata(Title=pdfs.SECRET),
    ]
    for data in samples:
        text = repr([f.to_dict() for f in scan_bytes(data).findings])
        for word in pdfs.SECRET.split():
            assert word not in text


def test_linearized_file_is_one_revision_without_findings(capfd):
    pikepdf = pytest.importorskip("pikepdf")
    import io

    source = pdfs.to_bytes(pdfs.build([pdfs.text_ops(f"Page {i} words{i}") for i in range(4)]))
    out = io.BytesIO()
    with pikepdf.open(io.BytesIO(source)) as pdf:
        pdf.save(out, linearize=True)
    report = scan_bytes(out.getvalue())
    assert report.revisions == 1
    assert not [f for f in report.findings if f.severity >= Severity.MEDIUM]
    assert capfd.readouterr().err == ""


def test_text_in_form_xobject_is_seen():
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = pdfs.build(["/Fm1 Do\n"])
    form = DecodedStreamObject()
    form.set_data(pdfs.text_ops(pdfs.SECRET, mode=3).encode("latin-1"))
    form.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"): pdfs.ArrayObject([pdfs.FloatObject(v) for v in (0, 0, 612, 792)]),
            NameObject("/Resources"): writer.pages[0]["/Resources"],
        }
    )
    writer.pages[0]["/Resources"][NameObject("/XObject")] = DictionaryObject(
        {NameObject("/Fm1"): writer._add_object(form)}
    )
    [finding] = checks(pdfs.to_bytes(writer))["invisible-text"]
    assert finding.count == len(pdfs.SECRET)
