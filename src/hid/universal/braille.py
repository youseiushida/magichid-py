"""Braille Display device (report ID 22, 1B INPUT + 8B OUTPUT + 1B FEATURE).

Conforms to:
* universal_reports.yaml — report ID 22, Page 0x0041 (Braille Display)

INPUT:   ``[dot_1..8:8×u1]`` — braille dot key presses
OUTPUT:  ``[cell:8]`` (u8 × 8) — host sends 8 braille cells to display
FEATURE: ``[cell_count:1]`` (u8) — number of braille cells
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 22
_CELLS = 8


class BrailleDisplay:
    """Braille display — dot keys in, cell data out, cell count config.

    Usage::

        brl = BrailleDisplay(client, ReportTable.universal())

        # send dot key state
        brl.set_dots(dot_1=True, dot_3=True)

        # set number of cells
        brl.set_cell_count(40)

        # receive braille cell data from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                brl.handle_host_event(ev)
        print(brl.cells)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._dots: int = 0          # INPUT: bitmap of pressed dots
        self._cells: bytes = b""     # OUTPUT: braille cells from host
        self._cell_count: int = 0    # FEATURE

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def dots(self) -> int:
        """Dot key bitmap (bits 0-7 = dots 1-8)."""
        return self._dots

    def set_dots(self, **dots: bool) -> None:
        """Set braille dot keys.  Pass ``dot_1=True, dot_2=False, ...``."""
        for i in range(1, 9):
            key = f"dot_{i}"
            if key in dots:
                if dots[key]:
                    self._dots |= 1 << (i - 1)
                else:
                    self._dots &= ~(1 << (i - 1))
        if not dots:
            return
        self._send_input()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def cells(self) -> bytes:
        """Last 8 braille cells sent by host (8 bytes)."""
        return self._cells

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            padded = event.data + b"\x00" * (_CELLS - len(event.data))
            self._cells = bytes(padded[:_CELLS])

    # -- FEATURE -------------------------------------------------------------- #

    @property
    def cell_count(self) -> int:
        """Configured number of braille cells."""
        return self._cell_count

    def set_cell_count(self, count: int) -> None:
        """Set the number of braille cells (0-255)."""
        self._cell_count = _clamp_u8(count)
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_input(self) -> None:
        report = bytes([self._dots & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    def _send_feature(self) -> None:
        report = bytes([self._cell_count & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _clamp_u8(v: int) -> int:
    return max(0, min(255, v))
