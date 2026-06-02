"""Boot-mouse (5-byte relative report) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §4 (Generic Desktop Page 0x01), §9 (Button Page 0x09)
* HID Device Class Definition, Appendix B (Boot Mouse descriptor)

The boot-mouse report is **relative** — every *move* sends a signed delta.
*Relative reports MUST use reliable delivery* (``reliable=True``), which the
class enables by default.
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import MOUSE, ReportTable
from core.wire import MsgType

from .._client import IHidClient


class MouseButton(IntEnum):
    """HID Button Page (0x09) — wire values map to bit positions in byte 0."""

    LEFT = 1        # Button 1 (primary)
    RIGHT = 2       # Button 2 (secondary)
    MIDDLE = 3      # Button 3
    BACK = 4        # Button 4
    FORWARD = 5     # Button 5

    def bit(self) -> int:
        """Bitmask for the boot-mouse button byte."""
        return 1 << (self - 1)


class Mouse:
    """Boot-mouse (5-byte relative report) with button state tracking.

    Usage::

        mouse = Mouse(client, ReportTable.universal())

        mouse.move(x=10, y=-5)                  # move pointer
        mouse.click(MouseButton.LEFT)           # click
        mouse.scroll(wheel=-1)                  # scroll down

    Drag::

        mouse.press(MouseButton.LEFT)
        mouse.move(x=100, y=0)
        mouse.release(MouseButton.LEFT)

    Or with a context manager::

        with mouse.hold(MouseButton.LEFT):
            mouse.move(x=100, y=0)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._buttons: int = 0  # bitmask of currently held buttons

    # -- state ---------------------------------------------------------------- #

    @property
    def buttons(self) -> int:
        """Current button bitmask."""
        return self._buttons

    def is_pressed(self, button: MouseButton) -> bool:
        """True if *button* is currently held."""
        return bool(self._buttons & button.bit())

    # -- movement ------------------------------------------------------------- #

    def move(self, x: int = 0, y: int = 0) -> None:
        """Send relative X/Y deltas (-128..127, clamped)."""
        self._send(x=_clamp_s8(x), y=_clamp_s8(y))

    def scroll(self, wheel: int = 0, pan: int = 0) -> None:
        """Send vertical (*wheel*) and horizontal (*pan*) scroll deltas."""
        self._send(wheel=_clamp_s8(wheel), pan=_clamp_s8(pan))

    # -- buttons -------------------------------------------------------------- #

    def press(self, *buttons: MouseButton) -> None:
        """Press one or more buttons (held until released)."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons |= b.bit()
        if self._buttons != prev:
            self._send()

    def release(self, *buttons: MouseButton) -> None:
        """Release one or more buttons."""
        if not buttons:
            return
        prev = self._buttons
        for b in buttons:
            self._buttons &= ~b.bit()
        if self._buttons != prev:
            self._send()

    def click(self, *buttons: MouseButton) -> None:
        """Press and immediately release (convenience for single clicks)."""
        self.press(*buttons)
        self.release(*buttons)

    def release_all(self) -> None:
        """Release all held buttons and send an empty report."""
        if self._buttons == 0:
            return
        self._buttons = 0
        self._send()

    # -- drag context --------------------------------------------------------- #

    def hold(self, *buttons: MouseButton) -> _HoldGuard:
        """Context manager: hold *buttons* while executing the block.

        >>> with mouse.hold(MouseButton.LEFT):
        ...     mouse.move(x=100, y=0)   # drag right
        """
        return _HoldGuard(self, *buttons)

    # -- internals ------------------------------------------------------------ #

    def _send(self, x: int = 0, y: int = 0, wheel: int = 0, pan: int = 0) -> None:
        report = bytes([self._buttons & 0xFF, x & 0xFF, y & 0xFF,
                        wheel & 0xFF, pan & 0xFF])
        payload = bytes([MOUSE]) + self._table.pad_input(MOUSE, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=True)


class _HoldGuard:
    def __init__(self, mouse: Mouse, *buttons: MouseButton) -> None:
        self._mouse = mouse
        self._buttons = buttons

    def __enter__(self) -> Mouse:
        self._mouse.press(*self._buttons)
        return self._mouse

    def __exit__(self, *_: object) -> None:
        self._mouse.release(*self._buttons)


def _clamp_s8(v: int) -> int:
    if v < -128:
        return -128
    if v > 127:
        return 127
    return v
