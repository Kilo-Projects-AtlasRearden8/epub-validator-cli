"""Data models for parsed EPUB artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ManifestItem:
    """A single resource declared in the OPF ``<manifest>`` element."""

    id: str
    href: str
    media_type: str = ""
    properties: str = ""
    line: int = 0  # source line within the OPF file (1-based, 0 = unknown)


@dataclass
class SpineItem:
    """A single entry in the OPF ``<spine>`` element (a reading order item)."""

    idref: str
    linear: str = "yes"
    line: int = 0


@dataclass
class NavPoint:
    """A navigation point from an NCX file (used for table of contents)."""

    label: str
    content_src: str
    level: int = 0
    play_order: int = 0
    line: int = 0


@dataclass
class NavEntry:
    """A navigation entry from the EPUB3 ``<nav>`` element."""

    kind: str  # "toc", "page", "landmarks", "other"
    label: str
    href: str
    line: int = 0


@dataclass
class ParsedEpub:
    """The fully parsed EPUB representation."""

    path: str
    mimetype: str = ""
    version: str = ""  # derived from OPF version attribute
    opf_path: str = ""  # path inside the zip (e.g. "OEBPS/content.opf")
    base_dir: str = ""  # directory of the OPF inside the zip
    manifest: Dict[str, ManifestItem] = field(default_factory=dict)
    spine: List[SpineItem] = field(default_factory=list)
    ncx: Optional[List[NavPoint]] = None
    nav: Optional[List[NavEntry]] = None
    raw_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
