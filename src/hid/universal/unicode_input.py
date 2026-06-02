"""Unicode text input device (report ID 16, 12-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §17 (Unicode Page 0x10)

Wire format: 6 UTF-16LE code units (= 12 bytes).  Unused slots are 0x0000.
Characters beyond the Basic Multilingual Plane are encoded as surrogate pairs.

Not relative — reliable delivery is not required.
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 16  # REPORT_ID_UNICODE
_MAX_CHARS = 6    # UTF-16 code units per report


class UnicodeInput:
    """Direct Unicode text input — send code points, host receives as typed text.

    Usage::

        uni = UnicodeInput(client, ReportTable.universal())

        uni.type("Hello")         # 5 chars = 5 code units → 1 report
        uni.type("Hello world")   # 11 chars → 2 reports (6 + 5)
        uni.type("🎉")            # surrogate pair → 2 code units, 1 report

    Each report holds up to 6 UTF-16 code units (12 bytes).
    Long strings are split across multiple reports automatically.
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    # -- type ----------------------------------------------------------------- #

    def type(self, text: str) -> None:
        """Send *text* as one or more Unicode input reports.

        The string is encoded as UTF-16LE and split into 6-code-unit chunks.
        """
        if not text:
            return
        encoded = text.encode("utf-16-le")
        # encoded = N code units × 2 bytes each

        for i in range(0, len(encoded), _MAX_CHARS * 2):
            chunk = encoded[i:i + _MAX_CHARS * 2]
            self._send(chunk)

    # -- internals ------------------------------------------------------------ #

    def _send(self, code_units: bytes) -> None:
        # Pad to 12 bytes with zeros
        report = code_units + b"\x00" * (12 - len(code_units))
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
