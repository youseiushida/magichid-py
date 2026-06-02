"""Battery System device (report ID 28, 10-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 28, Page 0x0085 (Battery System)

INPUT: ``[remaining:2][full:2][runtime:2][cycles:2][charge_pct:1][charging:1][discharging:1][ac:1][pad:5]``

OS WARNING: Same as UPS — report healthy state or stay silent.
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 28

_F_CHARGING = 1 << 0
_F_DISCHARGING = 1 << 1
_F_AC_PRESENT = 1 << 2


class BatterySystem:
    """Battery system — capacity, runtime, cycles, charging status.

    Usage::

        bat = BatterySystem(client, ReportTable.universal())

        bat.set(
            remaining_capacity=4000, full_charge_capacity=5000,
            run_time_to_empty=7200, cycle_count=150,
            state_of_charge=80, charging=True, ac_present=True,
        )
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._remaining: int = 0
        self._full: int = 0
        self._runtime: int = 0
        self._cycles: int = 0
        self._charge_pct: int = 0
        self._charging: bool = False
        self._discharging: bool = False
        self._ac_present: bool = False

    # -- state ---------------------------------------------------------------- #

    @property
    def remaining_capacity(self) -> int:
        return self._remaining

    @property
    def full_charge_capacity(self) -> int:
        return self._full

    @property
    def run_time_to_empty(self) -> int:
        return self._runtime

    @property
    def cycle_count(self) -> int:
        return self._cycles

    @property
    def state_of_charge(self) -> int:
        return self._charge_pct

    @property
    def charging(self) -> bool:
        return self._charging

    @property
    def discharging(self) -> bool:
        return self._discharging

    @property
    def ac_present(self) -> bool:
        return self._ac_present

    def set(
        self,
        *,
        remaining_capacity: int | None = None,
        full_charge_capacity: int | None = None,
        run_time_to_empty: int | None = None,
        cycle_count: int | None = None,
        state_of_charge: int | None = None,
        charging: bool | None = None,
        discharging: bool | None = None,
        ac_present: bool | None = None,
    ) -> None:
        if remaining_capacity is not None:
            self._remaining = _u16(remaining_capacity)
        if full_charge_capacity is not None:
            self._full = _u16(full_charge_capacity)
        if run_time_to_empty is not None:
            self._runtime = _u16(run_time_to_empty)
        if cycle_count is not None:
            self._cycles = _u16(cycle_count)
        if state_of_charge is not None:
            self._charge_pct = max(0, min(100, state_of_charge))
        if charging is not None:
            self._charging = charging
        if discharging is not None:
            self._discharging = discharging
        if ac_present is not None:
            self._ac_present = ac_present
        self._send()

    def _send(self) -> None:
        flags = 0
        if self._charging:
            flags |= _F_CHARGING
        if self._discharging:
            flags |= _F_DISCHARGING
        if self._ac_present:
            flags |= _F_AC_PRESENT
        report = struct.pack(
            "<HHHHBB",
            self._remaining, self._full, self._runtime, self._cycles,
            self._charge_pct, flags,
        )  # 4×2 + 1 + 1 = 10 bytes
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _u16(v: int) -> int:
    return max(0, min(65535, v))
