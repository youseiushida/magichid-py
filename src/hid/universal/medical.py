"""Medical Ultrasound device (report ID 21, 5-byte INPUT).

Conforms to:
* universal_reports.yaml — report ID 21, Page 0x0040 (Medical Instrument)

Fields: ``[vcr:1][freeze:1][pad:6][depth:1][focus:1][power:1][cine:1]``
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 21

_F_VCR = 1 << 0
_F_FREEZE = 1 << 1


class MedicalUltrasound:
    """Medical ultrasound controls — VCR, freeze, depth, focus, power, cine.

    Usage::

        us = MedicalUltrasound(client, ReportTable.universal())

        us.set(depth=50, focus=30, transmit_power=80)
        us.set(vcr_acquisition=True, cine=100)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._vcr: bool = False
        self._freeze: bool = False
        self._depth: int = 0
        self._focus: int = 0
        self._power: int = 0
        self._cine: int = 0

    # -- state ---------------------------------------------------------------- #

    @property
    def vcr_acquisition(self) -> bool:
        return self._vcr

    @property
    def freeze(self) -> bool:
        return self._freeze

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def focus(self) -> int:
        return self._focus

    @property
    def transmit_power(self) -> int:
        return self._power

    @property
    def cine(self) -> int:
        return self._cine

    def set(
        self,
        *,
        vcr_acquisition: bool | None = None,
        freeze: bool | None = None,
        depth: int | None = None,
        focus: int | None = None,
        transmit_power: int | None = None,
        cine: int | None = None,
    ) -> None:
        """Set one or more ultrasound controls and send a report."""
        if vcr_acquisition is not None:
            self._vcr = vcr_acquisition
        if freeze is not None:
            self._freeze = freeze
        if depth is not None:
            self._depth = _clamp_u8(depth)
        if focus is not None:
            self._focus = _clamp_u8(focus)
        if transmit_power is not None:
            self._power = _clamp_u8(transmit_power)
        if cine is not None:
            self._cine = _clamp_u8(cine)
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        flags = 0
        if self._vcr:
            flags |= _F_VCR
        if self._freeze:
            flags |= _F_FREEZE
        report = bytes([
            flags & 0xFF,
            self._depth & 0xFF,
            self._focus & 0xFF,
            self._power & 0xFF,
            self._cine & 0xFF,
        ])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _clamp_u8(v: int) -> int:
    return max(0, min(255, v))
