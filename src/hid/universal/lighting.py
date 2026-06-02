"""LampArray / Lighting device (report ID 23, 6-byte OUTPUT + 14-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 23, Page 0x0059 (Lighting), LampArray

OUTPUT:  ``[lamp_id:2][red:1][green:1][blue:1][intensity:1]`` — host lamp update
FEATURE: ``[lamp_count:2][width:4][height:4][depth:4]`` — array geometry
"""

from __future__ import annotations

import struct

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 23


class LampArray:
    """HID LampArray — receive per-lamp updates, report array geometry.

    Usage::

        la = LampArray(client, ReportTable.universal())

        # set array geometry
        la.set_geometry(lamp_count=64, width=800, height=600, depth=10)

        # receive lamp updates from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                la.handle_host_event(ev)
        print(la.lamp_id, la.rgb, la.intensity)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # OUTPUT state (from host)
        self._lamp_id: int = 0
        self._red: int = 0
        self._green: int = 0
        self._blue: int = 0
        self._intensity: int = 0
        # FEATURE state
        self._lamp_count: int = 0
        self._width: int = 0
        self._height: int = 0
        self._depth: int = 0

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def lamp_id(self) -> int:
        return self._lamp_id

    @property
    def rgb(self) -> tuple[int, int, int]:
        return self._red, self._green, self._blue

    @property
    def intensity(self) -> int:
        return self._intensity

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and len(event.data) >= 6
        ):
            self._lamp_id = event.data[0] | (event.data[1] << 8)
            self._red = event.data[2] & 0xFF
            self._green = event.data[3] & 0xFF
            self._blue = event.data[4] & 0xFF
            self._intensity = event.data[5] & 0xFF

    # -- FEATURE -------------------------------------------------------------- #

    @property
    def lamp_count(self) -> int:
        return self._lamp_count

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def depth(self) -> int:
        return self._depth

    def set_geometry(
        self,
        *,
        lamp_count: int = 0,
        width: int = 0,
        height: int = 0,
        depth: int = 0,
    ) -> None:
        """Set lamp array geometry and send a FEATURE report."""
        self._lamp_count = lamp_count & 0xFFFF
        self._width = width & 0xFFFFFFFF
        self._height = height & 0xFFFFFFFF
        self._depth = depth & 0xFFFFFFFF
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_feature(self) -> None:
        report = struct.pack(
            "<HIII",
            self._lamp_count, self._width, self._height, self._depth,
        )  # 2+4+4+4 = 14 bytes
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)
