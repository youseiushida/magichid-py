"""Monitor Control device (report ID 24, 130-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 24, Page 0x0080 (Monitor), Monitor Control

FEATURE report for Extended Display Identification Data (EDID):
  ``[edid:128][vesa_version:2]`` (u8 array + u16 LE)

FEATURE-only — no INPUT or OUTPUT.
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 24
_EDID_LEN = 128


class Monitor:
    """Monitor EDID / VESA version via FEATURE report (report ID 24).

    Usage::

        mon = Monitor(client, ReportTable.universal())

        mon.set_edid(edid_bytes)           # 128 bytes of EDID data
        mon.set_vesa_version(0x0103)       # VESA MCCS version 1.03

        # or set both at once
        mon.set(edid=edid_bytes, vesa_version=0x0103)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def set_edid(self, data: bytes) -> None:
        """Write EDID data (up to 128 bytes, zero-padded)."""
        if len(data) > _EDID_LEN:
            raise ValueError(f"EDID data exceeds {_EDID_LEN} bytes: {len(data)}")
        report = _pad(data, _EDID_LEN) + b"\x00\x00"
        self._send(report)

    def set_vesa_version(self, version: int) -> None:
        """Write VESA MCCS version (16-bit value)."""
        report = b"\x00" * _EDID_LEN + struct.pack("<H", version & 0xFFFF)
        self._send(report)

    def set(self, *, edid: bytes | None = None, vesa_version: int | None = None) -> None:
        """Write EDID and/or VESA version.  *None* means keep unchanged."""
        if edid is None and vesa_version is None:
            return
        if edid is not None:
            if len(edid) > _EDID_LEN:
                raise ValueError(f"EDID data exceeds {_EDID_LEN} bytes: {len(edid)}")
        report = (_pad(edid, _EDID_LEN) if edid is not None else b"\x00" * _EDID_LEN) \
                 + struct.pack("<H", (vesa_version & 0xFFFF) if vesa_version is not None else 0)
        self._send(report)

    def _send(self, report: bytes) -> None:
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _pad(data: bytes, length: int) -> bytes:
    return data + b"\x00" * (length - len(data))
