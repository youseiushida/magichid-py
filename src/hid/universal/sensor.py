"""3D Accelerometer sensor device (report ID 20, 7-byte INPUT + 4-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 20, Page 0x0020 (Sensors), Accelerometer 3D

INPUT:   ``[sensor_state:1][x:2][y:2][z:2]`` (u8 + s16 LE × 3)
FEATURE: ``[report_interval:4]`` (u32 LE, ms between reports)
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 20


class Accelerometer:
    """3D Accelerometer — X/Y/Z acceleration + reporting interval.

    Usage::

        accel = Accelerometer(client, ReportTable.universal())

        accel.set(x=100, y=-50, z=9800, sensor_state=1)
        accel.set_interval(100)  # report every 100ms
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._sensor_state: int = 0
        self._x: int = 0
        self._y: int = 0
        self._z: int = 0
        self._interval: int = 0

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def sensor_state(self) -> int:
        """Sensor status flags (0-255)."""
        return self._sensor_state

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    @property
    def z(self) -> int:
        return self._z

    def set(
        self,
        *,
        sensor_state: int | None = None,
        x: int | None = None,
        y: int | None = None,
        z: int | None = None,
    ) -> None:
        """Set acceleration values and/or sensor state, then send a report."""
        if sensor_state is not None:
            self._sensor_state = _clamp_u8(sensor_state)
        if x is not None:
            self._x = _clamp_s16(x)
        if y is not None:
            self._y = _clamp_s16(y)
        if z is not None:
            self._z = _clamp_s16(z)
        self._send_input()

    # -- FEATURE -------------------------------------------------------------- #

    @property
    def interval(self) -> int:
        """Reporting interval in ms (0–2³¹-1)."""
        return self._interval

    def set_interval(self, ms: int) -> None:
        """Set the sensor reporting interval in milliseconds."""
        self._interval = _clamp_u32(ms)
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_input(self) -> None:
        report = struct.pack(
            "<Bhhh", self._sensor_state, self._x, self._y, self._z,
        )  # 1 + 3×2 = 7 bytes
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    def _send_feature(self) -> None:
        report = struct.pack("<I", self._interval)
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _clamp_u8(v: int) -> int:
    return max(0, min(255, v))


def _clamp_s16(v: int) -> int:
    return max(-32768, min(32767, v))


def _clamp_u32(v: int) -> int:
    return max(0, min(2147483647, v))
