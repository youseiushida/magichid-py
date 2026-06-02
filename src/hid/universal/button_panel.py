"""Generic 8-button bitmap device (report ID 9) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §12 (Button Page 0x09)

The report is a single byte where each bit maps to one button (1-8).
Not relative — reliable delivery is not required.
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 9  # REPORT_ID_BUTTON


class PanelButton(IntEnum):
    """HID Button Page (0x09) usage IDs 1-8, mapped to bit positions in the report byte."""

    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5 = 5
    B6 = 6
    B7 = 7
    B8 = 8

    def bit(self) -> int:
        """Bitmask in the 1-byte button report."""
        return 1 << (self - 1)


class ButtonPanel:
    """8-button bitmap panel (report ID 9) with button state tracking.

    Usage::

        panel = ButtonPanel(client, ReportTable.universal())

        panel.press(PanelButton.B1, PanelButton.B3)
        panel.click(PanelButton.B2)
        panel.release_all()
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._state: int = 0  # 1-byte bitmap of currently held buttons

    # -- state ---------------------------------------------------------------- #

    @property
    def state(self) -> int:
        """Current button bitmap (bits 0-7)."""
        return self._state

    def is_pressed(self, button: PanelButton) -> bool:
        """True if *button* is currently held."""
        return bool(self._state & button.bit())

    @property
    def pressed_count(self) -> int:
        """Number of buttons currently held."""
        return self._state.bit_count()

    # -- buttons -------------------------------------------------------------- #

    def press(self, *buttons: PanelButton) -> None:
        """Press one or more buttons (held until released)."""
        if not buttons:
            return
        prev = self._state
        for b in buttons:
            self._state |= b.bit()
        if self._state != prev:
            self._send()

    def release(self, *buttons: PanelButton) -> None:
        """Release one or more buttons."""
        if not buttons:
            return
        prev = self._state
        for b in buttons:
            self._state &= ~b.bit()
        if self._state != prev:
            self._send()

    def click(self, *buttons: PanelButton) -> None:
        """Press and immediately release."""
        self.press(*buttons)
        self.release(*buttons)

    def release_all(self) -> None:
        """Release all held buttons and send an empty report."""
        if self._state == 0:
            return
        self._state = 0
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, bytes([self._state]))
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
