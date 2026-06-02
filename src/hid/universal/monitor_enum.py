"""Monitor Enumerated device (report ID 25, 1-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 25, Page 0x0081 (Monitor Enumerated)

FEATURE: ``[usage:1]`` (u8, 1-16) — enumerated monitor control
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 25


class MonitorEnum:
    """Enumerated monitor control — select a monitor control usage (1-16).

    Usage::

        me = MonitorEnum(client, ReportTable.universal())

        me.set(3)  # select usage 3
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._usage: int = 0

    @property
    def usage(self) -> int:
        return self._usage

    def set(self, usage: int) -> None:
        """Set the enumerated usage (1-16)."""
        self._usage = max(1, min(16, usage))
        self._send()

    def _send(self) -> None:
        report = bytes([self._usage & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)
