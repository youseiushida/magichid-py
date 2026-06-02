"""SoC configuration device (report ID 17, 41-byte FEATURE) on top of an :class:`IHidClient`.

FEATURE-only report — no INPUT or OUTPUT.  Used to read/write ESP32-S3 SoC
configuration (GPIO, clocks, peripherals, etc.) via :meth:`set_feature`.

Wire format: 41 bytes of raw feature data.  Shorter data is zero-padded.
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 17  # REPORT_ID_SOC
_FEAT_LEN = 41


class SoCControl:
    """ESP32-S3 SoC configuration via FEATURE report (report ID 17).

    Usage::

        soc = SoCControl(client, ReportTable.universal())
        soc.set_feature(bytes([0x01, 0x02, ...]))  # up to 41 bytes
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def set_feature(self, data: bytes) -> None:
        """Write *data* (up to 41 bytes) to the SoC feature report.

        Shorter data is zero-padded to ``feat_len``.
        """
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, data)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)
