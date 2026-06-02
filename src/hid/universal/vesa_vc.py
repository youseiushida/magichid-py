"""VESA Virtual Controls device (report ID 26, 1-byte OUTPUT + 10-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 26, Page 0x0082 (VESA Virtual Controls)

OUTPUT: ``[degauss:1+pad:7]`` — degauss command from host
FEATURE: ``[brightness:2][contrast:2][red:2][green:2][blue:2]`` (u16 LE × 5)

FEATURE values are VCP op-codes (0–65535).
"""

from __future__ import annotations

import struct

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 26

# -- OUTPUT bit --------------------------------------------------------------
_F_DEGAUSS = 1 << 0


class VESAVC:
    """VESA Virtual Control Panel — brightness, contrast, RGB gain, degauss.

    Usage::

        vc = VESAVC(client, ReportTable.universal())

        vc.set(brightness=32768, contrast=32768)
        vc.set(red_gain=65535)

        # receive degauss command from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                vc.handle_host_event(ev)
        if vc.degauss_requested:
            ...
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # FEATURE state
        self._brightness: int = 0
        self._contrast: int = 0
        self._red_gain: int = 0
        self._green_gain: int = 0
        self._blue_gain: int = 0
        # OUTPUT state (from host)
        self._degauss: bool = False

    # -- FEATURE state -------------------------------------------------------- #

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def contrast(self) -> int:
        return self._contrast

    @property
    def red_gain(self) -> int:
        return self._red_gain

    @property
    def green_gain(self) -> int:
        return self._green_gain

    @property
    def blue_gain(self) -> int:
        return self._blue_gain

    def set(
        self,
        *,
        brightness: int | None = None,
        contrast: int | None = None,
        red_gain: int | None = None,
        green_gain: int | None = None,
        blue_gain: int | None = None,
    ) -> None:
        """Update one or more VCP values and send a FEATURE report."""
        if brightness is not None:
            self._brightness = _clamp_u16(brightness)
        if contrast is not None:
            self._contrast = _clamp_u16(contrast)
        if red_gain is not None:
            self._red_gain = _clamp_u16(red_gain)
        if green_gain is not None:
            self._green_gain = _clamp_u16(green_gain)
        if blue_gain is not None:
            self._blue_gain = _clamp_u16(blue_gain)
        self._send_feature()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def degauss_requested(self) -> bool:
        """True if the host sent a degauss command."""
        return self._degauss

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._degauss = bool(event.data[0] & _F_DEGAUSS)

    # -- internals ------------------------------------------------------------ #

    def _send_feature(self) -> None:
        report = struct.pack(
            "<HHHHH",
            self._brightness & 0xFFFF,
            self._contrast & 0xFFFF,
            self._red_gain & 0xFFFF,
            self._green_gain & 0xFFFF,
            self._blue_gain & 0xFFFF,
        )
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _clamp_u16(v: int) -> int:
    if v < 0:
        return 0
    if v > 65535:
        return 65535
    return v
