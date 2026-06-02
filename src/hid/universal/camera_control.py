"""Camera control device (report ID 32, 1-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §35 (Camera Control Page 0x90)

Wire format: single byte = camera command usage ID.
Both usages are One-Shot Controls — the host fires the action on receipt.
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 32  # REPORT_ID_CAMERA


class CameraAction(IntEnum):
    """HID Camera Control Page (0x90) usage IDs."""

    AUTO_FOCUS = 0x20
    SHUTTER = 0x21


class CameraControl:
    """Camera trigger — auto-focus and shutter (report ID 32).

    Usage::

        cam = CameraControl(client, ReportTable.universal())

        cam.trigger(CameraAction.AUTO_FOCUS)
        cam.trigger(CameraAction.SHUTTER)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table

    def trigger(self, action: CameraAction) -> None:
        """Send a one-shot camera command (auto-focus or shutter)."""
        report = bytes([int(action)])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
