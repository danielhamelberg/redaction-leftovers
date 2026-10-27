"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from redaction_leftovers import __version__
from redaction_leftovers.findings import Severity
from redaction_leftovers.scan import Report, ScanError, scan_file

EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redaction-leftovers",
        description=(
            "Check PDFs for content that survives redaction: earlier saved revisions, "
            "unapplied redaction marks, invisible or off-page text, annotations, form "
            "values, attachments, bookmarks and metadata. Reports where and how much, "
            "never the content itself."
        ),
    )
    parser.add_argument("files", nargs="+", metavar="FILE", help="PDF file(s) to check")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument(
        "--fail-on",
        default="medium",
        choices=[s.name.lower() for s in Severity],
        help="lowest severity that makes the exit code 1 (default: medium)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _format(report: Report) -> str:
    lines = [f"{report.path}: {report.pages} page(s), {report.revisions} saved revision(s)"]
    if not report.findings:
        lines.append("  no leftovers found by these checks")
    for f in report.findings:
        where = f" [page {', '.join(map(str, f.pages))}]" if f.pages else ""
        lines.append(f"  {f.severity.name:<6} {f.check}{where}: {f.message}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    threshold = Severity.parse(args.fail_on)
    reports: list[Report] = []
    errors: list[str] = []
    for path in args.files:
        try:
            reports.append(scan_file(path))
        except ScanError as exc:
            errors.append(str(exc))

    if args.json:
        payload = {
            "version": __version__,
            "reports": [r.to_dict() for r in reports],
            "errors": errors,
        }
        print(json.dumps(payload, indent=2))
    else:
        print("\n\n".join(_format(r) for r in reports))
    for message in errors:
        print(f"error: {message}", file=sys.stderr)

    if errors:
        return EXIT_ERROR
    failing = any((r.worst() or 0) >= threshold for r in reports)
    return EXIT_FINDINGS if failing else EXIT_CLEAN


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
