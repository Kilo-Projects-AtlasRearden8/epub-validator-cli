"""Tests for the validation checks."""

from __future__ import annotations

from epub_validator_cli.validators import validate


def _codes(findings):
    return [f.code for f in findings]


def _errors(findings):
    return [f for f in findings if f.severity == "error"]


def test_valid_epub3_no_errors(valid_epub3):
    findings = validate(str(valid_epub3))
    errs = _errors(findings)
    assert errs == [], [f.message for f in errs]


def test_valid_epub2_no_errors(valid_epub2):
    findings = validate(str(valid_epub2))
    errs = _errors(findings)
    assert errs == [], [f.message for f in errs]


def test_missing_title_is_error(tmp_path, epub_builder):
    path = epub_builder(missing_title=True)
    findings = validate(str(path))
    assert "C001" in _codes(findings), _codes(findings)
    errs = _errors(findings)
    assert any(f.code == "C001" for f in errs)


def test_missing_cover_is_warning(tmp_path, epub_builder):
    path = epub_builder(cover_missing=True)
    findings = validate(str(path))
    assert "C003" in _codes(findings), _codes(findings)


def test_script_in_content_is_error(tmp_path, epub_builder):
    path = epub_builder(put_script=True)
    findings = validate(str(path))
    assert "C006" in _codes(findings), _codes(findings)
    errs = _errors(findings)
    assert any(f.code == "C006" for f in errs)


def test_broken_nav_link_is_error(tmp_path, epub_builder):
    path = epub_builder(nav_link_broken=True)
    findings = validate(str(path))
    assert "N004" in _codes(findings), _codes(findings)


def test_broken_content_link_is_warning(tmp_path, epub_builder):
    path = epub_builder(content_link_broken=True)
    findings = validate(str(path))
    assert "C007" in _codes(findings), _codes(findings)


def test_duplicate_id_is_warning(tmp_path, epub_builder):
    path = epub_builder(duplicate_id=True)
    findings = validate(str(path))
    assert "C008" in _codes(findings), _codes(findings)


def test_empty_spine_is_error(tmp_path, epub_builder):
    path = epub_builder(empty_spine=True)
    findings = validate(str(path))
    assert "S008" in _codes(findings), _codes(findings)


def test_spine_missing_idref_is_error(tmp_path, epub_builder):
    path = epub_builder(spine_missing_idref=True)
    findings = validate(str(path))
    assert "S007" in _codes(findings), _codes(findings)


def test_findings_have_locations(valid_epub3):
    findings = validate(str(valid_epub3))
    for f in findings:
        assert f.file
        assert f.check in ("structure", "navigation", "common")
        assert f.severity in ("error", "warning", "info")
        assert f.code
