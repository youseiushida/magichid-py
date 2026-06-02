"""Physical Input Device / Force Feedback (report ID 15, 4-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 15, Page 0x000F (PID), Physical Input Device

OUTPUT: ``[effect_type:1][duration:2][gain:1]``
  effect_type: 1=constant force, 2=ramp, 3=square (1-3)
  duration: u16 LE, 0–32767 (ms)
  gain: u8, 0–255
"""

from __future__ import annotations

import struct

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType

from .._client import IHidClient

_REPORT_ID = 15


class PID:
    """Physical Input Device — force feedback receiver (report ID 15).

    Usage::

        pid = PID(client, ReportTable.universal())

        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                result = pid.handle_host_event(ev)
                if result is not None:
                    effect_type, duration, gain = result
                    ...
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._effect_type: int = 0
        self._duration: int = 0
        self._gain: int = 0

    # -- state (from host) ---------------------------------------------------- #

    @property
    def effect_type(self) -> int:
        return self._effect_type

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def gain(self) -> int:
        return self._gain

    def handle_host_event(self, event: HostEventReceived) -> tuple[int, int, int] | None:
        """Extract force-feedback parameters from *event*.

        Returns ``(effect_type, duration, gain)`` or *None* if not a PID event.
        """
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and len(event.data) >= 4
        ):
            self._effect_type = _clamp(event.data[0], 1, 3)
            self._duration = event.data[1] | (event.data[2] << 8)
            self._gain = event.data[3] & 0xFF
            return self._effect_type, self._duration, self._gain
        return None


def _clamp(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
