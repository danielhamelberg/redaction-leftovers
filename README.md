# redaction-leftovers

A command-line check for PDFs that are about to be published or shared after redaction. It looks
for places where removed or hidden content is still in the file, and reports **where and how much,
never the content itself**, so the report is safe to paste into a ticket.

Its main check is one that the widely used [Free Law Project X-Ray](https://github.com/freelawproject/x-ray)
does not cover ([x-ray#1](https://github.com/freelawproject/x-ray/issues/1), open since 2020): text
that survives in an **earlier saved revision**. Many editors save changes as an incremental update,
which appends the new version and keeps the old bytes. Cutting the file at an earlier `%%EOF` marker
gives the old version back, including whatever the "redaction" removed.

## Quickstart

Requires Python 3.9 or newer. Not published to PyPI; install from a clone:

```console
$ git clone https://github.com/danielhamelberg/redaction-leftovers
$ cd redaction-leftovers
$ python -m pip install .
$ python examples/make_demo.py demo.pdf
$ redaction-leftovers demo.pdf
demo.pdf: 1 page(s), 2 saved revision(s)
  HIGH   earlier-revision [page 1]: Saved revision 1 of 2 still contains 2 word(s) (11 characters) that the final version does not show. Anyone can recover that revision by cutting the file at its end marker.
$ echo $?
1
```

`demo.pdf` is a page whose name was removed and covered with a black box in a second, incrementally
saved version. The page now reads "The complaint was filed by"; the name is still in revision 1.
CI runs the last three commands on every push and checks the exit code.

Use `--json` for a machine-readable report and `--fail-on low|medium|high` to choose which findings
make the exit code non-zero.

## What it checks

| Check | Severity | What it means |
| --- | --- | --- |
| `earlier-revision` | high | An earlier saved revision contains words the final version does not. |
| `unapplied-redaction` | high | A redaction annotation was marked but never applied, so the content under it is intact. |
| `invisible-text` | medium | Text drawn with an invisible render mode (3 or 7). Normal for a scan's OCR layer, but that layer keeps text that was blacked out only in the image. |
| `text-outside-page` | medium | Text that starts outside the visible crop box. |
| `annotation-text` | medium | Comments, notes and other annotations that carry text. |
| `form-values` | medium | Form fields that hold a value. |
| `embedded-files` | medium | Attached files. |
| `outline` | low | Bookmarks, whose titles can repeat redacted headings ([x-ray#2](https://github.com/freelawproject/x-ray/issues/2)). |
| `metadata`, `xmp-metadata` | low | Author-written document properties, and an XMP packet. |

Exit codes: `0` nothing at or above `--fail-on` (default `medium`), `1` findings at or above it,
`2` a file could not be read (not a PDF, damaged, or encrypted with a password).

Each check has tests that build a PDF exhibiting the problem and assert the finding, its count and
its pages, plus a test that no report contains any of the document's words. See [`tests/`](tests).

## What it does not check

- **Text covered by a drawn rectangle or highlight in the current version.** That is X-Ray's job;
  run both. [before-you-send](https://github.com/Waiga/before-you-send) also covers it.
- **Anything inside images.** Text in a scanned image is not read.
- **Removed images or drawings in earlier revisions.** The revision check compares words only.
- Positions are the start of each text-showing operation, not each glyph, so a run that starts just
  outside a rectangle and continues into it is not counted for that rectangle. Character counts for
  two-byte (Type0) fonts are approximate.

A clean result means these checks found nothing. It is not proof that a document is safe to publish.
For most findings the fix is to redact with a tool that removes content, then write a full new copy
of the file instead of an incremental update, and run this check again. `qpdf in.pdf out.pdf` writes
such a copy; a test confirms that it clears the `earlier-revision` finding on the demo file.

## Why another tool

See [docs/RESEARCH.md](docs/RESEARCH.md) for the problem search that led to this project, the
shortlist of candidates, how they were scored, and how this tool relates to existing ones.

## License

Apache-2.0. See [LICENSE](LICENSE).
