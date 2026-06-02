"""UPS (Uninterruptible Power Supply) device (report ID 27, 8-byte INPUT + 1-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 27, Page 0x0084 (Power), UPS

Wire format:
  INPUT:  ``[voltage:2][current:2][frequency:2][percent_load:2]`` (all u16 LE)
  OUTPUT: ``[flags]`` — bit 0=switch_on, bit 1=switch_off, bits 2-7=padding

OS WARNING: A host (esp. Windows) may bind this as a system UPS.
Send safe values (load=0, voltage=nominal) or the OS may show battery warnings.
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 27

# -- OUTPUT flag bits ---------------------------------------------------------
_O_SWITCH_ON = 1 << 0
_O_SWITCH_OFF = 1 << 1


def _clamp_u16(v: int) -> int:
    if v < 0:
        return 0
    if v > 65535:
        return 65535
    return v


class UPS:
    """UPS power device (report ID 27) — voltage, current, frequency, load.

    Usage::

        ups = UPS(client, ReportTable.universal())

        ups.set(voltage=100000, frequency=60)   # 100V, 60Hz
        ups.set(percent_load=45)

        # receive host power-control commands
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                ups.handle_host_event(ev)

    All INPUT values are unsigned 16-bit (0-65535).
    ``voltage`` / ``current`` are in device-specific units (typically mV / mA).
    ``frequency`` is in Hz × 10 (e.g. 600 = 60.0 Hz).
    ``percent_load`` is 0-10000 (0.00%-100.00%, in 0.01% steps).
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._voltage: int = 0
        self._current: int = 0
        self._frequency: int = 0
        self._percent_load: int = 0
        # host control
        self._switch_on: bool = False
        self._switch_off: bool = False

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def voltage(self) -> int:
        return self._voltage

    @property
    def current(self) -> int:
        return self._current

    @property
    def frequency(self) -> int:
        return self._frequency

    @property
    def percent_load(self) -> int:
        return self._percent_load

    def set(
        self,
        *,
        voltage: int | None = None,
        current: int | None = None,
        frequency: int | None = None,
        percent_load: int | None = None,
    ) -> None:
        """Update UPS metrics and send a report."""
        if voltage is not None:
            self._voltage = _clamp_u16(voltage)
        if current is not None:
            self._current = _clamp_u16(current)
        if frequency is not None:
            self._frequency = _clamp_u16(frequency)
        if percent_load is not None:
            self._percent_load = _clamp_u16(percent_load)
        self._send()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def switch_on(self) -> bool:
        """True if host requested power-on."""
        return self._switch_on

    @property
    def switch_off(self) -> bool:
        """True if host requested power-off."""
        return self._switch_off

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            b = event.data[0]
            self._switch_on = bool(b & _O_SWITCH_ON)
            self._switch_off = bool(b & _O_SWITCH_OFF)

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = bytes([
            self._voltage & 0xFF, (self._voltage >> 8) & 0xFF,
            self._current & 0xFF, (self._current >> 8) & 0xFF,
            self._frequency & 0xFF, (self._frequency >> 8) & 0xFF,
            self._percent_load & 0xFF, (self._percent_load >> 8) & 0xFF,
        ])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
