"""Gaming Device (GSA) pipe (report ID 34, 8-byte INPUT + 8-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 34, Page 0x0092 (Gaming Device), GSA-defined 0x01

Bidirectional 8-byte raw pipe for gaming machine protocols (GSA/IGSA).
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 34
_PAYLOAD_LEN = 8


class GamingDevice:
    """GSA gaming device 8-byte bidirectional pipe (report ID 34).

    Usage::

        gd = GamingDevice(client, ReportTable.universal())

        # send data to host
        gd.send(bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]))

        # receive commands from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                data = gd.handle_host_event(ev)
                if data is not None:
                    ...
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def send(self, data: bytes) -> None:
        """Send an 8-byte INPUT report.

        *data* is zero-padded to exactly 8 bytes.
        Raises :class:`ValueError` if *data* exceeds 8 bytes.
        """
        if len(data) > _PAYLOAD_LEN:
            raise ValueError(f"data exceeds {_PAYLOAD_LEN} bytes: {len(data)}")
        report = data + b"\x00" * (_PAYLOAD_LEN - len(data))
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    def handle_host_event(self, event: HostEventReceived) -> bytes | None:
        """Extract 8-byte OUTPUT report payload from *event*.

        Returns *None* if *event* is not a Gaming Device OUTPUT report.
        """
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
        ):
            padded = event.data + b"\x00" * (_PAYLOAD_LEN - len(event.data))
            return bytes(padded[:_PAYLOAD_LEN])
        return None
