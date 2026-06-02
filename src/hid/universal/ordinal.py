"""Ordinal device (report ID 10, 4-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 10, Page 0x000A (Ordinal), Instance 1

INPUT: ``[instance_1:1][instance_2:1][instance_3:1][instance_4:1]`` (u8 × 4)
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 10


class Ordinal:
    """Ordinal instance values — 4 generic u8 channels.

    Usage::

        ord = Ordinal(client, ReportTable.universal())

        ord.set(instance_1=10, instance_2=20)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._values: list[int] = [0] * 4

    # -- state ---------------------------------------------------------------- #

    @property
    def instance_1(self) -> int:
        return self._values[0]

    @property
    def instance_2(self) -> int:
        return self._values[1]

    @property
    def instance_3(self) -> int:
        return self._values[2]

    @property
    def instance_4(self) -> int:
        return self._values[3]

    def set(
        self,
        *,
        instance_1: int | None = None,
        instance_2: int | None = None,
        instance_3: int | None = None,
        instance_4: int | None = None,
    ) -> None:
        """Set one or more ordinal values and send a report."""
        vals = [
            instance_1, instance_2, instance_3, instance_4,
        ]
        for i, v in enumerate(vals):
            if v is not None:
                self._values[i] = _clamp_u8(v)
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = bytes([v & 0xFF for v in self._values])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_u8(v: int) -> int:
    return max(0, min(255, v))
