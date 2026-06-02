"""FIDO/U2F authenticator pipe (report ID 35, 64-byte INPUT + 64-byte OUTPUT).

Conforms to:
* FIDO Alliance CTAP over HID (Usage Page 0xF1D0)

Bidirectional 64-byte packet pipe:
* ``send(data)`` — send INPUT report (authenticator → host response)
* ``handle_host_event(ev)`` — receive OUTPUT report (host → authenticator command)

Not relative — reliable delivery is not required (CTAP has its own reliability).
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 35  # REPORT_ID_FIDO


class FIDO:
    """FIDO/U2F authenticator 64-byte packet pipe (report ID 35).

    Usage::

        fido = FIDO(client, ReportTable.universal())

        # receive a host command
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                data = fido.handle_host_event(ev)
                if data is not None:
                    # process CTAP command in *data*, build response
                    response = process_ctap_command(data)
                    fido.send(response)

        # or send unsolicited (e.g. keepalive)
        fido.send(b"\\x00" * 64)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    # -- send (authenticator → host) ------------------------------------------ #

    def send(self, data: bytes) -> None:
        """Send a 64-byte INPUT report (authenticator response to host).

        *data* is zero-padded to exactly 64 bytes.
        Raises :class:`ValueError` if *data* exceeds 64 bytes.
        """
        report = _to_64(data)
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    # -- receive (host → authenticator) --------------------------------------- #

    def handle_host_event(self, event: HostEventReceived) -> bytes | None:
        """Extract FIDO command data from a :class:`HostEventReceived`.

        Returns the 64-byte OUTPUT report payload, or *None* if *event*
        is not a FIDO OUTPUT report.
        """
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
        ):
            return _to_64(event.data)
        return None


def _to_64(data: bytes) -> bytes:
    """Pad to exactly 64 bytes.  Raises :class:`ValueError` if *data* exceeds 64."""
    if len(data) > 64:
        raise ValueError(f"FIDO data exceeds 64 bytes: {len(data)}")
    return data + b"\x00" * (64 - len(data))
