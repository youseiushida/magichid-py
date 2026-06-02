"""Camera control device (report ID 32, 1-byte) on top of an :class:`IHidClient`.

Conforms to:
* universal_reports.yaml — report ID 32, Page 0x0090 (Camera Control)

Wire format: 1 byte with auto-focus (bit 0) and shutter (bit 1) flags.
Both are One-Shot Controls — send 1 to trigger the action.
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 32

_F_AUTO_FOCUS = 1 << 0
_F_SHUTTER = 1 << 1


class CameraControl:
    """Camera trigger — auto-focus and shutter (report ID 32).

    Usage::

        cam = CameraControl(client, ReportTable.universal())

        cam.auto_focus()     # trigger auto-focus
        cam.shutter()        # trigger shutter
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def auto_focus(self) -> None:
        """Trigger camera auto-focus (one-shot)."""
        self._send(_F_AUTO_FOCUS)

    def shutter(self) -> None:
        """Trigger camera shutter (one-shot)."""
        self._send(_F_SHUTTER)

    def _send(self, flags: int) -> None:
        report = bytes([flags & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
