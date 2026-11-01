"""Command-line interface for the EPUB KDP validator."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .report import format_report
from .validators import validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epub-validate",
        description=(
            "Validate an EPUB file for Amazon KDP upload: checks structure, "
            "navigation, and common errors. Local-only processing."
        ),
    )
    parser.add_argument(
        "epub",
        help="Path to the .epub file to validate.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"epub-validate {__version__}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output instead of plain text.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    findings = validate(args.epub)

    if args.json:
        import json

        payload = [
            {
                "code": f.code,
                "severity": f.severity,
                "message": f.message,
                "file": f.file,
                "line": f.line,
                "check": f.check,
            }
            for f in findings
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(findings), end="")

    errors = sum(1 for f in findings if f.severity == "error")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
