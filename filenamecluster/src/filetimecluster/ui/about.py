"""Help text shown in the About tab. The wording lives in the JSON catalogs.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
Introduction: ``readme.md``. Mathematics: ``docs/algorithm.md``.
Design: ``docs/architecture.md``.
"""

from filetimecluster.ui.i18n import t

SECTION_KEYS: tuple[tuple[str, str], ...] = (
    ("about_what_title", "about_what_body"),
    ("about_how_title", "about_how_body"),
    ("about_views_title", "about_views_body"),
    ("about_names_title", "about_names_body"),
    ("about_files_title", "about_files_body"),
    ("about_options_title", "about_options_body"),
    ("about_author_title", "about_author_body"),
)


def sections() -> tuple[tuple[str, str], ...]:
    """Heading and body for each About section, in the current language."""

    return tuple((t(title), t(body)) for title, body in SECTION_KEYS)
