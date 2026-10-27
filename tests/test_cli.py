from __future__ import annotations

import json

from redaction_leftovers.cli import EXIT_CLEAN, EXIT_ERROR, EXIT_FINDINGS, main
from tests import pdfs


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_clean_file_exits_zero(tmp_path, capsys):
    path = write(tmp_path, "clean.pdf", pdfs.plain())
    assert main([path]) == EXIT_CLEAN
    assert "no leftovers found" in capsys.readouterr().out


def test_low_findings_pass_by_default_but_fail_with_fail_on_low(tmp_path):
    path = write(tmp_path, "meta.pdf", pdfs.with_metadata(Author="Someone"))
    assert main([path]) == EXIT_CLEAN
    assert main([path, "--fail-on", "low"]) == EXIT_FINDINGS


def test_high_finding_exits_one_and_json_is_valid(tmp_path, capsys):
    path = write(tmp_path, "r.pdf", pdfs.with_redact_annotation((60, 710, 400, 735)))
    assert main([path, "--json"]) == EXIT_FINDINGS
    payload = json.loads(capsys.readouterr().out)
    [report] = payload["reports"]
    assert report["findings"][0]["check"] == "unapplied-redaction"
    assert report["findings"][0]["severity"] == "high"
    assert payload["errors"] == []


def test_fail_on_high_ignores_medium(tmp_path):
    path = write(tmp_path, "i.pdf", pdfs.to_bytes(pdfs.build([pdfs.text_ops("ocr", mode=3)])))
    assert main([path]) == EXIT_FINDINGS
    assert main([path, "--fail-on", "high"]) == EXIT_CLEAN


def test_unreadable_file_exits_two(tmp_path, capsys):
    path = write(tmp_path, "x.pdf", b"not a pdf")
    missing = str(tmp_path / "missing.pdf")
    assert main([path, missing]) == EXIT_ERROR
    err = capsys.readouterr().err
    assert "not a PDF" in err
    assert "missing.pdf" in err


def test_text_output_does_not_print_document_text(tmp_path, capsys):
    path = write(
        tmp_path,
        "s.pdf",
        pdfs.incremental_edit(pdfs.plain("Decision " + pdfs.SECRET), pdfs.text_ops("Decision")),
    )
    assert main([path, "--fail-on", "low"]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "earlier-revision" in out
    for word in pdfs.SECRET.split():
        assert word not in out
