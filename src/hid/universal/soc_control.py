"""SoC firmware update device (report ID 17, 41-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 17, Page 0x0011 (SoC)

FEATURE report used for firmware flashing:
  ``[firmware_id:2][file_offset:4][payload_size:2][payload:32][last:1+pad:7]``
"""

from __future__ import annotations

import struct

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 17


class SoCControl:
    """ESP32-S3 firmware update via FEATURE report (report ID 17).

    Usage::

        soc = SoCControl(client, ReportTable.universal())

        soc.set_firmware_chunk(
            firmware_id=1,
            offset=0,
            payload=b"..." * 16,          # 32 bytes
            is_last=False,
        )
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def set_firmware_chunk(
        self,
        *,
        firmware_id: int = 0,
        offset: int = 0,
        payload: bytes = b"",
        is_last: bool = False,
    ) -> None:
        """Send one 32-byte firmware chunk at *offset*.

        *firmware_id*: file identifier (0-65535)
        *offset*: byte offset in the firmware file (0–2³¹-1)
        *payload*: up to 32 bytes of firmware data (zero-padded)
        *is_last*: set True for the final chunk
        """
        if len(payload) > 32:
            raise ValueError(f"payload exceeds 32 bytes: {len(payload)}")
        # pad payload to exactly 32 bytes
        padded = payload + b"\x00" * (32 - len(payload))

        report = struct.pack(
            "<H I H 32s B",
            firmware_id & 0xFFFF,
            offset & 0xFFFFFFFF,
            len(payload) & 0xFFFF,
            padded,
            1 if is_last else 0,
        )  # 2+4+2+32+1 = 41 bytes
        payload_wire = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload_wire, reliable=True)
