"""Shared CLI helpers -- importable from anywhere without cycles."""

from __future__ import annotations

import json as _json
import sys
from typing import Any


def output(data: Any, as_json: bool) -> None:
    """Print *data*.  JSON to stdout if *as_json*; human-readable otherwise."""
    if as_json:
        _json.dump(data, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    elif isinstance(data, str):
        print(data)
    elif isinstance(data, dict):
        for k, v in data.items():
            print(f"{k}: {v}")
    elif data is None:
        pass
    else:
        print(data)


def error(message: str) -> None:
    """Print an error to stderr."""
    print(f"error: {message}", file=sys.stderr)


def exit_fail(code: int, message: str = "") -> None:
    """Exit with an error code and optional message to stderr."""
    if message:
        error(message)
    sys.exit(code)
