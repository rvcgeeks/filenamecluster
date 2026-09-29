"""Languages for the window.

The catalogs are JSON files in ``ui/assets/i18n``. English is the default.
Hindi, Marathi, German, French, Japanese, and Korean use the same keys.
This module belongs to the view: it turns a catalog key into the words on
the window. The session model does not import it.

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import json
import string
import sys
from pathlib import Path

from filenamecluster.log import trace_module
from filenamecluster.ui.model import LearnedKind, LearnedSummary

_DIR = Path(__file__).resolve().parents[1] / "assets" / "i18n"

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

def language_name(code: str = "en") -> str:
    chosen = code if code in CATALOGS else "en"
    return next(name for lang, name in LANGUAGES if lang == chosen)


def t(key: str, *, code: str = "en", **kwargs: object) -> str:
    """Translate ``key`` explicitly, then fall back to English and the key."""

    catalog = CATALOGS.get(code, EN)
    text = catalog.get(key) or EN.get(key) or key
    return text.format(**kwargs) if kwargs else text


def file_count(count: int, code: str = "en") -> str:
    key = "file_one" if count == 1 else "file_many"
    return t(key, code=code, n=count)


def describe_model(summary: LearnedSummary, code: str = "en", translate=None) -> str:
    """One status-line sentence from presentation-neutral learned facts."""

    phrase = translate or (lambda key, **fields: t(key, code=code, **fields))
    name = "filenamecluster-model.json"
    if summary.kind is LearnedKind.NONE:
        return phrase("model_none", name=name)
    if summary.kind is LearnedKind.ONE_GROUP:
        return phrase("model_one", name=name)
    boundary = summary.boundary_hours or 0
    return phrase("model_learned", hours=f"{boundary:.0f}", name=name)


trace_module(sys.modules[__name__])
