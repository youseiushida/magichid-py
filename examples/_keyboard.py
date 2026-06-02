"""Convenience builders for boot-keyboard and mouse HID reports.

These are *examples* of how to construct report payloads — they are not part
of the protocol core.  Use them as-is, copy them, or replace them with your
own builders for other profiles.  All they do is lay out bytes; the actual
rules (size, relative/reliable) are enforced by :class:`core.reports.ReportTable`.
"""

from __future__ import annotations

__all__ = [
    "KEY_MOD", "keyboard_report", "mouse_report", "char_to_keycode",
]


class KEY_MOD:
    """Keyboard modifier bitmask (HID boot-keyboard byte 0)."""

    LCTRL = 0x01
    LSHIFT = 0x02
    LALT = 0x04
    LGUI = 0x08
    RCTRL = 0x10
    RSHIFT = 0x20
    RALT = 0x40
    RGUI = 0x80


def keyboard_report(keys: bytes | tuple[int, ...] = (), modifier: int = 0) -> bytes:
    """Boot-keyboard 8-byte INPUT: ``[modifier][reserved=0][k1..k6]``."""
    kc = list(keys)
    if len(kc) > 6:
        raise ValueError("at most 6 simultaneous keycodes")
    kc += [0] * (6 - len(kc))
    return bytes([modifier & 0xFF, 0, *(k & 0xFF for k in kc)])


def mouse_report(buttons: int = 0, x: int = 0, y: int = 0,
                 wheel: int = 0, pan: int = 0) -> bytes:
    """5-byte mouse INPUT: ``[buttons][x][y][wheel][pan]`` (signed int8 deltas)."""
    return bytes([buttons & 0xFF, *((v & 0xFF) for v in (x, y, wheel, pan))])


def char_to_keycode(ch: str) -> tuple[int, int]:
    """Single ASCII char -> ``(modifier, keycode)``.

    Covers a-z, A-Z, 0-9 and a few common symbols — enough for demos.
    US layout only; not a full IME.
    """
    if len(ch) != 1:
        raise ValueError("exactly one character required")
    o = ord(ch)
    if "a" <= ch <= "z":
        return 0, 0x04 + (o - 0x61)
    if "A" <= ch <= "Z":
        return KEY_MOD.LSHIFT, 0x04 + (o - 0x41)
    if "1" <= ch <= "9":
        return 0, 0x1E + (o - 0x31)
    if ch == "0":
        return 0, 0x27
    m = {
        " ": (0, 0x2C), "\n": (0, 0x28), "\t": (0, 0x2B),
        "-": (0, 0x2D), "=": (0, 0x2E), ".": (0, 0x37),
        ",": (0, 0x36), "/": (0, 0x38), ";": (0, 0x33),
    }
    if ch in m:
        return m[ch]
    raise KeyError(f"no keycode for {ch!r}")
