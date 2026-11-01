# STATUS

epub-validate — Python CLI that validates EPUB files for Amazon KDP upload.

## What was built

A local-only, dependency-free Python CLI (`epub-validate`) that checks an
EPUB file for structural integrity, navigation correctness, and common errors
that Amazon KDP rejects. Every finding is reported with a file path and line
number so it can be fixed before upload.

Project files:

- `LICENSE` — MIT, `Copyright (c) 2026 Asdale Dynamics, LLC`
- `README.md` — usage, checks performed, credits Asdale Dynamics, LLC
- `pyproject.toml` — package metadata, console script `epub-validate`, ruff config
- `epub_validator_cli/__init__.py` — package marker + version
- `epub_validator_cli/models.py` — parsed EPUB data models
- `epub_validator_cli/parser.py` — zip/mimetype/container.xml/OPF/NCX/nav parsing
- `epub_validator_cli/validators.py` — structure, navigation, common-error checks
- `epub_validator_cli/report.py` — line-numbered plain-text report
- `epub_validator_cli/cli.py` — argparse CLI (plain text or `--json`)
- `tests/conftest.py` — minimal valid EPUB3/EPUB2 fixtures + defect builders
- `tests/test_parser.py` — parsing tests
- `tests/test_validators.py` — validation tests
- `tests/test_cli.py` — CLI exit-code and output tests
- `.gitignore` — excludes build artifacts

## What it checks

Structure: valid ZIP; `mimetype` first/uncompressed/`application/epub+zip`;
`META-INF/container.xml` present and valid; OPF present and valid; recognized
EPUB version; manifest and spine references resolve; non-empty spine.

Navigation: table of contents present (EPUB3 `<nav>` toc or EPUB2 NCX);
navigation links resolve to existing files.

Common errors (KDP-specific): `<dc:title>` present; cover image declared;
no `<script>` tags or script media types; internal content-document links
resolve; no duplicate `id` attributes.

Findings are labeled error (fix before upload), warning (review), or info.
Exit code is 0 with no errors, 1 when errors are present.

## How to run

Install:

```bash
pip install .
```

Validate an EPUB:

```bash
epub-validate book.epub
```

JSON output:

```bash
epub-validate --json book.epub
```

Version:

```bash
epub-validate --version
```

Run from source without installing:

```bash
python -m epub_validator_cli book.epub
```

Run the test suite:

```bash
python3 -m pytest
```

## Verification results

- `python3 -m pytest`: **24 passed**
- `ruff check`: **All checks passed**
- `ruff format --check`: **11 files already formatted**
- CLI smoke test on a valid EPUB3: exit 0, 0 errors
- CLI on an EPUB missing `<dc:title>`: exit 1, reports `C001`
- `--json` emits machine-readable findings with `file` and `line`

## Known gaps

- Line numbers for OPF/nav/ncx content are best-effort (0 when the source
  location can't be determined precisely); content-document line numbers are
  accurate.
- EPUB3 `<nav>` reading relies on the `epub:type` attribute and spine
  `toc`; unusual but valid nav layouts may not be detected.
- Only the first `rootfile` declared in `container.xml` is used.
- Does not validate XHTML well-formedness of content documents beyond
  regex scans for `<script>`, `href`, and `id`.
- No media-type/image-dimension deep validation of cover images.
- Local-first by design: no network, no API keys, no telemetry.

## Credits

Built by Asdale Dynamics, LLC. MIT License.
Copyright (c) 2026 Asdale Dynamics, LLC.
