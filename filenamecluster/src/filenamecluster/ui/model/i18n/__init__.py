"""Languages for the window. Catalogs are JSON files beside this module.

English is the default. Hindi, Marathi, German, French, Japanese, and Korean use the same keys.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import sys
from filenamecluster.log import trace_module

import json
import string
from pathlib import Path

_DIR = Path(__file__).resolve().parent

LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("hi", "हिन्दी"),
    ("mr", "मराठी"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("ja", "日本語"),
    ("ko", "한국어"),
)


def _load(code: str) -> dict[str, str]:
    data = json.loads((_DIR / f"{code}.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(value, str) for value in data.values()):
        raise RuntimeError(f"{code}.json must be an object of strings")
    return data


def _fields(text: str) -> set[str]:
    return {name for _literal, name, _format, _conversion in string.Formatter().parse(text) if name}


CATALOGS: dict[str, dict[str, str]] = {code: _load(code) for code, _name in LANGUAGES}
EN = CATALOGS["en"]

_problems: list[str] = []
for code, catalog in CATALOGS.items():
    if set(catalog) != set(EN):
        _problems.append(f"{code} keys {sorted(set(EN) ^ set(catalog))}")
    for key, value in catalog.items():
        if key not in EN:
            continue
        if not value.strip():
            _problems.append(f"{code}.{key} is empty")
        elif _fields(value) != _fields(EN[key]):
            _problems.append(f"{code}.{key} placeholders differ")
if _problems:
    raise RuntimeError("i18n catalogs do not match English: " + "; ".join(_problems))

_language = "en"


def language() -> str:
    return _language


def set_language(code: str) -> None:
    """Select a catalog. Unknown codes stay on English."""

    global _language
    _language = code if code in CATALOGS else "en"


def language_name(code: str | None = None) -> str:
    chosen = _language if code is None else code
    return next(name for lang, name in LANGUAGES if lang == chosen)


def t(key: str, **kwargs: object) -> str:
    """Translate ``key`` into the current language, then English, then the key."""

    catalog = CATALOGS.get(_language, EN)
    text = catalog.get(key) or EN.get(key) or key
    return text.format(**kwargs) if kwargs else text


def file_count(count: int) -> str:
    return t("file_one", n=count) if count == 1 else t("file_many", n=count)

trace_module(sys.modules[__name__])
