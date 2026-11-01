"""Tests for the EPUB parser."""

from __future__ import annotations

from epub_validator_cli.parser import parse_epub


def test_valid_epub3_parses(valid_epub3):
    parsed = parse_epub(str(valid_epub3))
    assert parsed.errors == [], parsed.errors
    assert parsed.mimetype == "application/epub+zip"
    assert parsed.opf_path == "OEBPS/content.opf"
    assert parsed.version == "3.0"
    assert "chap1" in parsed.manifest
    assert "cover" in parsed.manifest
    assert "nav" in parsed.manifest
    assert any(s.idref == "chap1" for s in parsed.spine)
    assert parsed.nav is not None
    assert len(parsed.nav) >= 1


def test_valid_epub2_parses(valid_epub2):
    parsed = parse_epub(str(valid_epub2))
    assert parsed.errors == [], parsed.errors
    assert parsed.mimetype == "application/epub+zip"
    assert parsed.opf_path == "OEBPS/content.opf"
    assert parsed.version == "2.0"
    assert "ncx" in parsed.manifest
    assert parsed.ncx is not None
    assert len(parsed.ncx) >= 1


def test_broken_zip_reports_error(tmp_path, epub_builder):
    path = epub_builder(broken_zip=True)
    parsed = parse_epub(str(path))
    assert parsed.errors, "expected an error for a non-zip file"


def test_wrong_mimetype_reports_error(tmp_path, epub_builder):
    path = epub_builder(wrong_mimetype=True)
    parsed = parse_epub(str(path))
    assert any("mimetype" in e.lower() for e in parsed.errors), parsed.errors


def test_missing_container_reports_error(tmp_path, epub_builder):
    path = epub_builder(no_container=True)
    parsed = parse_epub(str(path))
    assert any("container" in e.lower() for e in parsed.errors), parsed.errors


def test_mimetype_not_first_reports_error(tmp_path, epub_builder):
    path = epub_builder(no_mimetype_first=True)
    parsed = parse_epub(str(path))
    assert any("first" in e.lower() for e in parsed.errors), parsed.errors


def test_compressed_mimetype_reports_error(tmp_path, epub_builder):
    path = epub_builder(mimetype_compressed=True)
    parsed = parse_epub(str(path))
    assert any("compress" in e.lower() or "stored" in e.lower() for e in parsed.errors), parsed.errors


def test_spine_missing_idref_reports_error(tmp_path, epub_builder):
    path = epub_builder(spine_missing_idref=True)
    parsed = parse_epub(str(path))
    assert parsed.errors or parsed.spine, parsed.errors
    # spine itemref points to a manifest id that does not exist
    missing = [s.idref for s in parsed.spine if s.idref not in parsed.manifest]
    assert missing == ["does-not-exist"]


def test_raw_files_recorded(valid_epub3):
    parsed = parse_epub(str(valid_epub3))
    assert "mimetype" in parsed.raw_files
    assert "OEBPS/content.opf" in parsed.raw_files
