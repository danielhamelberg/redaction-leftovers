# Contributing

Bug reports and pull requests are welcome.

## Reporting a missed leftover or a false alarm

Please **do not attach a real redacted document**. Describe the structure instead (which editor
produced it, which check fired or should have fired) or, better, add a test fixture built in code in
[`tests/pdfs.py`](tests/pdfs.py) that reproduces it with made-up text.

## Development

```console
python -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check . && ruff format --check .
```

Ground rules:

- A new check needs a test that builds a PDF showing the problem and one showing a near miss that
  must not fire.
- Reports describe location and size only. A change that makes the tool print document text,
  metadata values or form values will not be merged; `tests/test_checks.py` enforces this.
- Keep the runtime dependency list to `pypdf`.
- README claims must be backed by a test or by the CI quickstart.
