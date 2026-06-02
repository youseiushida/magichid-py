"""Generic Device Controls (report ID 6, 4-byte INPUT + 4-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 6, Page 0x0006 (Generic Device Controls)

INPUT:   ``[battery:1][wireless_ch:1][rf_signal:1][seq_id:1]`` (u8 × 4)
FEATURE: ``[wireless_id:4]`` (u32 LE)
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 6


class GenericDevice:
    """Background device controls — battery, wireless, RF signal, sequence ID.

    Usage::

        gd = GenericDevice(client, ReportTable.universal())

        gd.set(battery_strength=80, wireless_channel=3, rf_signal=200, sequence_id=1)
        gd.set_wireless_id(0x12345678)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._battery: int = 0
        self._channel: int = 0
        self._rf_signal: int = 0
        self._seq_id: int = 0
        self._wireless_id: int = 0

    @property
    def battery_strength(self) -> int:
        return self._battery

    @property
    def wireless_channel(self) -> int:
        return self._channel

    @property
    def rf_signal(self) -> int:
        return self._rf_signal

    @property
    def sequence_id(self) -> int:
        return self._seq_id

    @property
    def wireless_id(self) -> int:
        return self._wireless_id

    def set(
        self,
        *,
        battery_strength: int | None = None,
        wireless_channel: int | None = None,
        rf_signal: int | None = None,
        sequence_id: int | None = None,
    ) -> None:
        if battery_strength is not None:
            self._battery = _u8(battery_strength)
        if wireless_channel is not None:
            self._channel = _u8(wireless_channel)
        if rf_signal is not None:
            self._rf_signal = _u8(rf_signal)
        if sequence_id is not None:
            self._seq_id = _u8(sequence_id)
        self._send_input()

    def set_wireless_id(self, wid: int) -> None:
        self._wireless_id = _u32(wid)
        self._send_feature()

    def _send_input(self) -> None:
        report = bytes([self._battery, self._channel, self._rf_signal, self._seq_id])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    def _send_feature(self) -> None:
        report = struct.pack("<I", self._wireless_id)
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _u8(v: int) -> int:
    return max(0, min(255, v))


def _u32(v: int) -> int:
    return max(0, min(2147483647, v))
