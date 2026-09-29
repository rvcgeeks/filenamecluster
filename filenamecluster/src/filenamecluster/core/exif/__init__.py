"""Capture times stored inside pictures, videos, and PDFs.

Other packages import ``read_exif_timestamp`` from ``filenamecluster.core.exif``.
"""

from .read import read_exif_timestamp

__all__ = ["read_exif_timestamp"]
