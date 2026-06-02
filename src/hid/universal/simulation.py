"""Flight Simulation device (report ID 2, 11-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 2, Page 0x0002 (Simulation Controls)

Fields: ``[aileron:2][elevator:2][rudder:2][throttle:2][flaps:2][trigger:1+pad:7]``
All axes are signed 16-bit LE (-32768..32767).  Trigger is a single bit.
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 2

_F_TRIGGER = 1 << 0


class FlightSim:
    """Flight simulation controls — aileron, elevator, rudder, throttle, flaps, trigger.

    Usage::

        sim = FlightSim(client, ReportTable.universal())

        sim.set(aileron=100, elevator=-50, rudder=0)
        sim.set(throttle=20000, trigger=True)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._aileron: int = 0
        self._elevator: int = 0
        self._rudder: int = 0
        self._throttle: int = 0
        self._flaps: int = 0
        self._trigger: bool = False

    # -- state ---------------------------------------------------------------- #

    @property
    def aileron(self) -> int:
        return self._aileron

    @property
    def elevator(self) -> int:
        return self._elevator

    @property
    def rudder(self) -> int:
        return self._rudder

    @property
    def throttle(self) -> int:
        return self._throttle

    @property
    def flaps(self) -> int:
        return self._flaps

    @property
    def trigger(self) -> bool:
        return self._trigger

    def set(
        self,
        *,
        aileron: int | None = None,
        elevator: int | None = None,
        rudder: int | None = None,
        throttle: int | None = None,
        flaps: int | None = None,
        trigger: bool | None = None,
    ) -> None:
        """Set one or more flight controls and send a report."""
        if aileron is not None:
            self._aileron = _clamp_s16(aileron)
        if elevator is not None:
            self._elevator = _clamp_s16(elevator)
        if rudder is not None:
            self._rudder = _clamp_s16(rudder)
        if throttle is not None:
            self._throttle = _clamp_s16(throttle)
        if flaps is not None:
            self._flaps = _clamp_s16(flaps)
        if trigger is not None:
            self._trigger = trigger
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        flags = _F_TRIGGER if self._trigger else 0
        report = struct.pack(
            "<hhhhhB",
            self._aileron, self._elevator, self._rudder,
            self._throttle, self._flaps, flags,
        )  # 5 × s16 LE + 1 byte = 11 bytes
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_s16(v: int) -> int:
    if v < -32768:
        return -32768
    if v > 32767:
        return 32767
    return v
