"""Gamepad device (report ID 5, 6-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §4 (Generic Desktop Page 0x01) — Gamepad (Usage ID 0x05)
* HID Usage Tables 1.7 §12 (Button Page 0x09)

Wire format: ``[buttons_low][buttons_high][lx][ly][rx][ry]``

* Buttons: 16-bit bitmap (buttons/high each 1 byte)
* Sticks: absolute unsigned bytes (0=min, 128=center, 255=max)
* D-pad: encoded as 8-directional hat-switch value in buttons_high (bits 4-7)

The report is flagged RELATIVE (at least one axis is relative), so
**reliable delivery is always enabled** (``reliable=True``).
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 5  # REPORT_ID_GAME


class GamepadButton(IntEnum):
    """Standard gamepad buttons (Button Page 0x09)."""

    SOUTH = 1       # A (Nintendo) / Cross (PlayStation) / A (Xbox)
    EAST = 2        # B / Circle / B
    WEST = 3        # X / Square / X
    NORTH = 4       # Y / Triangle / Y
    L1 = 5          # Left shoulder / bumper
    R1 = 6          # Right shoulder / bumper
    L2 = 7          # Left trigger
    R2 = 8          # Right trigger
    SELECT = 9      # Select / - / View
    START = 10      # Start / + / Menu
    L3 = 11         # Left stick click
    R3 = 12         # Right stick click

    def bit(self) -> int:
        """Bitmask in the 16-bit button bitmap (bits 0-7 → byte 0, bits 8-11 → byte 1)."""
        return 1 << (self - 1)


class GamepadDPad(IntEnum):
    """8-directional hat switch (HID Generic Desktop Hat Switch 0x39)."""

    CENTER = 0x0F
    UP = 0
    UP_RIGHT = 1
    RIGHT = 2
    DOWN_RIGHT = 3
    DOWN = 4
    DOWN_LEFT = 5
    LEFT = 6
    UP_LEFT = 7


class Gamepad:
    """6-byte gamepad with dual sticks, 12 buttons, and 8-way D-pad.

    Usage::

        pad = Gamepad(client, ReportTable.universal())

        pad.press(GamepadButton.SOUTH)
        pad.set_stick(left_x=1.0, left_y=0.5)  # right full, centered
        pad.set_dpad(GamepadDPad.UP)
        pad.release_all()

    Stick values are **absolute** (0.0=min, 0.5=center, 1.0=max).
    Every *set_* / *press* / *release* call sends a report immediately.
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # state
        self._buttons: int = 0           # 16-bit button bitmap
        self._lx: int = 128              # left stick X  (0-255, center 128)
        self._ly: int = 128              # left stick Y
        self._rx: int = 128              # right stick X
        self._ry: int = 128              # right stick Y
        self._dpad: int = 0x0F           # hat switch (0-7 active, 0x0F centered)

    # -- state queries -------------------------------------------------------- #

    @property
    def buttons(self) -> int:
        """16-bit button bitmap."""
        return self._buttons

    @property
    def left_stick(self) -> tuple[float, float]:
        """Left stick position as (x, y) in 0.0–1.0."""
        return _byte_to_float(self._lx), _byte_to_float(self._ly)

    @property
    def right_stick(self) -> tuple[float, float]:
        """Right stick position as (x, y) in 0.0–1.0."""
        return _byte_to_float(self._rx), _byte_to_float(self._ry)

    @property
    def dpad(self) -> int:
        """Current D-pad direction (0-7 or 0x0F for center)."""
        return self._dpad

    def is_pressed(self, button: GamepadButton) -> bool:
        """True if *button* is currently held."""
        return bool(self._buttons & button.bit())

    # -- sticks --------------------------------------------------------------- #

    def set_stick(
        self,
        left_x: float | None = None,
        left_y: float | None = None,
        right_x: float | None = None,
        right_y: float | None = None,
    ) -> None:
        """Set one or both stick positions (0.0=min, 0.5=center, 1.0=max).

        Pass *None* to leave an axis unchanged.
        """
        if left_x is None and left_y is None and right_x is None and right_y is None:
            return
        if left_x is not None:
            self._lx = _float_to_byte(left_x)
        if left_y is not None:
            self._ly = _float_to_byte(left_y)
        if right_x is not None:
            self._rx = _float_to_byte(right_x)
        if right_y is not None:
            self._ry = _float_to_byte(right_y)
        self._send()

    # -- dpad ----------------------------------------------------------------- #

    def set_dpad(self, direction: GamepadDPad) -> None:
        """Set the D-pad direction (or CENTER to release)."""
        if self._dpad == direction:
            return
        self._dpad = int(direction)
        self._send()

    # -- buttons -------------------------------------------------------------- #

    def press(self, *buttons: GamepadButton) -> None:
        """Press one or more buttons (held until released)."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons |= b.bit()
        if self._buttons != prev:
            self._send()

    def release(self, *buttons: GamepadButton) -> None:
        """Release one or more buttons."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons &= ~b.bit()
        if self._buttons != prev:
            self._send()

    def click(self, *buttons: GamepadButton) -> None:
        """Press and immediately release."""
        self.press(*buttons)
        self.release(*buttons)

    def release_all(self) -> None:
        """Release all buttons, center sticks and D-pad."""
        if self._buttons == 0 and self._lx == 128 and self._ly == 128 \
           and self._rx == 128 and self._ry == 128 and self._dpad == 0x0F:
            return
        self._buttons = 0
        self._lx = self._ly = self._rx = self._ry = 128
        self._dpad = 0x0F
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        # Pack dpad into buttons_high bits 4-6
        b_low = self._buttons & 0xFF
        b_high = ((self._buttons >> 8) & 0x0F) | ((self._dpad & 0x0F) << 4)

        report = bytes([
            b_low, b_high,
            self._lx & 0xFF, self._ly & 0xFF,
            self._rx & 0xFF, self._ry & 0xFF,
        ])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=True)


def _float_to_byte(v: float) -> int:
    """0.0–1.0 → 0–255, clamped."""
    if v < 0.0:
        v = 0.0
    elif v > 1.0:
        v = 1.0
    return round(v * 255)


def _byte_to_float(b: int) -> float:
    """0–255 → 0.0–1.0."""
    return b / 255.0
