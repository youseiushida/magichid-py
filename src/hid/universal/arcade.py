"""Arcade GPIO device (report ID 33, 2-byte INPUT + 2-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 33, Page 0x0091 (Arcade), General Purpose IO Card

INPUT:  ``[digital_in:1][analog_in:1]`` (8-bit bitmap + u8 analog)
OUTPUT: ``[digital_out:1][coin_lockout:1+pad:7]`` (8-bit bitmap + lockout flag)
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 33

# -- OUTPUT bit --------------------------------------------------------------
_F_COIN_LOCKOUT = 1 << 0


class ArcadeIO:
    """Arcade GPIO I/O card — digital I/O + analog input + coin door lockout.

    Usage::

        io = ArcadeIO(client, ReportTable.universal())

        # send digital + analog input state
        io.set_input(digital=0b10101010, analog=128)

        # set digital output state on the arcade machine
        io.set_output(digital=0xFF, coin_lockout=True)

        # receive output commands from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                io.handle_host_event(ev)
        print(io.host_digital, io.coin_lockout)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # INPUT state
        self._digital_in: int = 0
        self._analog_in: int = 0
        # OUTPUT state (from host)
        self._host_digital: int = 0
        self._coin_lockout: bool = False

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def digital_in(self) -> int:
        """Digital input bitmap (8 bits)."""
        return self._digital_in

    @property
    def analog_in(self) -> int:
        """Analog input value (0–255)."""
        return self._analog_in

    def set_input(self, *, digital: int = 0, analog: int = 0) -> None:
        """Set digital and/or analog input state and send an INPUT report."""
        self._digital_in = digital & 0xFF
        self._analog_in = _clamp_u8(analog)
        self._send_input()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def host_digital(self) -> int:
        """Digital output bitmap (8 bits) from host."""
        return self._host_digital

    @property
    def coin_lockout(self) -> bool:
        """True if host commanded coin door lockout."""
        return self._coin_lockout

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._host_digital = event.data[0] & 0xFF
            self._coin_lockout = bool(event.data[1] & _F_COIN_LOCKOUT)

    # -- internals ------------------------------------------------------------ #

    def _send_input(self) -> None:
        report = bytes([self._digital_in & 0xFF, self._analog_in & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_u8(v: int) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v
