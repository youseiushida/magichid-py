"""Digitizer device (report ID 13, 9-byte) on top of an :class:`IHidClient`.

Conforms to:
* universal_reports.yaml — report ID 13, Page 0x000D (Digitizers), Touch Screen

Wire format: ``[flags][contact_id][x:2][y:2][pressure:2][contact_count]``

* flags: bit 0 = tip_switch, bit 1 = in_range, bits 2-7 = padding
* contact_id: 8-bit identifier for multi-touch tracking
* X/Y: unsigned 16-bit LE (0–32767)
* Pressure: unsigned 16-bit LE (0–32767)
* contact_count: number of active contacts (0–127)

FEATURE (1 byte): contact_count_maximum (read-only, max supported contacts).
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 13

# -- flag bits ---------------------------------------------------------------
_F_TIP_SWITCH = 1 << 0
_F_IN_RANGE = 1 << 1

# -- defaults ----------------------------------------------------------------
_DEF_X = 16384
_DEF_Y = 16384


class Digitizer:
    """Absolute-position digitizer (touch screen, pen tablet).

    Usage::

        dig = Digitizer(client, ReportTable.universal())

        dig.down(x=0.5, y=0.5, contact_id=0)
        dig.move(x=0.6, y=0.5)
        dig.up()

    Coordinate ranges default to 0–32767 (15-bit signed-positive).
    All *float* inputs are clamped to 0.0–1.0 and mapped to the range.
    """

    def __init__(
        self,
        client: IHidClient,
        table: ReportTable,
        *,
        x_max: float = 32767.0,
        y_max: float = 32767.0,
        pressure_max: float = 32767.0,
    ) -> None:
        self._client = client
        self._table = table
        self._x_max = x_max
        self._y_max = y_max
        self._pressure_max = pressure_max
        self._flags: int = 0
        self._contact_id: int = 0
        self._x: int = _DEF_X
        self._y: int = _DEF_Y
        self._pressure: int = 0
        self._contact_count: int = 0

    # -- state queries -------------------------------------------------------- #

    @property
    def is_touching(self) -> bool:
        return bool(self._flags & _F_TIP_SWITCH)

    @property
    def in_range(self) -> bool:
        return bool(self._flags & _F_IN_RANGE)

    @property
    def contact_id(self) -> int:
        return self._contact_id

    @property
    def position(self) -> tuple[int, int]:
        return self._x, self._y

    @property
    def position_frac(self) -> tuple[float, float]:
        return self._x / self._x_max, self._y / self._y_max

    @property
    def pressure(self) -> int:
        return self._pressure

    @property
    def pressure_frac(self) -> float:
        return self._pressure / self._pressure_max

    @property
    def contact_count(self) -> int:
        return self._contact_count

    # -- touch lifecycle ------------------------------------------------------ #

    def move(self, x: float, y: float, pressure: float | None = None) -> None:
        self._x = _frac_to_u16(x, self._x_max)
        self._y = _frac_to_u16(y, self._y_max)
        if pressure is not None:
            self._pressure = _frac_to_u16(pressure, self._pressure_max)
        self._send()

    def down(
        self,
        x: float,
        y: float,
        pressure: float = 0.5,
        *,
        contact_id: int = 0,
    ) -> None:
        self._flags = _F_TIP_SWITCH | _F_IN_RANGE
        self._contact_id = contact_id & 0xFF
        self._contact_count = 1
        self._x = _frac_to_u16(x, self._x_max)
        self._y = _frac_to_u16(y, self._y_max)
        self._pressure = _frac_to_u16(pressure, self._pressure_max)
        self._send()

    def up(self) -> None:
        if not self.is_touching and not self.in_range:
            return
        self._flags = 0
        self._pressure = 0
        self._contact_count = 0
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = bytes([
            self._flags & 0xFF,
            self._contact_id & 0xFF,
            self._x & 0xFF, (self._x >> 8) & 0xFF,
            self._y & 0xFF, (self._y >> 8) & 0xFF,
            self._pressure & 0xFF, (self._pressure >> 8) & 0xFF,
            self._contact_count & 0xFF,
        ])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _frac_to_u16(v: float, max_: float) -> int:
    if v < 0.0:
        v = 0.0
    elif v > 1.0:
        v = 1.0
    return round(v * max_)
