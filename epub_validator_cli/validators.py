"""Validation checks for EPUB files targeting Amazon KDP.

Categories: structure, navigation, common errors. Each finding carries a
code, severity, message, file path (inside the zip), and line number when
the source location is known (0 means unknown).
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List

from .models import ParsedEpub
from .parser import _read_text


@dataclass
class Finding:
    code: str
    severity: str  # "error" | "warning" | "info"
    message: str
    file: str
    line: int
    check: str  # "structure" | "navigation" | "common"


def validate(path: str) -> List[Finding]:
    """Run every validation check on ``path`` and return findings."""
    from .parser import parse_epub

    parsed = parse_epub(path)
    findings: List[Finding] = []
    findings.extend(_check_structure(parsed))
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, OSError):
        return findings
    with zf:
        findings.extend(_check_navigation(parsed, zf))
        findings.extend(_check_common(parsed, zf))
    return findings


def _sev(level: str) -> str:
    return level


# ---------------------------------------------------------------------------
# Structure checks
# ---------------------------------------------------------------------------


def _check_structure(parsed: ParsedEpub) -> List[Finding]:
    findings: List[Finding] = []

    if parsed.errors:
        for err in parsed.errors:
            findings.append(
                Finding(
                    code="S001",
                    severity="error",
                    message=err,
                    file=parsed.path,
                    line=0,
                    check="structure",
                )
            )
        return findings

    if parsed.mimetype:
        findings.append(
            Finding(
                code="S002",
                severity="info",
                message=f"mimetype = {parsed.mimetype}",
                file="mimetype",
                line=0,
                check="structure",
            )
        )

    if not parsed.opf_path:
        return findings

    findings.append(
        Finding(
            code="S003",
            severity="info",
            message=f"OPF file: {parsed.opf_path}",
            file=parsed.opf_path,
            line=0,
            check="structure",
        )
    )

    # OPF version
    version = parsed.version
    if version:
        findings.append(
            Finding(
                code="S004",
                severity="info",
                message=f"EPUB version: {version}",
                file=parsed.opf_path,
                line=0,
                check="structure",
            )
        )
        if version not in ("2.0", "3.0"):
            findings.append(
                Finding(
                    code="S005",
                    severity="warning",
                    message=(f"OPF version {version!r} is unusual; KDP accepts EPUB 2.0 and EPUB 3.0."),
                    file=parsed.opf_path,
                    line=0,
                    check="structure",
                )
            )

    # Manifest resources resolve
    namelist = set(parsed.raw_files)
    missing_manifest: List[str] = []
    for mid, item in parsed.manifest.items():
        resolved = item.href
        if parsed.base_dir:
            resolved = parsed.base_dir + resolved.lstrip("/")
        if resolved and resolved not in namelist:
            missing_manifest.append(mid)
    if missing_manifest:
        findings.append(
            Finding(
                code="S006",
                severity="error",
                message=("Manifest resources not found in zip: " + ", ".join(missing_manifest)),
                file=parsed.opf_path,
                line=0,
                check="structure",
            )
        )

    # Spine references resolve to manifest ids
    missing_spine: List[str] = []
    for spine_item in parsed.spine:
        if spine_item.idref not in parsed.manifest:
            missing_spine.append(spine_item.idref)
    if missing_spine:
        findings.append(
            Finding(
                code="S007",
                severity="error",
                message=("Spine items reference missing manifest ids: " + ", ".join(missing_spine)),
                file=parsed.opf_path,
                line=0,
                check="structure",
            )
        )

    # Empty spine
    if not parsed.spine:
        findings.append(
            Finding(
                code="S008",
                severity="error",
                message="Spine is empty; EPUB has no reading order.",
                file=parsed.opf_path,
                line=0,
                check="structure",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Navigation checks
# ---------------------------------------------------------------------------


def _check_navigation(parsed: ParsedEpub, zf: zipfile.ZipFile) -> List[Finding]:
    findings: List[Finding] = []

    has_nav = parsed.nav is not None and len(parsed.nav) > 0
    has_ncx = parsed.ncx is not None and len(parsed.ncx) > 0

    if not has_nav and not has_ncx:
        findings.append(
            Finding(
                code="N001",
                severity="error",
                message=("No table of contents found. Add an EPUB3 <nav> document (toc section) or an EPUB2 NCX toc."),
                file=parsed.opf_path,
                line=0,
                check="navigation",
            )
        )
        return findings

    if has_ncx:
        findings.append(
            Finding(
                code="N002",
                severity="info",
                message=f"NCX toc found with {len(parsed.ncx)} navPoint(s).",
                file=parsed.opf_path,
                line=0,
                check="navigation",
            )
        )
    if has_nav:
        toc_entries = [e for e in (parsed.nav or []) if e.kind == "toc"]
        findings.append(
            Finding(
                code="N003",
                severity="info",
                message=(f"<nav> document found with {len(toc_entries)} toc entry/entries."),
                file=parsed.opf_path,
                line=0,
                check="navigation",
            )
        )

    # Resolve navigation hrefs to existing files
    nav_hrefs: List[tuple] = []
    if parsed.ncx:
        for np in parsed.ncx:
            if np.content_src:
                nav_hrefs.append((np.content_src, np.line))
    if parsed.nav:
        for e in parsed.nav:
            nav_hrefs.append((e.href, e.line))

    broken: List[str] = []
    for href, line in nav_hrefs:
        target = href.split("#", 1)[0]
        if not target:
            continue
        resolved = target
        if parsed.base_dir:
            resolved = parsed.base_dir + target.lstrip("/")
        if resolved not in zf.namelist():
            broken.append(f"{target} (line {line})")
    if broken:
        findings.append(
            Finding(
                code="N004",
                severity="error",
                message=("Navigation links point to missing files: " + "; ".join(broken)),
                file=parsed.opf_path,
                line=0,
                check="navigation",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Common error checks (KDP-specific)
# ---------------------------------------------------------------------------


def _check_common(parsed: ParsedEpub, zf: zipfile.ZipFile) -> List[Finding]:
    findings: List[Finding] = []

    # Title present in OPF metadata
    title_found = False
    title_line = 0
    for err in parsed.errors:
        pass
    # Re-parse OPF raw to inspect <dc:title>
    opf_raw = None
    if parsed.opf_path and parsed.opf_path in zf.namelist():
        try:
            opf_raw = zf.read(parsed.opf_path).decode("utf-8")
        except UnicodeDecodeError:
            opf_raw = None
    if opf_raw:
        title_m = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", opf_raw, re.DOTALL)
        if title_m:
            title_found = True
            title_line = opf_raw.count("\n", 0, title_m.start()) + 1
    if not title_found:
        findings.append(
            Finding(
                code="C001",
                severity="error",
                message=("No <dc:title> found in OPF metadata. KDP requires a book title."),
                file=parsed.opf_path,
                line=title_line,
                check="common",
            )
        )
    else:
        findings.append(
            Finding(
                code="C002",
                severity="info",
                message="dc:title present in OPF metadata.",
                file=parsed.opf_path,
                line=title_line,
                check="common",
            )
        )

    # Cover image present (manifest item with cover-image property or
    # meta name="cover")
    cover_found = False
    cover_line = 0
    cover_href = ""
    for item in parsed.manifest.values():
        if "cover-image" in item.properties.split():
            cover_found = True
            cover_href = item.href
            cover_line = item.line
            break
    if not cover_found and opf_raw:
        cover_m = re.search(
            r'<meta[^>]*name="cover"[^>]*content="([^"]+)"',
            opf_raw,
        )
        if cover_m:
            cover_found = True
            cover_href = cover_m.group(1)
            cover_line = opf_raw.count("\n", 0, cover_m.start()) + 1
    if not cover_found:
        findings.append(
            Finding(
                code="C003",
                severity="warning",
                message=(
                    "No cover image declared (cover-image property or "
                    'meta name="cover"). KDP strongly recommends a cover.'
                ),
                file=parsed.opf_path,
                line=0,
                check="common",
            )
        )
    else:
        findings.append(
            Finding(
                code="C004",
                severity="info",
                message=(f"Cover image declared: {cover_href}"),
                file=parsed.opf_path,
                line=cover_line,
                check="common",
            )
        )

    # No scripts in manifest media types
    for item in parsed.manifest.values():
        mt = (item.media_type or "").lower()
        if "javascript" in mt or "ecmascript" in mt:
            findings.append(
                Finding(
                    code="C005",
                    severity="error",
                    message=(
                        f"Manifest item {item.id!r} uses script media type "
                        f"{item.media_type!r}; KDP does not allow scripts."
                    ),
                    file=parsed.opf_path,
                    line=item.line,
                    check="common",
                )
            )

    # Scan content documents for <script> tags
    script_files: List[tuple] = []
    for item in parsed.manifest.values():
        mt = (item.media_type or "").lower()
        if "xhtml" in mt or "html" in mt:
            target = item.href
            if parsed.base_dir:
                target = parsed.base_dir + target.lstrip("/")
            raw = _read_text(zf, target) if target in zf.namelist() else None
            if raw is not None:
                for m in re.finditer(r"<script\b", raw, re.IGNORECASE):
                    line = raw.count("\n", 0, m.start()) + 1
                    script_files.append((target, line))
    if script_files:
        details = "; ".join(f"{f} (line {ln})" for f, ln in script_files)
        findings.append(
            Finding(
                code="C006",
                severity="error",
                message=(f"<script> tag found in content document(s); KDP does not allow scripts: {details}"),
                file=parsed.opf_path,
                line=0,
                check="common",
            )
        )

    # Check internal links inside XHTML content documents resolve
    broken_links: List[str] = []
    for item in parsed.manifest.values():
        mt = (item.media_type or "").lower()
        if "xhtml" in mt or "html" in mt:
            target = item.href
            if parsed.base_dir:
                target = parsed.base_dir + target.lstrip("/")
            raw = _read_text(zf, target) if target in zf.namelist() else None
            if raw is None:
                continue
            for m in re.finditer(r'href=["\']([^"\']+)["\']', raw):
                href = m.group(1).split("#", 1)[0]
                if not href:
                    continue
                # content doc dir
                cdir = target.rsplit("/", 1)[0] + "/" if "/" in target else ""
                cand = cdir + href.lstrip("/") if cdir else href.lstrip("/")
                if cand not in zf.namelist():
                    line = raw.count("\n", 0, m.start()) + 1
                    broken_links.append(f"{href} in {item.href} (line {line})")
    if broken_links:
        findings.append(
            Finding(
                code="C007",
                severity="warning",
                message=("Internal links in content documents point to missing files: " + "; ".join(broken_links[:8])),
                file=parsed.opf_path,
                line=0,
                check="common",
            )
        )

    # Duplicate ids across content documents (rough)
    seen_ids: Dict[str, str] = {}
    dup_ids: List[str] = []
    for item in parsed.manifest.values():
        mt = (item.media_type or "").lower()
        if "xhtml" in mt or "html" in mt:
            target = item.href
            if parsed.base_dir:
                target = parsed.base_dir + target.lstrip("/")
            raw = _read_text(zf, target) if target in zf.namelist() else None
            if raw is None:
                continue
            for m in re.finditer(r'id=["\']([^"\']+)["\']', raw):
                aid = m.group(1)
                if aid in seen_ids:
                    if aid not in dup_ids:
                        dup_ids.append(aid)
                else:
                    seen_ids[aid] = item.href
    if dup_ids:
        findings.append(
            Finding(
                code="C008",
                severity="warning",
                message=("Duplicate id attribute(s) across content documents: " + ", ".join(dup_ids[:8])),
                file=parsed.opf_path,
                line=0,
                check="common",
            )
        )

    return findings
