"""Convenience builder for the HORIPAD (Nintendo Switch) profile.

This is an *example* — not part of the protocol core.  The byte layout is the
contract in ``spec/horipad.md``; this module just encodes it as a Python
function.  Use as-is, copy, or replace.
"""

from __future__ import annotations

__all__ = [
    "HORIPAD_NEUTRAL", "HORIPAD_BUTTONS", "HORIPAD_DPAD", "horipad_report",
]

# Neutral: nothing pressed, sticks centered (0x80), hat centered (0x0F).
HORIPAD_NEUTRAL = bytes([0x00, 0x00, 0x0F, 0x80, 0x80, 0x80, 0x80, 0x00])

HORIPAD_BUTTONS = {
    "Y": 0, "B": 1, "A": 2, "X": 3,
    "L": 4, "R": 5, "ZL": 6, "ZR": 7,
    "MINUS": 8, "PLUS": 9,
    "LCLICK": 10, "RCLICK": 11,
    "HOME": 12, "CAPTURE": 13,
}

HORIPAD_DPAD = {
    "UP": 0, "UP_RIGHT": 1, "RIGHT": 2, "DOWN_RIGHT": 3,
    "DOWN": 4, "DOWN_LEFT": 5, "LEFT": 6, "UP_LEFT": 7,
    "CENTER": 0x0F,
}


def horipad_report(
    buttons: tuple[str, ...] = (),
    dpad: str = "CENTER",
    lx: int = 0x80,
    ly: int = 0x80,
    rx: int = 0x80,
    ry: int = 0x80,
    vendor: int = 0x00,
) -> bytes:
    """Bare 8-byte HORIPAD controller state (full-state, no deltas)."""
    bits = 0
    for name in buttons:
        bits |= 1 << HORIPAD_BUTTONS[name]
    return bytes([
        bits & 0xFF,
        (bits >> 8) & 0xFF,
        HORIPAD_DPAD[dpad] & 0x0F,
        lx & 0xFF, ly & 0xFF,
        rx & 0xFF, ry & 0xFF,
        vendor & 0xFF,
    ])
