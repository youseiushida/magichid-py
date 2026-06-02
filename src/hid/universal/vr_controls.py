"""VR / Head Mounted Display device (report ID 3, 7-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 3, Page 0x0003 (VR Controls), Head Mounted Display

Fields: ``[rx:2][ry:2][rz:2][stereo:1][display:1][pad:6]``
Rotation axes are s16 LE (-32768..32767).
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 3

_F_STEREO = 1 << 0
_F_DISPLAY = 1 << 1


class VRHeadset:
    """VR Head Mounted Display — 3-axis rotation + stereo/display flags.

    Usage::

        hmd = VRHeadset(client, ReportTable.universal())

        hmd.set(rx=100, ry=-50, rz=0)
        hmd.set(stereo=True, display=True)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._rx: int = 0
        self._ry: int = 0
        self._rz: int = 0
        self._stereo: bool = False
        self._display: bool = False

    # -- state ---------------------------------------------------------------- #

    @property
    def rx(self) -> int:
        return self._rx

    @property
    def ry(self) -> int:
        return self._ry

    @property
    def rz(self) -> int:
        return self._rz

    @property
    def stereo(self) -> bool:
        return self._stereo

    @property
    def display(self) -> bool:
        return self._display

    def set(
        self,
        *,
        rx: int | None = None,
        ry: int | None = None,
        rz: int | None = None,
        stereo: bool | None = None,
        display: bool | None = None,
    ) -> None:
        """Set one or more VR controls and send a report."""
        if rx is not None:
            self._rx = _clamp_s16(rx)
        if ry is not None:
            self._ry = _clamp_s16(ry)
        if rz is not None:
            self._rz = _clamp_s16(rz)
        if stereo is not None:
            self._stereo = stereo
        if display is not None:
            self._display = display
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        flags = 0
        if self._stereo:
            flags |= _F_STEREO
        if self._display:
            flags |= _F_DISPLAY
        report = struct.pack(
            "<hhhB", self._rx, self._ry, self._rz, flags,
        )  # 3 × s16 LE + 1 byte = 7 bytes
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_s16(v: int) -> int:
    if v < -32768:
        return -32768
    if v > 32767:
        return 32767
    return v
