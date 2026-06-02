"""Haptics controller device (report ID 14, 2-byte OUTPUT + 2-byte FEATURE).

Conforms to:
* universal_reports.yaml — report ID 14, Page 0x000E (Haptics), Simple Haptic Controller

OUTPUT:  ``[manual_trigger:1][intensity:1]`` — host requests a haptic pulse
FEATURE: ``[waveform:1][duration:1]`` — brain configures waveform + duration
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 14


class Haptics:
    """Simple haptic controller — receive triggers, configure waveform/duration.

    Usage::

        hap = Haptics(client, ReportTable.universal())

        # configure haptic parameters
        hap.set(waveform=1, duration=50)

        # receive trigger events from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                hap.handle_host_event(ev)
        if hap.triggered:
            print(hap.trigger_value, hap.intensity)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        # OUTPUT state (from host)
        self._trigger_value: int = 0
        self._intensity: int = 0
        # FEATURE state
        self._waveform: int = 0
        self._duration: int = 0

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def trigger_value(self) -> int:
        """Last manual trigger value (0-255) from host."""
        return self._trigger_value

    @property
    def intensity(self) -> int:
        """Last intensity value (0-255) from host."""
        return self._intensity

    @property
    def triggered(self) -> bool:
        """True if the host sent a non-zero trigger."""
        return self._trigger_value != 0

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and len(event.data) >= 2
        ):
            self._trigger_value = event.data[0] & 0xFF
            self._intensity = event.data[1] & 0xFF

    # -- FEATURE -------------------------------------------------------------- #

    @property
    def waveform(self) -> int:
        """Configured waveform type (0-255)."""
        return self._waveform

    @property
    def duration(self) -> int:
        """Configured duration (0-255)."""
        return self._duration

    def set(self, *, waveform: int | None = None, duration: int | None = None) -> None:
        """Set haptic waveform and/or duration and send a FEATURE report."""
        if waveform is not None:
            self._waveform = _clamp_u8(waveform)
        if duration is not None:
            self._duration = _clamp_u8(duration)
        self._send_feature()

    # -- internals ------------------------------------------------------------ #

    def _send_feature(self) -> None:
        report = bytes([self._waveform & 0xFF, self._duration & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_feature(_REPORT_ID, report)
        self._client.request(MsgType.SET_FEATURE, payload, reliable=True)


def _clamp_u8(v: int) -> int:
    if v < 0:
        return 0
    if v > 255:
        return 255
    return v
