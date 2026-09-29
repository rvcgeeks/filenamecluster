"""Pull an EXIF block out of a JPEG, PNG, WebP, or HEIF container.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import sys

from filenamecluster.log import trace_module

_MAX_READ = 1_048_576
_MAX_SEGMENT = 2_000_000
_JPEG_STANDALONE = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7}


def _jpeg_marker(handle) -> int | None:
    if handle.read(1) != b"\xff":
        return None
    while True:
        value = handle.read(1)
        if not value:
            return None
        if value != b"\xff":
            return value[0]


def _jpeg_exif(handle) -> bytes | None:
    if handle.read(2) != b"\xff\xd8":
        return None
    while True:
        marker = _jpeg_marker(handle)
        if marker is None or marker in {0xD8, 0xD9, 0xDA}:
            return None
        if marker in _JPEG_STANDALONE:
            continue
        size_raw = handle.read(2)
        if len(size_raw) != 2:
            return None
        size = int.from_bytes(size_raw, "big")
        if size < 2:
            return None
        if size > _MAX_SEGMENT:
            handle.seek(size - 2, 1)
            continue
        payload = handle.read(size - 2)
        if len(payload) != size - 2:
            return None
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return payload[6:]


def _png_exif(handle) -> bytes | None:
    if handle.read(8) != b"\x89PNG\r\n\x1a\n":
        return None
    while True:
        header = handle.read(8)
        if len(header) != 8:
            return None
        length = int.from_bytes(header[:4], "big")
        kind = header[4:8]
        if kind == b"IEND" or length > _MAX_SEGMENT:
            return None
        data = handle.read(length)
        handle.read(4)
        if len(data) != length:
            return None
        if kind == b"eXIf":
            return data


def _webp_exif(handle) -> bytes | None:
    header = handle.read(12)
    if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    while True:
        chunk = handle.read(8)
        if len(chunk) != 8:
            return None
        kind = chunk[:4]
        size = int.from_bytes(chunk[4:8], "little")
        if size > _MAX_SEGMENT:
            return None
        data = handle.read(size)
        if len(data) != size:
            return None
        if size % 2:
            handle.read(1)
        if kind == b"EXIF":
            if data.startswith(b"Exif\x00\x00"):
                return data[6:]
            return data


def _search_exif_header(handle) -> bytes | None:
    """Find an ``Exif`` TIFF block inside a HEIF/AVIF file."""

    marker = b"Exif\x00\x00"
    pending = b""
    scanned = 0
    while scanned < _MAX_READ:
        block = handle.read(65536)
        if not block:
            return None
        scanned += len(block)
        data = pending + block
        found = data.find(marker)
        if found != -1:
            rest = data[found + len(marker) :]
            if len(rest) < 64:
                rest += handle.read(65536)
            return rest
        pending = data[1 - len(marker) :]
    return None


trace_module(sys.modules[__name__])
