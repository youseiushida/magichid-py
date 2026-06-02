"""3D Game Controller device (report ID 5, 6-byte, relative) on top of an :class:`IHidClient`.

Conforms to:
* universal_reports.yaml — report ID 5, Page 0x0005 (Game Controls), 3D Game Controller

Wire format: 6 signed 8-bit relative axes (deltas).

Fields: ``[turn_r_l][pitch_fwd_back][roll_r_l][move_r_l][move_fwd_back][move_up_down]``

Relative deltas — **reliable delivery is required** (``reliable=True``).
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 5


class Gamepad:
    """3D Game Controller — 6-axis relative movement (report ID 5).

    Usage::

        ctl = Gamepad(client, ReportTable.universal())

        ctl.turn(10)           # yaw right
        ctl.pitch(-5)          # pitch backward
        ctl.roll(3)            # roll right
        ctl.move(right=5, forward=10, up=-2)

        ctl.reset()            # send all-zero report

    All axis values are signed 8-bit deltas (-127..127).
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._axes: list[int] = [0] * 6  # turn, pitch, roll, move_rl, move_fb, move_ud

    # -- movement ------------------------------------------------------------- #

    def turn(self, delta: int) -> None:
        """Yaw (turn right-left)."""
        self._axes[0] = _clamp_s8(delta)
        self._send()

    def pitch(self, delta: int) -> None:
        """Pitch forward-backward."""
        self._axes[1] = _clamp_s8(delta)
        self._send()

    def roll(self, delta: int) -> None:
        """Roll right-left."""
        self._axes[2] = _clamp_s8(delta)
        self._send()

    def move(self, *, right: int = 0, forward: int = 0, up: int = 0) -> None:
        """Slide along world axes (right/forward/up deltas)."""
        self._axes[3] = _clamp_s8(right)
        self._axes[4] = _clamp_s8(forward)
        self._axes[5] = _clamp_s8(up)
        self._send()

    def reset(self) -> None:
        """Send all-zero report (no movement)."""
        self._axes = [0] * 6
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = bytes([a & 0xFF for a in self._axes])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=True)


def _clamp_s8(v: int) -> int:
    if v < -127:
        return -127
    if v > 127:
        return 127
    return v
