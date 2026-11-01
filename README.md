# epub-validate

A local-only Python CLI that validates EPUB files for Amazon KDP upload.
It checks **structure**, **navigation**, and **common errors** and reports
each issue with a **file path and line number** so you can fix it before
uploading.

Built by **Asdale Dynamics, LLC** — beginner-friendly AI education, books,
and practical tools for authors and small businesses. Local-first: no
network access, no API keys, no telemetry.

---

## What it checks

**Structure**
- Valid ZIP container
- `mimetype` is the first entry, stored uncompressed, and contains exactly
  `application/epub+zip`
- `META-INF/container.xml` exists, is valid XML, and declares an OPF file
- OPF file exists, is valid XML, and declares a recognized EPUB version
- Manifest resources and spine itemrefs resolve to real files
- Non-empty reading order (spine)

**Navigation**
- Table of contents present (EPUB3 `<nav>` toc or EPUB2 NCX `navMap`)
- Navigation links resolve to existing files

**Common errors (KDP-specific)**
- `<dc:title>` present in OPF metadata
- Cover image declared (`cover-image` property or `meta name="cover"`)
- No `<script>` tags or script media types (KDP rejects scripts)
- Internal links in content documents resolve
- No duplicate `id` attributes across content documents

Each finding is labeled **error** (fix before upload), **warning**
(review), or **info**, and shows the file and line number where it occurs.

---

## Install

```bash
pip install .
```

This provides the `epub-validate` command (and `python -m
epub_validator_cli`).

Run from source without installing:

```bash
python -m epub_validator_cli path/to/book.epub
```

---

## Usage

Validate a single EPUB:

```bash
epub-validate mybook.epub
```

Exit code is `0` when there are no errors, `1` when errors are found.
Warnings and info do not change the exit code.

Machine-readable JSON output:

```bash
epub-validate --json mybook.epub
```

Show version:

```bash
epub-validate --version
```

---

## Example output

```
EPUB validation report
======================

Total findings: 3
  errors: 1   warnings: 1   info: 4

[OEBPS/content.opf]
  [E] S007  Spine items reference missing manifest ids: chap2   (OEBPS/content.opf:0)
  [i] S002  mimetype = application/epub+zip   (mimetype:0)

[mimetype]
  [W] C003  No cover image declared ...   (OEBPS/content.opf:0)

Legend: E = error (fix before KDP upload), W = warning (review), i = info.
```

Line numbers appear after the colon when the source location is known.

---

## Local-first, no secrets

This tool reads only the EPUB file you point it at. It makes no network
requests, sends nothing anywhere, and requires no API keys or credentials.
There are no secrets, keys, or personal data in this repository.

---

## License

MIT License. Copyright (c) 2026 Asdale Dynamics, LLC. See `LICENSE`.
