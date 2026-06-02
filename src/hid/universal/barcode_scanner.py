"""Barcode Scanner device (report ID 29, 33B INPUT + 1B OUTPUT + 1B FEATURE).

Conforms to:
* universal_reports.yaml — report ID 29, Page 0x008C (Barcode Scanner)

INPUT:  ``[trigger_state:1+pad:7][decoded_data:32]`` (flag + u8 array)
OUTPUT: ``[initiate_read:1+pad:7]`` — host triggers a scan
FEATURE: ``[aiming_pointer:1+pad:7]`` — aiming pointer mode config
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 29
_DATA_LEN = 32

# -- flag bits ---------------------------------------------------------------
_F_TRIGGER = 1 << 0
_F_SCAN = 1 << 0
_F_AIMING = 1 << 0


class BarcodeScanner:
    """Barcode scanner — decoded data output + scan trigger input.

    Usage::

        scanner = BarcodeScanner(client, ReportTable.universal())

        # send a barcode read result
        scanner.send(b"4901234567890")      # UPC barcode
        scanner.send(b"", triggered=False)   # no data, not triggered

        # receive scan commands from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                scanner.handle_host_event(ev)
        if scanner.scan_requested:
            ...

        # configure aiming pointer mode
        scanner.set_aiming_pointer(True)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # INPUT state
        self._triggered: bool = False
        self._data: bytes = b""
        # OUTPUT state (from host)
        self._scan_requested: bool = False
        # FEATURE state
        self._aiming_pointer: bool = False

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def triggered(self) -> bool:
        """True if the last-sent data was acquired via a physical trigger pull."""
        return self._triggered

    @property
    def data(self) -> bytes:
        """Last-sent decoded barcode data (up to 32 bytes)."""
        return self._data

    def send(self, data: bytes, *, triggered: bool = True) -> None:
        """Send decoded barcode *data* (up to 32 bytes, zero-padded).

        *triggered* indicates whether the read was initiated by a physical
        trigger pull (True) or auto-sense / software (False).
        """
        if len(data) > _DATA_LEN:
            raise ValueError(f"barcode data exceeds {_DATA_LEN} bytes: {len(data)}")
        self._triggered = triggered
        self._data = data
        self._send_input()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def scan_requested(self) -> bool:
        """True if the host sent an initiate-barcode-read command."""
        return self._scan_requested

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._scan_requested = bool(event.data[0] & _F_SCAN)

    # -- FEATURE -------------------------------------------------------------- #

    def set_aiming_pointer(self, on: bool) -> None:
        """Enable or disable the aiming pointer (laser dot / LED frame)."""
        self._aiming_pointer = on
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_input(self) -> None:
        flags = _F_TRIGGER if self._triggered else 0
        padded = self._data + b"\x00" * (_DATA_LEN - len(self._data))
        report = bytes([flags & 0xFF]) + padded
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)

    def _send_feature(self) -> None:
        report = bytes([_F_AIMING if self._aiming_pointer else 0])
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)
