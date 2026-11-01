"""Human-readable report formatting for validation findings."""

from __future__ import annotations

from typing import List, Optional

from .validators import Finding

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def format_report(findings: List[Finding]) -> str:
    """Return a formatted, line-numbered report string."""
    if not findings:
        return "No issues found. EPUB looks valid for KDP upload.\n"

    # Sort: severity (error, warning, info), then file, then line.
    ordered = sorted(
        findings,
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 99),
            f.file,
            f.line,
            f.code,
        ),
    )

    lines: List[str] = []
    lines.append("EPUB validation report")
    lines.append("=" * 22)
    lines.append("")
    lines.append(f"Total findings: {len(findings)}")
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")
    lines.append(f"  errors: {errors}   warnings: {warnings}   info: {infos}")
    lines.append("")

    current_file: Optional[str] = None
    for f in ordered:
        marker = {
            "error": "E",
            "warning": "W",
            "info": "i",
        }.get(f.severity, "?")
        loc = f"{f.file}:{f.line}" if f.line else f.file
        if current_file != f.file:
            current_file = f.file
            lines.append(f"[{current_file}]")
        lines.append(f"  [{marker}] {f.code}  {f.message}   ({loc})")

    lines.append("")
    lines.append("Legend: E = error (fix before KDP upload), W = warning (review), i = info.")
    return "\n".join(lines) + "\n"
