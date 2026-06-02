"""Eye / Head Tracker device (report ID 18, 8-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 18, Page 0x0012 (Eye and Head Trackers)

INPUT: ``[timestamp:4][x:2][y:2]`` (u32 LE + s16 LE × 2)
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 18


class EyeTracker:
    """Eye/head tracker — timestamp + 2D gaze position.

    Usage::

        et = EyeTracker(client, ReportTable.universal())

        et.set(timestamp=12345678, x=100, y=-50)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._timestamp: int = 0
        self._x: int = 0
        self._y: int = 0

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    def set(
        self,
        *,
        timestamp: int | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        if timestamp is not None:
            self._timestamp = _u32(timestamp)
        if x is not None:
            self._x = _s16(x)
        if y is not None:
            self._y = _s16(y)
        self._send()

    def _send(self) -> None:
        report = struct.pack("<Ihh", self._timestamp, self._x, self._y)
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _u32(v: int) -> int:
    return max(0, min(2147483647, v))


def _s16(v: int) -> int:
    return max(-32768, min(32767, v))
