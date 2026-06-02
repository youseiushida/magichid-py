"""Auxiliary (Alphanumeric) Display device (report ID 19, 16B OUTPUT + 2B FEATURE).

Conforms to:
* universal_reports.yaml — report ID 19, Page 0x0014 (Auxiliary Display)

OUTPUT:  ``[display_data:16]`` (u8 array — text sent by host to show on panel)
FEATURE: ``[brightness:1][contrast:1]`` (u8, 0–100 each)
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 19
_DISPLAY_LEN = 16


class AuxDisplay:
    """Alphanumeric display panel — receive text from host, set brightness/contrast.

    Usage::

        disp = AuxDisplay(client, ReportTable.universal())

        # set brightness / contrast
        disp.set(brightness=80, contrast=50)

        # receive display text from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                disp.handle_host_event(ev)
        print(disp.text)  # bytes sent by host for display
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # OUTPUT state (from host)
        self._text: bytes = b""
        # FEATURE state
        self._brightness: int = 0
        self._contrast: int = 0

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def text(self) -> bytes:
        """Last 16-byte display text sent by the host."""
        return self._text

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            padded = event.data + b"\x00" * (_DISPLAY_LEN - len(event.data))
            self._text = bytes(padded[:_DISPLAY_LEN])

    # -- FEATURE -------------------------------------------------------------- #

    @property
    def brightness(self) -> int:
        """Display brightness (0–100)."""
        return self._brightness

    @property
    def contrast(self) -> int:
        """Display contrast (0–100)."""
        return self._contrast

    def set(self, *, brightness: int | None = None, contrast: int | None = None) -> None:
        """Set display brightness and/or contrast (0–100)."""
        if brightness is not None:
            self._brightness = _clamp(brightness, 0, 100)
        if contrast is not None:
            self._contrast = _clamp(contrast, 0, 100)
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_feature(self) -> None:
        report = bytes([self._brightness & 0xFF, self._contrast & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
