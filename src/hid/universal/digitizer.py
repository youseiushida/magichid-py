"""Digitizer device (report ID 13, 9-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §16 (Digitizers Page 0x0D)

Wire format: ``[flags][x_lo][x_hi][y_lo][y_hi][pressure_lo][pressure_hi][x_tilt][y_tilt]``

* flags: bit 0 = Tip Switch (contact), bit 1 = Barrel Switch (pen button),
  bit 2 = In Range (proximity), bit 3 = Eraser
* X/Y: absolute 16-bit little-endian (0–65535)
* Pressure: 16-bit (0 = no contact, 65535 = max)
* Tilt: signed int8 (-128..127, where 0 = perpendicular to surface)

Not relative — reliable delivery is not required.
"""

from __future__ import annotations

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 13  # REPORT_ID_DIGITIZER

# -- flag bits ---------------------------------------------------------------
_F_TIP_SWITCH = 1 << 0
_F_BARREL_SWITCH = 1 << 1
_F_IN_RANGE = 1 << 2
_F_ERASER = 1 << 3

# -- defaults ----------------------------------------------------------------
_DEF_X = 32768
_DEF_Y = 32768


class Digitizer:
    """Absolute-position digitizer (touchscreen, pen tablet, etc.).

    Usage::

        dig = Digitizer(client, ReportTable.universal())

        # touch at (1000, 2000) with pressure
        dig.down(x=1000, y=2000, pressure=0.8)
        dig.move(x=1100, y=2050, pressure=0.7)
        dig.up()

        # pen with tilt
        dig.down(x=5000, y=3000, pressure=0.5, tilt_x=0.2, tilt_y=-0.1)
        dig.up()

    Coordinate ranges default to 0–65535 (16-bit absolute).
    All *float* inputs are clamped to 0.0–1.0 and mapped to the range.
    """

    def __init__(
        self,
        client: IHidClient,
        table: ReportTable,
        *,
        x_max: float = 65535.0,
        y_max: float = 65535.0,
        pressure_max: float = 65535.0,
    ) -> None:
        self._client = client
        self._table = table
        self._x_max = x_max
        self._y_max = y_max
        self._pressure_max = pressure_max
        # state
        self._flags: int = 0
        self._x: int = _DEF_X
        self._y: int = _DEF_Y
        self._pressure: int = 0
        self._x_tilt: int = 0
        self._y_tilt: int = 0

    # -- state queries -------------------------------------------------------- #

    @property
    def flags(self) -> int:
        return self._flags

    @property
    def is_touching(self) -> bool:
        """True if the tip is in contact with the surface."""
        return bool(self._flags & _F_TIP_SWITCH)

    @property
    def in_range(self) -> bool:
        """True if the transducer is in proximity of the surface."""
        return bool(self._flags & _F_IN_RANGE)

    @property
    def is_eraser(self) -> bool:
        """True if the eraser end is active."""
        return bool(self._flags & _F_ERASER)

    @property
    def position(self) -> tuple[int, int]:
        """Raw (x, y) position in device coordinates."""
        return self._x, self._y

    @property
    def position_frac(self) -> tuple[float, float]:
        """Fractional (x, y) position (0.0–1.0)."""
        return self._x / self._x_max, self._y / self._y_max

    @property
    def pressure(self) -> int:
        """Raw pressure (0–pressure_max)."""
        return self._pressure

    @property
    def pressure_frac(self) -> float:
        """Fractional pressure (0.0–1.0)."""
        return self._pressure / self._pressure_max

    @property
    def tilt(self) -> tuple[float, float]:
        """Tilt as (x, y) in -1.0 (left/back) to 1.0 (right/forward)."""
        return _s8_to_float(self._x_tilt), _s8_to_float(self._y_tilt)

    # -- touch lifecycle ------------------------------------------------------ #

    def move(self, x: float, y: float, pressure: float | None = None) -> None:
        """Move to (*x*, *y*) with optional *pressure*.  Maintains current contact state.

        *x*, *y* are fractional (0.0–1.0) coordinates.
        """
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
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        barrel: bool = False,
        eraser: bool = False,
    ) -> None:
        """Touch down at (*x*, *y*).  Sets Tip Switch and In Range."""
        self._x = _frac_to_u16(x, self._x_max)
        self._y = _frac_to_u16(y, self._y_max)
        self._pressure = _frac_to_u16(pressure, self._pressure_max)
        self._x_tilt = _float_to_s8(tilt_x)
        self._y_tilt = _float_to_s8(tilt_y)
        self._flags = _F_TIP_SWITCH | _F_IN_RANGE
        if barrel:
            self._flags |= _F_BARREL_SWITCH
        if eraser:
            self._flags |= _F_ERASER
        self._send()

    def up(self) -> None:
        """Lift off: clear all contact flags (Tip Switch, Barrel, Eraser, In Range).

        Sends an empty-flags report with zero pressure.
        """
        if not self.is_touching and not self.in_range:
            return
        self._flags &= ~(_F_TIP_SWITCH | _F_BARREL_SWITCH | _F_ERASER | _F_IN_RANGE)
        self._pressure = 0
        self._send()

    def release_all(self) -> None:
        """Release all contact: equivalent to :meth:`up`."""
        self.up()

    # -- pen buttons ---------------------------------------------------------- #

    def barrel_press(self) -> None:
        """Press the barrel (pen side) button."""
        if self._flags & _F_BARREL_SWITCH:
            return
        self._flags |= _F_BARREL_SWITCH
        self._send()

    def barrel_release(self) -> None:
        """Release the barrel button."""
        if not (self._flags & _F_BARREL_SWITCH):
            return
        self._flags &= ~_F_BARREL_SWITCH
        self._send()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        report = bytes([
            self._flags & 0xFF,
            self._x & 0xFF, (self._x >> 8) & 0xFF,
            self._y & 0xFF, (self._y >> 8) & 0xFF,
            self._pressure & 0xFF, (self._pressure >> 8) & 0xFF,
            self._x_tilt & 0xFF,
            self._y_tilt & 0xFF,
        ])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


# -- helpers ------------------------------------------------------------------

def _frac_to_u16(v: float, max_: float) -> int:
    """0.0–1.0 → 0–max_, clamped."""
    if v < 0.0:
        v = 0.0
    elif v > 1.0:
        v = 1.0
    return round(v * max_)


def _float_to_s8(v: float) -> int:
    """-1.0..1.0 → -128..127, clamped."""
    if v < -1.0:
        v = -1.0
    elif v > 1.0:
        v = 1.0
    return max(-128, min(127, round(v * 128)))


def _s8_to_float(b: int) -> float:
    """-128..127 → -1.0..1.0."""
    return (b - 256 if b >= 128 else b) / 128.0
