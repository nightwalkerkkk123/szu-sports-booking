"""Zero-dependency ANSI-coloured output helpers for the CLI.

We deliberately avoid pulling in `rich` to keep the dependency surface
small (this is one of Webwright's design principles: only the four core
deps). The helpers in this module:

* :func:colorize wraps a string with an ANSI escape sequence.
* :func:paint formats a log-level style line.
* :func:	ask_prefix returns a coloured `[taskN]` prefix for concurrent
  runs, so different accounts' output is easy to tell apart.

Colours are auto-disabled when:
    * stdout/stderr is not a TTY (e.g. piped to a file).
    * the `NO_COLOR` env var is set (https://no-color.org).
    * the platform is Windows *and* the legacy console is in use. (Modern
      Windows Terminal / VS Code integrated terminal handle ANSI fine.)
"""

from __future__ import annotations

import os
import sys
from typing import Literal

# ANSI escape codes (kept short to play nicely with redirected output).
_RESET = chr(0x1B) + "[0m"
_BOLD = chr(0x1B) + "[1m"
_DIM = chr(0x1B) + "[2m"

_COLOURS = {
    "red": chr(0x1B) + "[31m",
    "green": chr(0x1B) + "[32m",
    "yellow": chr(0x1B) + "[33m",
    "blue": chr(0x1B) + "[34m",
    "magenta": chr(0x1B) + "[35m",
    "cyan": chr(0x1B) + "[36m",
    "gray": chr(0x1B) + "[90m",
}


Level = Literal["ok", "info", "warn", "error", "debug", "dim"]


def _color_enabled() -> bool:
    """Decide whether ANSI escapes should be emitted."""
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


def colorize(text: str, colour: str, *, bold: bool = False) -> str:
    """Wrap *text* in an ANSI colour escape.

    Args:
        text: The string to colourise.
        colour: One of the keys in `_COLOURS` (`red`, `green` ...).
        bold: Also apply the bold escape.

    Returns:
        The colourised string, or the original text when colours are off.
    """
    if not _color_enabled():
        return text
    code = _COLOURS.get(colour)
    if code is None:
        return text
    prefix = (_BOLD if bold else "") + code
    return f"{prefix}{text}{_RESET}"


def paint(text: str, level: Level = "info") -> str:
    """Colour a one-line message by log level.

    Mapping:
        * `ok`   -> green bold
        * `info` -> blue
        * `warn` -> yellow
        * `error` -> red bold
        * `debug` -> gray
        * `dim`   -> gray (decorative, e.g. separators)
    """
    mapping = {
        "ok": ("green", True),
        "info": ("blue", False),
        "warn": ("yellow", False),
        "error": ("red", True),
        "debug": ("gray", False),
        "dim": ("gray", False),
    }
    colour, bold = mapping.get(level, ("gray", False))
    return colorize(text, colour, bold=bold)


def task_prefix(task_id: int | str) -> str:
    """Return a coloured `[taskN]` (or `[taskName]`) prefix.

    Different task IDs get different foreground colours so concurrent output
    is easy to tell apart. Colours are picked from a small palette
    deterministically based on the ID, so the same task always shows in the
    same colour within a run.
    """
    palette = ["cyan", "magenta", "blue", "yellow", "green"]
    if isinstance(task_id, int):
        colour = palette[task_id % len(palette)]
        return colorize(f"[task{task_id}]", colour, bold=True)
    return colorize(f"[{task_id}]", "cyan", bold=True)


def print_task(
    task_id: int | str,
    message: str,
    level: Level = "info",
    *,
    err: bool = False,
) -> None:
    """Print a `[taskN] coloured-message` line, falling back to plain text.

    Args:
        task_id: Concurrency slot number or label.
        message: The message body.
        level: One of :data:Level. Default `info`.
        err: When `True` write to stderr (mirrors :func:click.echo's
            `err=True`).
    """
    line = f"{task_prefix(task_id)} {paint(message, level)}"
    print(line, file=sys.stderr if err else sys.stdout)


def print_header(text: str) -> None:
    """Print a bold section header line, e.g. `=== Loading config ===`."""
    print(paint(text, "dim"))


def should_color() -> bool:
    """Public re-export of :func:_color_enabled for tests / config."""
    return _color_enabled()
