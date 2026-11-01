"""Tests for the CLI entry point."""

from __future__ import annotations

import json

import pytest

from epub_validator_cli.cli import main


def test_valid_epub_exit_zero(valid_epub3, capsys):
    code = main([str(valid_epub3)])
    assert code == 0
    out = capsys.readouterr().out
    assert "No issues found" in out or "Total findings" in out


def test_epub_with_errors_exit_nonzero(tmp_path, epub_builder, capsys):
    path = epub_builder(missing_title=True)
    code = main([str(path)])
    assert code == 1


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])


def test_json_output(valid_epub3, capsys):
    code = main([str(valid_epub3), "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
