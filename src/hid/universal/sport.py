"""Golf Club / Sport Controls device (report ID 4, 8-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 4, Page 0x0004 (Sport Controls), Golf Club

Fields: ``[speed:2][face_angle:2][heel_toe:2][tempo:2]``  (all s16 LE)
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 4


class GolfClub:
    """Golf club swing analysis — speed, face angle, heel/toe, tempo.

    Usage::

        club = GolfClub(client, ReportTable.universal())

        club.set(speed=12000, face_angle=-200, heel_toe=50, tempo=8000)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._speed: int = 0
        self._face_angle: int = 0
        self._heel_toe: int = 0
        self._tempo: int = 0

    # -- state ---------------------------------------------------------------- #

    @property
    def speed(self) -> int:
        return self._speed

    @property
    def face_angle(self) -> int:
        return self._face_angle

    @property
    def heel_toe(self) -> int:
        return self._heel_toe

    @property
    def tempo(self) -> int:
        return self._tempo

    def set(
        self,
        *,
        speed: int | None = None,
        face_angle: int | None = None,
        heel_toe: int | None = None,
        tempo: int | None = None,
    ) -> None:
        """Set one or more golf club metrics and send a report."""
        if speed is not None:
            self._speed = _clamp_s16(speed)
        if face_angle is not None:
            self._face_angle = _clamp_s16(face_angle)
        if heel_toe is not None:
            self._heel_toe = _clamp_s16(heel_toe)
        if tempo is not None:
            self._tempo = _clamp_s16(tempo)
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = struct.pack(
            "<hhhh", self._speed, self._face_angle, self._heel_toe, self._tempo,
        )
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_s16(v: int) -> int:
    if v < -32768:
        return -32768
    if v > 32767:
        return 32767
    return v
