"""Help text shown in the About tab. The wording lives in the JSON catalogs.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

import sys
from collections.abc import Callable

from filenamecluster.log import log_path, trace_module
from .i18n import t

SECTION_KEYS: tuple[tuple[str, str], ...] = (
    ("about_what_title", "about_what_body"),
    ("about_how_title", "about_how_body"),
    ("about_views_title", "about_views_body"),
    ("about_names_title", "about_names_body"),
    ("about_files_title", "about_files_body"),
    ("about_options_title", "about_options_body"),
    ("about_regex_title", "about_regex_body"),
    ("about_regex_marks_title", "about_regex_marks_body"),
    ("about_regex_kinds_title", "about_regex_kinds_body"),
    ("about_regex_camera_title", "about_regex_camera_body"),
    ("about_regex_scan_title", "about_regex_scan_body"),
    ("about_regex_table_title", "about_regex_table_body"),
    ("about_logging_title", "about_logging_body"),
    ("about_author_title", "about_author_body"),
)


def sections(translate: Callable[..., str] = t) -> tuple[tuple[str, str], ...]:
    """Heading and body for each About section."""

    rendered: list[tuple[str, str]] = []
    for title, body in SECTION_KEYS:
        if body == "about_logging_body":
            text = translate(body, path=str(log_path()))
        elif body.startswith("about_regex"):
            text = translate(body).format()
        else:
            text = translate(body)
        rendered.append((translate(title), text))
    return tuple(rendered)


trace_module(sys.modules[__name__])
