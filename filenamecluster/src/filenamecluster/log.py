"""File logging for the application.

Each line carries a timestamp and the process id. ``CALL`` is written before
a function runs, ``ENTER`` as it begins, and ``EXIT`` when it returns.
``EVENT`` marks a key step such as saving the model. ``DETAIL`` records a
decision or an intermediate value inside a function.

Logging is off until Options, Write application log, is turned on.
The file lives where this operating system keeps application logs:

- macOS: ``~/Library/Logs/filenamecluster/filenamecluster.log``
- Windows: ``%LOCALAPPDATA%/filenamecluster/Logs/filenamecluster.log``
- Linux: ``$XDG_STATE_HOME/filenamecluster/filenamecluster.log``, or
  ``~/.local/state/filenamecluster/filenamecluster.log``

Author: Rajas Chavadekar (rvchavadekar@gmail.com).
"""

from __future__ import annotations

import functools
import logging
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

_LOGGER_NAME = "filenamecluster"
_STATE: dict[str, str | None] = {"path": None}
_ENABLED = False
_LOCAL = threading.local()
_F = TypeVar("_F", bound=Callable[..., object])

_SKIP_DUNDERS = frozenset(
    {
        "__getattr__",
        "__setattr__",
        "__getattribute__",
        "__new__",
        "__init_subclass__",
        "__class_getitem__",
    }
)


def log_path() -> Path:
    """Absolute path of the log file for this operating system."""

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "filenamecluster" / "filenamecluster.log"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / "filenamecluster" / "Logs" / "filenamecluster.log"
    state = os.environ.get("XDG_STATE_HOME")
    root = Path(state) if state else Path.home() / ".local" / "state"
    return root / "filenamecluster" / "filenamecluster.log"


def configure() -> Path:
    """Open the log file. Later calls keep the same file until the path changes."""

    path = log_path()
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    key = str(path)
    if _STATE["path"] == key and logger.handlers:
        return path
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError:
        logger.addHandler(logging.NullHandler())
        _STATE["path"] = key
        return path
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d pid=%(process)d %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    _STATE["path"] = key
    logger.info("EVENT logging_started path=%s", path)
    return path


def logging_enabled() -> bool:
    """Whether new lines are written. The application starts with this off."""

    return _ENABLED


def set_logging_enabled(enabled: bool) -> None:
    """Turn file logging on or off. The last change itself is still recorded."""

    global _ENABLED
    enabled = bool(enabled)
    if enabled == _ENABLED:
        return
    if enabled:
        _ENABLED = True
        event("logging_enabled")
        return
    event("logging_disabled")
    _ENABLED = False


def _write(message: str) -> None:
    """One log line. Failures here must not change what the caller was doing."""

    if not _ENABLED or getattr(_LOCAL, "on", False):
        return
    _LOCAL.on = True
    try:
        try:
            configure()
            logging.getLogger(_LOGGER_NAME).info(message)
        except Exception:  # noqa: BLE001  # a log failure must not change the caller
            return
    finally:
        _LOCAL.on = False


def _field(value: object) -> str:
    text = str(value).replace("\n", " ")
    if any(char.isspace() for char in text):
        return '"' + text.replace('"', "'") + '"'
    return text


def log_call(target: str) -> None:
    """Write ``CALL`` immediately before invoking ``target``."""

    _write(f"CALL {target}")


def event(marker: str, **fields: object) -> None:
    """Write ``EVENT`` for a key step, with ``key=value`` details."""

    _write(_line("EVENT", marker, fields))


def detail(marker: str, **fields: object) -> None:
    """Write ``DETAIL`` for a decision or an intermediate value inside a function."""

    _write(_line("DETAIL", marker, fields))


def _line(kind: str, name: str, fields: dict[str, object]) -> str:
    extra = " ".join(f"{key}={_field(fields[key])}" for key in fields)
    message = f"{kind} {name}"
    if extra:
        message = f"{message} {extra}"
    return message


def traced(fn: _F) -> _F:
    """Log ``CALL``, ``ENTER``, and ``EXIT`` around ``fn``."""

    if getattr(fn, "_filenamecluster_traced", False):
        return fn
    qual = f"{fn.__module__}.{fn.__qualname__}"

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        _write(f"CALL {qual}")
        _write(f"ENTER {qual}")
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            _write(f"EXIT {qual} error={type(exc).__name__}")
            raise
        _write(f"EXIT {qual}")
        return result

    wrapper._filenamecluster_traced = True  # type: ignore[attr-defined]
    return wrapper  # type: ignore[return-value]


def _own(module_name: str, fn: object) -> bool:
    return getattr(fn, "__module__", None) == module_name and not getattr(
        fn, "_filenamecluster_traced", False
    )


def _wrap(module_name: str, owner: object, name: str, member: object) -> None:
    if name.startswith("__") and name not in {"__init__", "__post_init__"}:
        return
    if name in _SKIP_DUNDERS:
        return
    if isinstance(member, staticmethod):
        fn = member.__func__
        if _own(module_name, fn):
            setattr(owner, name, staticmethod(traced(fn)))
        return
    if isinstance(member, classmethod):
        fn = member.__func__
        if _own(module_name, fn):
            setattr(owner, name, classmethod(traced(fn)))
        return
    if isinstance(member, property):
        return
    if callable(member) and _own(module_name, member):
        setattr(owner, name, traced(member))


def trace_module(module: object) -> None:
    """Log entry, exit, and the call of every function defined in ``module``."""

    name = getattr(module, "__name__", "")
    if not isinstance(name, str) or name == "filenamecluster.log" or name.endswith(".log"):
        return
    for attr, member in list(vars(module).items()):
        if isinstance(member, type) and getattr(member, "__module__", None) == name:
            for class_attr, class_member in list(vars(member).items()):
                _wrap(name, member, class_attr, class_member)
            continue
        if callable(member) and _own(name, member):
            setattr(module, attr, traced(member))
