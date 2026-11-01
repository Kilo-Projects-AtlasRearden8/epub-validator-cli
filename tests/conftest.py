"""Pytest fixtures that build minimal valid EPUB files in tmp_path."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Callable, Dict

import pytest

MIMETYPE = b"application/epub+zip"

CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<container version="1.0" '
    'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
    "  <rootfiles>\n"
    '    <rootfile full-path="OEBPS/content.opf" '
    'media-type="application/oebps-package+xml"/>\n'
    "  </rootfiles>\n"
    "</container>\n"
)

NAV_XHTML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml" '
    'xmlns:epub="http://www.idpf.org/2007/ops">\n'
    "  <head><title>Table of Contents</title></head>\n"
    "  <body>\n"
    '    <nav epub:type="toc">\n'
    "      <h1>Contents</h1>\n"
    "      <ol>\n"
    '        <li><a href="chap1.xhtml">Chapter 1</a></li>\n'
    "      </ol>\n"
    "    </nav>\n"
    "  </body>\n"
    "</html>\n"
)

CHAP1_XHTML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml">\n'
    "  <head><title>Chapter 1</title></head>\n"
    "  <body>\n"
    '    <h1 id="ch1">Chapter 1</h1>\n'
    "    <p>Hello world.</p>\n"
    "  </body>\n"
    "</html>\n"
)

NCX = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
    "  <head>\n"
    '    <meta name="dtb:uid" content="urn:uuid:11111111-1111-1111-1111-111111111111"/>\n'
    '    <meta name="dtb:depth" content="1"/>\n'
    '    <meta name="dtb:totalPageCount" content="0"/>\n'
    '    <meta name="dtb:maxPageNumber" content="0"/>\n'
    "  </head>\n"
    "  <docTitle><text>Test Book</text></docTitle>\n"
    "  <navMap>\n"
    '    <navPoint id="np1" playOrder="1">\n'
    "      <navLabel><text>Chapter 1</text></navLabel>\n"
    '      <content src="chap1.xhtml"/>\n'
    "    </navPoint>\n"
    "  </navMap>\n"
    "</ncx>\n"
)

SMALL_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x00\x00\x00\x00\x00\xff\xd9"


def _opf_epub3(extra_manifest: str = "", extra_spine: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="uid">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '    <dc:identifier id="uid">urn:uuid:11111111-1111-1111-1111-111111111111</dc:identifier>\n'
        "    <dc:title>Test Book</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        '    <meta property="dcterms:modified">2026-01-01T00:00:00Z</meta>\n'
        '    <meta name="cover" content="cover"/>\n'
        "  </metadata>\n"
        "  <manifest>\n"
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
        '    <item id="cover" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>\n'
        '    <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>\n'
        + extra_manifest
        + "  </manifest>\n"
        '  <spine toc="nav">\n'
        '    <itemref idref="chap1"/>\n' + extra_spine + "  </spine>\n"
        "</package>\n"
    )


def _opf_epub2() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0" '
        'unique-identifier="uid">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '    <dc:identifier id="uid">urn:uuid:22222222-2222-2222-2222-222222222222</dc:identifier>\n'
        "    <dc:title>Test Book EPUB2</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        "  </metadata>\n"
        "  <manifest>\n"
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        '    <item id="cover" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>\n'
        '    <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>\n'
        "  </manifest>\n"
        '  <spine toc="ncx">\n'
        '    <itemref idref="chap1"/>\n'
        "  </spine>\n"
        "</package>\n"
    )


def build_epub(
    tmp_path: Path,
    *,
    epub_version: str = "3",
    name: str = "book.epub",
    put_script: bool = False,
    missing_title: bool = False,
    wrong_mimetype: bool = False,
    mimetype_compressed: bool = False,
    no_container: bool = False,
    no_mimetype_first: bool = False,
    broken_zip: bool = False,
    empty_spine: bool = False,
    spine_missing_idref: bool = False,
    cover_missing: bool = False,
    nav_link_broken: bool = False,
    content_link_broken: bool = False,
    duplicate_id: bool = False,
) -> Path:
    """Build a minimal EPUB zip at ``tmp_path / name`` with optional defects.

    Returns the path to the created .epub file.
    """
    path = tmp_path / name

    if broken_zip:
        path.write_bytes(b"not a zip file at all")
        return path

    files: Dict[str, bytes] = {}

    # mimetype must be first entry; zipfile writes in dict order
    mt_content = b"application/epub+zip"
    if wrong_mimetype:
        mt_content = b"text/plain"
    files["mimetype"] = mt_content

    if not no_container:
        files["META-INF/container.xml"] = CONTAINER_XML.encode("utf-8")

    opf = _opf_epub3() if epub_version == "3" else _opf_epub2()
    if missing_title:
        opf = opf.replace("<dc:title>Test Book</dc:title>", "")
        opf = opf.replace("<dc:title>Test Book EPUB2</dc:title>", "")
    if cover_missing:
        opf = opf.replace('properties="cover-image"', "")
        opf = opf.replace('<meta name="cover" content="cover"/>', "")
    if empty_spine:
        opf = opf.replace('    <itemref idref="chap1"/>\n', "")
    if spine_missing_idref:
        opf = opf.replace(
            '    <itemref idref="chap1"/>\n',
            '    <itemref idref="does-not-exist"/>\n',
        )
    files["OEBPS/content.opf"] = opf.encode("utf-8")

    files["OEBPS/nav.xhtml"] = NAV_XHTML.encode("utf-8")
    files["OEBPS/chap1.xhtml"] = CHAP1_XHTML.encode("utf-8")
    files["OEBPS/cover.jpg"] = SMALL_JPEG

    if epub_version == "2":
        files["OEBPS/toc.ncx"] = NCX.encode("utf-8")

    if put_script:
        files["OEBPS/chap1.xhtml"] = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<html xmlns="http://www.w3.org/1999/xhtml">\n'
            b"  <head><title>Chapter 1</title></head>\n"
            b"  <body>\n"
            b'    <script>alert("hi");</script>\n'
            b"    <p>Hello world.</p>\n"
            b"  </body>\n"
            b"</html>\n"
        )

    if nav_link_broken:
        files["OEBPS/nav.xhtml"] = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<html xmlns="http://www.w3.org/1999/xhtml" '
            b'xmlns:epub="http://www.idpf.org/2007/ops">\n'
            b"  <head><title>Table of Contents</title></head>\n"
            b"  <body>\n"
            b'    <nav epub:type="toc">\n'
            b"      <h1>Contents</h1>\n"
            b"      <ol>\n"
            b'        <li><a href="missing.xhtml">Missing</a></li>\n'
            b"      </ol>\n"
            b"    </nav>\n"
            b"  </body>\n"
            b"</html>\n"
        )

    if content_link_broken:
        files["OEBPS/chap1.xhtml"] = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<html xmlns="http://www.w3.org/1999/xhtml">\n'
            b"  <head><title>Chapter 1</title></head>\n"
            b"  <body>\n"
            b'    <a href="nope.xhtml">broken</a>\n'
            b"  </body>\n"
            b"</html>\n"
        )

    if duplicate_id:
        files["OEBPS/chap1.xhtml"] = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<html xmlns="http://www.w3.org/1999/xhtml">\n'
            b"  <head><title>Chapter 1</title></head>\n"
            b"  <body>\n"
            b'    <h1 id="ch1">Chapter 1</h1>\n'
            b'    <p id="ch1">dup</p>\n'
            b"  </body>\n"
            b"</html>\n"
        )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be stored (uncompressed). Write it first, stored.
        if mimetype_compressed:
            # write all normally; mimetype will be deflated (wrong)
            for name, data in files.items():
                zf.writestr(name, data)
        else:
            zf.writestr("mimetype", files["mimetype"], zipfile.ZIP_STORED)
            for name, data in files.items():
                if name == "mimetype":
                    continue
                zf.writestr(name, data)

    if no_mimetype_first:
        # Rebuild so mimetype is not first: put container.xml first.
        ordered = [
            ("META-INF/container.xml", files["META-INF/container.xml"]),
            ("mimetype", files["mimetype"]),
        ]
        rest = [(n, d) for n, d in files.items() if n not in ("mimetype", "META-INF/container.xml")]
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("META-INF/container.xml", ordered[0][1], zipfile.ZIP_STORED)
            zf.writestr("mimetype", files["mimetype"], zipfile.ZIP_STORED)
            for n, d in rest:
                zf.writestr(n, d)

    return path


@pytest.fixture
def valid_epub3(tmp_path: Path) -> Path:
    return build_epub(tmp_path, epub_version="3")


@pytest.fixture
def valid_epub2(tmp_path: Path) -> Path:
    return build_epub(tmp_path, epub_version="2")


@pytest.fixture
def epub_builder(tmp_path: Path) -> Callable[..., Path]:
    return lambda **kw: build_epub(tmp_path, **kw)
