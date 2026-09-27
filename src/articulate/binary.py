#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""articulate.binary -- refuse inputs that are not screenable text.
Standard library only.
"""
import os

# Magic-byte signatures for common binary and Office formats. A file that starts
# with one of these is not screenable prose, so a caller refuses it and never
# scans the replacement characters a lossy UTF-8 decode would produce.
_SIGNATURES = [
    (b"PK\x03\x04", "a Zip-based Office file (.docx/.xlsx/.pptx) or archive"),
    (b"PK\x05\x06", "an empty Zip archive"),
    (b"%PDF-", "a PDF"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "a legacy Office file (.doc/.xls/.ppt)"),
    (b"{\\rtf", "an RTF document"),
    (b"\x89PNG\r\n\x1a\n", "a PNG image"),
    (b"\xff\xd8\xff", "a JPEG image"),
    (b"GIF87a", "a GIF image"),
    (b"GIF89a", "a GIF image"),
    (b"\x1f\x8b", "a gzip archive"),
    (b"Rar!\x1a\x07", "a RAR archive"),
    (b"\x7fELF", "an ELF binary"),
    (b"%!PS", "a PostScript file"),
    (b"\x00\x00\x00\x00", "binary data"),
]

# Extensions we refuse by name even before reading, for known non-prose formats.
_BINARY_EXTENSIONS = frozenset({
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".pdf", ".odt", ".ods",
    ".odp", ".rtf", ".pages", ".key", ".numbers", ".png", ".jpg", ".jpeg",
    ".gif", ".bmp", ".webp", ".ico", ".tif", ".tiff", ".svgz", ".zip", ".gz",
    ".tar", ".rar", ".7z", ".exe", ".dll", ".so", ".dylib", ".bin", ".mp3",
    ".mp4", ".wav", ".mov", ".avi", ".mkv", ".ttf", ".otf", ".woff", ".woff2",
})


def binary_reason(data: bytes, name: str = None) -> str:
    """A human reason if these bytes are not screenable text (a known binary or
    document format, or content with null bytes), or None if the file is text.
    Fail-closed: a caller refuses the input and never scans replacement
    characters. English-only note: the patterns are English literals, so a
    decoded non-English document scans as inapplicable and is never verified."""
    if name:
        ext = os.path.splitext(str(name))[1].lower()
        if ext in _BINARY_EXTENSIONS:
            return f"unsupported binary or document format ({ext})"
    for sig, desc in _SIGNATURES:
        if data.startswith(sig):
            return f"unsupported binary: {desc}"
    if b"\x00" in data[:8192]:
        return "unsupported binary (contains null bytes)"
    return None
