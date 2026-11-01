"""EPUB parsing: zip container, mimetype, container.xml, OPF, NCX, nav."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Optional, Tuple
from xml.etree.ElementTree import ParseError as XmlParseError

from .models import (
    ManifestItem,
    NavEntry,
    NavPoint,
    ParsedEpub,
    SpineItem,
)

MIMETYPE_NAME = "mimetype"
EXPECTED_MIMETYPE = "application/epub+zip"
CONTAINER_PATH = "META-INF/container.xml"


def _first_ns(tag: str) -> str:
    """Return a tags's local name minus any namespace prefix."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _line_at(content: str, pos: int) -> int:
    """Compute the 1-based line number for a character position."""
    return content.count("\n", 0, pos) + 1


def _attr_line(element: ET.Element, raw_text: str, attr: str) -> int:
    """Best-effort line number for an XML element's start tag using source."""
    # ElementTree doesn't expose line numbers. Scan raw text for the tag's
    # first occurrence after its children are not yet closed.
    return 0


def parse_epub(path: str) -> ParsedEpub:
    """Open an EPUB zip and return its parsed representation.

    Performs only local reads; no network access.
    """
    result = ParsedEpub(path=path)
    result.raw_files = []

    # --- 1. Open the zip container ---
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, OSError) as exc:
        result.errors.append(f"Cannot open EPUB zip: {exc}")
        return result

    with zf:
        names = zf.namelist()
        result.raw_files = list(names)

        # --- 2. mimetype must be first entry, uncompressed ---
        if not names:
            result.errors.append("EPUB zip contains no files.")
            return result

        first = names[0]
        if first != MIMETYPE_NAME:
            result.errors.append(f"mimetype must be the first entry in the EPUB zip (got {first!r}).")
        else:
            info = zf.getinfo(MIMETYPE_NAME)
            if info.compress_type != zipfile.ZIP_STORED:
                result.errors.append(
                    f"mimetype entry must be stored (uncompressed); it is compressed ({info.compress_type})."
                )
            try:
                mimetype_bytes = zf.read(MIMETYPE_NAME)
                result.mimetype = mimetype_bytes.decode("ascii").strip()
            except UnicodeDecodeError:
                result.mimetype = "<binary>"
                result.errors.append("mimetype entry is not valid ASCII text.")
            if result.mimetype != EXPECTED_MIMETYPE:
                result.errors.append(
                    f"mimetype content must be exactly {EXPECTED_MIMETYPE!r}; got {result.mimetype!r}."
                )

        # --- 3. container.xml -> locate OPF ---
        container_raw = None
        if CONTAINER_PATH in names:
            try:
                container_raw = zf.read(CONTAINER_PATH).decode("utf-8")
            except UnicodeDecodeError as exc:
                result.errors.append(f"{CONTAINER_PATH} is not valid UTF-8: {exc}")

        if container_raw is None:
            result.errors.append(f"{CONTAINER_PATH} missing; cannot locate OPF file.")
        else:
            try:
                container_root = ET.fromstring(container_raw)
            except XmlParseError as exc:
                result.errors.append(f"{CONTAINER_PATH} is not valid XML: {exc}")
                container_root = None

            if container_root is not None:
                full_path_opts: List[str] = []
                for child in container_root:
                    if _first_ns(child.tag) == "rootfiles":
                        for rf in child:
                            if _first_ns(rf.tag) == "rootfile":
                                p = rf.get("full-path")
                                if p:
                                    full_path_opts.append(p)
                if full_path_opts:
                    opf_path = full_path_opts[0]
                    result.opf_path = opf_path.strip()
                    # base directory = everything before last '/'
                    if "/" in result.opf_path:
                        result.base_dir = result.opf_path.rsplit("/", 1)[0] + "/"
                else:
                    result.errors.append(f"{CONTAINER_PATH} declares no rootfile full-path.")

        # --- 4. Parse the OPF file ---
        opf_raw = None
        if result.opf_path and result.opf_path in names:
            try:
                opf_raw = zf.read(result.opf_path).decode("utf-8")
            except UnicodeDecodeError as exc:
                result.errors.append(f"{result.opf_path} is not valid UTF-8: {exc}")
        elif result.opf_path:
            result.errors.append(f"OPF file {result.opf_path!r} declared in container.xml was not found in the zip.")

        if opf_raw is not None:
            opf_root, opf_text = _parse_opf(opf_raw, result)
            if opf_root is not None:
                result.version = opf_root.get("version", "")
                result.manifest = _parse_manifest(opf_root, opf_text)
                result.spine = _parse_spine(opf_root, opf_text)
                result.ncx = _parse_ncx(opf_root, zf, names, result)
                result.nav = _parse_nav(opf_root, zf, names, result)

    return result


def _parse_opf(raw_text: str, result: ParsedEpub):
    """Parse OPF XML into ElementTree root, returning (root, raw_text)."""
    try:
        root = ET.fromstring(raw_text)
        return root, raw_text
    except XmlParseError as exc:
        result.errors.append(f"OPF file is not valid XML: {exc}")
        return None, raw_text


def _parse_manifest(root: ET.Element, raw_text: str) -> Dict[str, ManifestItem]:
    manifest: Dict[str, ManifestItem] = {}
    for child in root:
        if _first_ns(child.tag) != "manifest":
            continue
        for item in child:
            if _first_ns(item.tag) != "item":
                continue
            mid = item.get("id") or ""
            href = item.get("href") or ""
            media_type = item.get("media-type") or ""
            properties = item.get("properties") or ""
            manifest[mid] = ManifestItem(
                id=mid,
                href=href,
                media_type=media_type,
                properties=properties,
                line=_line_at(raw_text, raw_text.find("<" + item.tag)),
            )
    return manifest


def _parse_spine(root: ET.Element, raw_text: str) -> List[SpineItem]:
    spine: List[SpineItem] = []
    for child in root:
        if _first_ns(child.tag) != "spine":
            continue
        for item in child:
            if _first_ns(item.tag) != "itemref":
                continue
            spine.append(
                SpineItem(
                    idref=item.get("idref") or "",
                    linear=item.get("linear") or "yes",
                    line=_line_at(raw_text, raw_text.find("<" + item.tag)),
                )
            )
    return spine


def _resolve(href: str, base_dir: str) -> str:
    """Resolve an OPF-relative href to a zip-internal path."""
    if base_dir:
        return base_dir + href.lstrip("/")
    return href.lstrip("/")


def _read_text(zf: zipfile.ZipFile, path: str) -> Optional[str]:
    if path not in zf.namelist():
        return None
    try:
        return zf.read(path).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _find_nav_document(root: ET.Element, zf: zipfile.ZipFile, names: List[str], base_dir: str) -> Optional[str]:
    """Find the EPUB3 nav document path from manifest properties/nav attribute."""
    # Check spine toc attribute first
    spine_el = None
    for child in root:
        if _first_ns(child.tag) == "spine":
            spine_el = child
            break
    if spine_el is not None:
        toc = spine_el.get("toc")
        if toc:
            # toc points to a manifest item id; resolve via manifest
            manifest = {}
            for mchild in root:
                if _first_ns(mchild.tag) == "manifest":
                    for item in mchild:
                        if _first_ns(item.tag) == "item":
                            manifest[item.get("id") or ""] = item.get("href") or ""
            if toc in manifest:
                nav_path = _resolve(manifest[toc], base_dir)
                if nav_path in names:
                    return nav_path
    # Otherwise look for manifest item with nav property
    for mchild in root:
        if _first_ns(mchild.tag) != "manifest":
            continue
        for item in mchild:
            if _first_ns(item.tag) != "item":
                continue
            props = item.get("properties") or ""
            if "nav" in props.split():
                nav_path = _resolve(item.get("href") or "", base_dir)
                if nav_path in names:
                    return nav_path
    return None


def _parse_nav(root: ET.Element, zf: zipfile.ZipFile, names: List[str], result: ParsedEpub) -> Optional[List[NavEntry]]:
    nav_path = _find_nav_document(root, zf, names, result.base_dir)
    if nav_path is None:
        return None
    raw = _read_text(zf, nav_path)
    if raw is None:
        return None
    entries: List[NavEntry] = []
    try:
        nav_root = ET.fromstring(raw)
    except XmlParseError:
        return None
    # Walk the nav document for nav elements whose type is toc/page/landmarks
    for nav_el in nav_root.iter():
        if _first_ns(nav_el.tag) != "nav":
            continue
        kind = nav_el.get("{http://www.idpf.org/2007/ops}type") or nav_el.get("type") or "other"
        # only collect direct anchor children inside this nav section
        for a in nav_el.iter():
            if _first_ns(a.tag) != "a":
                continue
            href = a.get("href") or ""
            label = (a.text or "").strip()
            entries.append(NavEntry(kind=kind, label=label, href=href))
    return entries or None


def _parse_ncx(root: ET.Element, zf: zipfile.ZipFile, names: List[str], result: ParsedEpub) -> Optional[List[NavPoint]]:
    """Locate and parse the EPUB2 NCX toc document referenced from spine toc."""
    # spine toc attribute references manifest item id
    spine_el = None
    for child in root:
        if _first_ns(child.tag) == "spine":
            spine_el = child
            break
    toc_id = spine_el.get("toc") if spine_el is not None else None
    if not toc_id:
        return None
    manifest = {}
    for mchild in root:
        if _first_ns(mchild.tag) == "manifest":
            for item in mchild:
                if _first_ns(item.tag) == "item":
                    manifest[item.get("id") or ""] = item.get("href") or ""
    href = manifest.get(toc_id)
    if not href:
        return None
    ncx_path = _resolve(href, result.base_dir)
    if ncx_path not in names:
        return None
    raw = _read_text(zf, ncx_path)
    if raw is None:
        return None
    try:
        ncx_root = ET.fromstring(raw)
    except XmlParseError:
        return None
    points: List[NavPoint] = []
    for nav_point in ncx_root.iter():
        if _first_ns(nav_point.tag) != "navPoint":
            continue
        label_el = None
        content_el = None
        for ch in nav_point:
            if _first_ns(ch.tag) == "navLabel":
                for sub in ch:
                    if _first_ns(sub.tag) == "text":
                        label_el = sub
            if _first_ns(ch.tag) == "content":
                content_el = ch
        label = (label_el.text or "").strip() if label_el is not None else ""
        src = content_el.get("src") or "" if content_el is not None else ""
        points.append(
            NavPoint(
                label=label,
                content_src=src,
                level=int(nav_point.get("level") or 0),
                play_order=int(nav_point.get("playOrder") or 0),
            )
        )
    return points or None


def iter_hrefs_in_opf(raw_text: str) -> List[Tuple[str, int]]:
    """Return (href, line) for href attributes in raw OPF text."""
    out: List[Tuple[str, int]] = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', raw_text):
        line = raw_text.count("\n", 0, m.start()) + 1
        out.append((m.group(1), line))
    return out
