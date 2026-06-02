"""LED / Generic Indicator device (report ID 8, 4-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 8, Page 0x0008 (LED), Generic Indicator

OUTPUT: ``[flags:1][red:1][green:1][blue:1]`` — keyboard LEDs + RGB channel
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType

from .._client import IHidClient

_REPORT_ID = 8

_F_NUM_LOCK = 1 << 0
_F_CAPS_LOCK = 1 << 1
_F_SCROLL_LOCK = 1 << 2
_F_MUTE = 1 << 3
_F_GENERIC = 1 << 4


class LED:
    """LED indicator receiver — keyboard lock LEDs + RGB channels.

    Usage::

        led = LED(client, ReportTable.universal())

        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                led.handle_host_event(ev)
        print(led.num_lock, led.caps_lock)
        print(led.red, led.green, led.blue)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._num_lock: bool = False
        self._caps_lock: bool = False
        self._scroll_lock: bool = False
        self._mute: bool = False
        self._generic: bool = False
        self._red: int = 0
        self._green: int = 0
        self._blue: int = 0

    # -- state ---------------------------------------------------------------- #

    @property
    def num_lock(self) -> bool:
        return self._num_lock

    @property
    def caps_lock(self) -> bool:
        return self._caps_lock

    @property
    def scroll_lock(self) -> bool:
        return self._scroll_lock

    @property
    def mute(self) -> bool:
        return self._mute

    @property
    def generic(self) -> bool:
        return self._generic

    @property
    def red(self) -> int:
        return self._red

    @property
    def green(self) -> int:
        return self._green

    @property
    def blue(self) -> int:
        return self._blue

    @property
    def rgb(self) -> tuple[int, int, int]:
        return self._red, self._green, self._blue

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and len(event.data) >= 4
        ):
            f = event.data[0]
            self._num_lock = bool(f & _F_NUM_LOCK)
            self._caps_lock = bool(f & _F_CAPS_LOCK)
            self._scroll_lock = bool(f & _F_SCROLL_LOCK)
            self._mute = bool(f & _F_MUTE)
            self._generic = bool(f & _F_GENERIC)
            self._red = event.data[1] & 0xFF
            self._green = event.data[2] & 0xFF
            self._blue = event.data[3] & 0xFF
