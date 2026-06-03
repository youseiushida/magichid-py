"""HORIPAD wired gamepad (profile 1) — single 8-byte report, no Report ID.

Conforms to:
* `spec/horipad.md`_ — complete byte/bit layout contract
* `spec/PROTOCOL.md §5`_ — profile 1 definition

The descriptor carries **no Report ID**, so the ``SEND_REPORT`` payload is the
bare 8-byte controller state.  ``ReportTable.horipad()`` returns a single-entry
table ``[id=0, in_len=8, out_len=0, feat_len=0, flags=0]``.

Switching to this profile requires ``SET_IDENTITY`` (profile=1), which triggers
a USB re-enumeration — the operator must reconnect the serial port afterwards.
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

# ---------------------------------------------------------------------------
# Neutral state (spec/horipad.md §Neutral state)
# ---------------------------------------------------------------------------
_NEUTRAL = bytes([0x00, 0x00, 0x0F, 0x80, 0x80, 0x80, 0x80, 0x00])

_REPORT_ID = 0  # descriptor has no Report ID

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HoripadButton(IntEnum):
    """Nintendo Switch controller buttons — wire bit positions (0–13).

    Bit *n* lives in byte 0 for *n* < 8, byte 1 for *n* ≥ 8.
    Bits 14–15 are unused (constant 0).
    """

    Y = 0
    B = 1
    A = 2
    X = 3
    L = 4
    R = 5
    ZL = 6
    ZR = 7
    MINUS = 8
    PLUS = 9
    L_STICK = 10
    R_STICK = 11
    HOME = 12
    CAPTURE = 13

    def bit(self) -> int:
        """Bitmask for the 16-bit button field."""
        return 1 << self


class HoripadDpad(IntEnum):
    """D-pad / hat switch values (byte 2, low nibble).

    In the descriptor this is a single HAT switch usage with 8 directions;
    ``0x0F`` is the centred (neutral) position.
    """

    UP = 0
    UP_RIGHT = 1
    RIGHT = 2
    DOWN_RIGHT = 3
    DOWN = 4
    DOWN_LEFT = 5
    LEFT = 6
    UP_LEFT = 7
    CENTER = 0x0F


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class Horipad:
    """HORIPAD wired controller — buttons, d-pad, dual analog sticks.

    Usage::

        pad = Horipad(client, ReportTable.horipad())

        pad.press(HoripadButton.A)
        pad.set_dpad(HoripadDpad.RIGHT)
        pad.set_stick_left(x=0.5, y=-0.3)
        pad.set_stick_right(x=0.0, y=0.0)
        pad.release_all()           # return to neutral

    Stick values are normalised floats (-1.0 … 1.0, centre 0.0).
    Raw ``int`` access is also available via ``*_raw`` methods.
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._buttons: int = 0          # 16-bit button bitmap
        self._dpad: int = 0x0F          # hat value (low nibble)
        self._lx: int = 0x80            # left stick X (0x00–0xFF, 0x80 centre)
        self._ly: int = 0x80
        self._rx: int = 0x80
        self._ry: int = 0x80
        self._batched: bool = False
        self._dirty: bool = False

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    @property
    def buttons(self) -> int:
        """Current 16-bit button bitmap."""
        return self._buttons

    def is_pressed(self, button: HoripadButton) -> bool:
        """True if *button* is currently held."""
        return bool(self._buttons & button.bit())

    def press(self, *buttons: HoripadButton) -> None:
        """Press one or more buttons (held until released)."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons |= b.bit()
        if self._buttons != prev:
            self._dirty = True
            self._maybe_flush()

    def release(self, *buttons: HoripadButton) -> None:
        """Release one or more buttons."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons &= ~b.bit()
        if self._buttons != prev:
            self._dirty = True
            self._maybe_flush()

    def tap(self, *buttons: HoripadButton) -> None:
        """Press and immediately release (convenience)."""
        self.press(*buttons)
        self.release(*buttons)

    def release_all(self) -> None:
        """Release every held button, centre sticks and dpad, send neutral."""
        self._buttons = 0
        self._dpad = 0x0F
        self._lx = 0x80
        self._ly = 0x80
        self._rx = 0x80
        self._ry = 0x80
        self._dirty = True
        self._flush()

    def resend(self) -> None:
        """Force-send the current full controller state."""
        self._dirty = True
        self._flush()

    def hold(self, *buttons: HoripadButton) -> _HoldGuard:
        """Context manager: hold *buttons* while executing the block.

        >>> with pad.hold(HoripadButton.A):
        ...     pad.set_stick_left(x=1.0)   # hold A while tilting stick
        """
        return _HoldGuard(self, *buttons)

    # ------------------------------------------------------------------
    # Batch (defer reports)
    # ------------------------------------------------------------------

    def batch(self) -> _BatchGuard:
        """Context manager: defer report until exit.

        >>> with pad.batch():
        ...     pad.press(HoripadButton.A)
        ...     pad.set_dpad(HoripadDpad.UP)
        # sends one report on exit
        """
        return _BatchGuard(self)

    # ------------------------------------------------------------------
    # D-pad
    # ------------------------------------------------------------------

    @property
    def dpad(self) -> HoripadDpad | None:
        """Current d-pad direction, or None if centred."""
        try:
            return HoripadDpad(self._dpad)
        except ValueError:
            return None

    def set_dpad(self, direction: HoripadDpad) -> None:
        """Set the d-pad to *direction* and send a report."""
        self._dpad = int(direction)
        self._dirty = True
        self._maybe_flush()

    def clear_dpad(self) -> None:
        """Return the d-pad to centre (0x0F)."""
        self._dpad = 0x0F
        self._dirty = True
        self._maybe_flush()

    # ------------------------------------------------------------------
    # Sticks — normalised float (-1.0 … 1.0)
    # ------------------------------------------------------------------

    @property
    def stick_left(self) -> tuple[float, float]:
        """Left stick (x, y) as normalised floats (-1.0 … 1.0)."""
        return _stick_to_float(self._lx), _stick_to_float(self._ly)

    @property
    def stick_right(self) -> tuple[float, float]:
        """Right stick (x, y) as normalised floats (-1.0 … 1.0)."""
        return _stick_to_float(self._rx), _stick_to_float(self._ry)

    def set_stick_left(self, *, x: float = 0.0, y: float = 0.0) -> None:
        """Set left stick position (*x*, *y* normalised -1.0 … 1.0)."""
        self._lx = _float_to_stick(x)
        self._ly = _float_to_stick(y)
        self._dirty = True
        self._maybe_flush()

    def set_stick_right(self, *, x: float = 0.0, y: float = 0.0) -> None:
        """Set right stick position (*x*, *y* normalised -1.0 … 1.0)."""
        self._rx = _float_to_stick(x)
        self._ry = _float_to_stick(y)
        self._dirty = True
        self._maybe_flush()

    def centre_sticks(self) -> None:
        """Return both sticks to centre (0x80)."""
        self._lx = 0x80
        self._ly = 0x80
        self._rx = 0x80
        self._ry = 0x80
        self._dirty = True
        self._maybe_flush()

    # ------------------------------------------------------------------
    # Sticks — raw 0x00–0xFF
    # ------------------------------------------------------------------

    @property
    def stick_left_raw(self) -> tuple[int, int]:
        """Left stick (x, y) raw values (0x00–0xFF, 0x80 centre)."""
        return self._lx, self._ly

    @property
    def stick_right_raw(self) -> tuple[int, int]:
        """Right stick (x, y) raw values (0x00–0xFF, 0x80 centre)."""
        return self._rx, self._ry

    def set_stick_left_raw(self, *, x: int = 0x80, y: int = 0x80) -> None:
        """Set left stick raw values (0x00–0xFF, 0x80 centre)."""
        self._lx = _clamp_u8(x)
        self._ly = _clamp_u8(y)
        self._dirty = True
        self._maybe_flush()

    def set_stick_right_raw(self, *, x: int = 0x80, y: int = 0x80) -> None:
        """Set right stick raw values (0x00–0xFF, 0x80 centre)."""
        self._rx = _clamp_u8(x)
        self._ry = _clamp_u8(y)
        self._dirty = True
        self._maybe_flush()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _maybe_flush(self) -> None:
        if not self._batched:
            self._flush()

    def _flush(self) -> None:
        if not self._dirty:
            return
        report = bytes([
            self._buttons & 0xFF,              # byte 0: buttons low
            (self._buttons >> 8) & 0x3F,       # byte 1: buttons high (bits 8-13)
            self._dpad & 0xFF,                 # byte 2: dpad
            self._lx & 0xFF,                   # byte 3: LX
            self._ly & 0xFF,                   # byte 4: LY
            self._rx & 0xFF,                   # byte 5: RX
            self._ry & 0xFF,                   # byte 6: RY
            0x00,                              # byte 7: vendor filler
        ])
        payload = self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
        self._dirty = False


# ---------------------------------------------------------------------------
# Stick conversion helpers
# ---------------------------------------------------------------------------

def _stick_to_float(raw: int) -> float:
    """Convert raw 0x00–0xFF (0x80 centre) to normalised -1.0 … 1.0."""
    if raw >= 0x80:
        return (raw - 0x80) / 127.0
    return (raw - 0x80) / 128.0


def _float_to_stick(v: float) -> int:
    """Convert normalised -1.0 … 1.0 to raw 0x00–0xFF (0x80 centre)."""
    if v < -1.0:
        v = -1.0
    elif v > 1.0:
        v = 1.0
    if v >= 0.0:
        return round(v * 127.0 + 0x80)
    return round(v * 128.0 + 0x80)


def _clamp_u8(v: int) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------


class _HoldGuard:
    def __init__(self, pad: Horipad, *buttons: HoripadButton) -> None:
        self._pad = pad
        self._buttons = buttons

    def __enter__(self) -> Horipad:
        self._pad.press(*self._buttons)
        return self._pad

    def __exit__(self, *_: object) -> None:
        self._pad.release(*self._buttons)


class _BatchGuard:
    def __init__(self, pad: Horipad) -> None:
        self._pad = pad

    def __enter__(self) -> Horipad:
        self._pad._batched = True
        return self._pad

    def __exit__(self, *_: object) -> None:
        self._pad._batched = False
        self._pad._maybe_flush()
