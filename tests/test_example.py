"""The README quickstart: the demo file must produce exactly the documented finding."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

from redaction_leftovers import Severity, scan_file

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "make_demo.py"


def test_demo_file_reports_the_earlier_revision(tmp_path, monkeypatch):
    out = tmp_path / "demo.pdf"
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(out)])
    runpy.run_path(str(EXAMPLE), run_name="__main__")
    report = scan_file(out)
    assert report.revisions == 2
    [finding] = report.findings
    assert finding.check == "earlier-revision"
    assert finding.severity is Severity.HIGH
    assert (finding.count, finding.details["characters"]) == (2, len("JaneExample"))


def test_rewriting_with_qpdf_clears_the_earlier_revision(tmp_path, monkeypatch):
    import pytest

    pikepdf = pytest.importorskip("pikepdf")  # pikepdf bundles qpdf
    demo = tmp_path / "demo.pdf"
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(demo)])
    runpy.run_path(str(EXAMPLE), run_name="__main__")
    rewritten = tmp_path / "rewritten.pdf"
    with pikepdf.open(demo) as pdf:
        pdf.save(rewritten)
    report = scan_file(rewritten)
    assert report.revisions == 1
    assert not [f for f in report.findings if f.check == "earlier-revision"]
