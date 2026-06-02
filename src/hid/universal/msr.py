"""Magnetic Stripe Reader device (report ID 31, 229-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 31, Page 0x008E (Magnetic Stripe Reader)

INPUT: ``[t1_len:1][t2_len:1][t3_len:1][t1_data:79][t2_data:40][t3_data:107]``

Three ISO magnetic stripe tracks with length headers.
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 31

_T1_LEN = 79
_T2_LEN = 40
_T3_LEN = 107


class MSR:
    """Magnetic Stripe Reader — send track data from a card swipe.

    Usage::

        msr = MSR(client, ReportTable.universal())

        msr.send(
            track1=b"%B1234567890123456^DOE/JOHN^01011010000000?",
            track2=b";1234567890123456=01011010000000?",
        )
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def send(
        self,
        *,
        track1: bytes = b"",
        track2: bytes = b"",
        track3: bytes = b"",
    ) -> None:
        """Send magnetic stripe data.  Each track is zero-padded to its max length.

        Track 1: up to 79 bytes
        Track 2: up to 40 bytes
        Track 3: up to 107 bytes
        """
        if len(track1) > _T1_LEN:
            raise ValueError(f"track1 exceeds {_T1_LEN} bytes: {len(track1)}")
        if len(track2) > _T2_LEN:
            raise ValueError(f"track2 exceeds {_T2_LEN} bytes: {len(track2)}")
        if len(track3) > _T3_LEN:
            raise ValueError(f"track3 exceeds {_T3_LEN} bytes: {len(track3)}")

        report = bytes([
            len(track1) & 0xFF,
            len(track2) & 0xFF,
            len(track3) & 0xFF,
        ])
        report += _pad(track1, _T1_LEN)
        report += _pad(track2, _T2_LEN)
        report += _pad(track3, _T3_LEN)

        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _pad(data: bytes, length: int) -> bytes:
    return data + b"\x00" * (length - len(data))
