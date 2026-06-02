"""Tests for Digitizer class (9-byte absolute-position digitizer, report ID 13)."""

from __future__ import annotations

import pytest
from math import isclose

from hid import IHidClient, Digitizer
from core.reports import ReportTable


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))

    @property
    def last(self) -> tuple[int, bytes, bool]:
        return self.calls[-1]


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def table() -> ReportTable:
    return ReportTable.universal()


@pytest.fixture
def dig(client: _FakeClient, table: ReportTable) -> Digitizer:
    return Digitizer(client, table)


# -- down / move / up --------------------------------------------------------


def test_down_sets_tip_and_in_range(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    assert dig.is_touching
    assert dig.in_range
    p = client.last[1]
    assert p[0] == 13            # report ID
    # flags: Tip Switch (0x01) + In Range (0x04) = 0x05
    assert p[1] == 0x05


def test_move_while_down(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.0, y=0.0)
    dig.move(x=1.0, y=1.0)
    assert dig.is_touching         # state preserved
    p = client.last[1]
    assert p[1] == 0x05            # flags unchanged


def test_up_clears_flags(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    dig.up()
    assert not dig.is_touching
    assert not dig.in_range
    assert client.last[1][1] == 0x00


def test_up_when_idle_noop(dig: Digitizer, client: _FakeClient) -> None:
    n = len(client.calls)
    dig.up()
    assert len(client.calls) == n


# -- coordinates -------------------------------------------------------------


def test_position_raw(dig: Digitizer) -> None:
    """Default x_max=65535, so 0.5 → 32768."""
    dig.down(x=0.5, y=0.0)
    assert dig.position == (32768, 0)


def test_position_frac(dig: Digitizer) -> None:
    dig.down(x=0.25, y=0.75)
    fx, fy = dig.position_frac
    assert isclose(fx, 0.25, rel_tol=0.01)
    assert isclose(fy, 0.75, rel_tol=0.01)


def test_coord_wire_bytes(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=1.0, y=1.0)  # both → 65535
    p = client.last[1]
    # X at bytes 2-3 (little-endian)
    assert p[2] == 0xFF and p[3] == 0xFF   # 65535
    # Y at bytes 4-5
    assert p[4] == 0xFF and p[5] == 0xFF


# -- pressure ----------------------------------------------------------------


def test_pressure(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, pressure=1.0)
    assert dig.pressure == 65535
    p = client.last[1]
    assert p[6] == 0xFF and p[7] == 0xFF  # pressure 16-bit


def test_pressure_frac(dig: Digitizer) -> None:
    dig.down(x=0.5, y=0.5, pressure=0.5)
    assert isclose(dig.pressure_frac, 0.5, rel_tol=0.01)


# -- tilt --------------------------------------------------------------------


def test_tilt(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, tilt_x=1.0, tilt_y=-1.0)
    tx, ty = dig.tilt
    assert isclose(tx, 1.0, rel_tol=0.02)
    assert isclose(ty, -1.0, rel_tol=0.02)
    p = client.last[1]
    assert _s8(p[8]) == 127    # x tilt
    assert _s8(p[9]) == -128   # y tilt


def test_tilt_default_zero(dig: Digitizer) -> None:
    dig.down(x=0.5, y=0.5)
    tx, ty = dig.tilt
    assert isclose(tx, 0.0, abs_tol=0.02)
    assert isclose(ty, 0.0, abs_tol=0.02)


# -- barrel / eraser ---------------------------------------------------------


def test_barrel_button(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, barrel=True)
    assert client.last[1][1] & 0x02  # barrel switch flag


def test_barrel_press_release(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    dig.barrel_press()
    assert client.last[1][1] & 0x02
    dig.barrel_release()
    assert not (client.last[1][1] & 0x02)


def test_eraser_flag(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, eraser=True)
    assert client.last[1][1] & 0x08
    assert dig.is_eraser


def test_eraser_not_set_by_default(dig: Digitizer) -> None:
    dig.down(x=0.5, y=0.5)
    assert not dig.is_eraser


def test_release_all(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    dig.release_all()
    assert not dig.is_touching
    assert not dig.in_range
    assert client.last[1][1] == 0x00


# -- reliable flag -----------------------------------------------------------


def test_digitizer_not_reliable(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    _, _, reliable = client.last
    assert reliable is False  # not relative


# -- payload structure -------------------------------------------------------


def test_payload_length(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    assert len(client.last[1]) == 1 + 9  # report_id + 9 bytes


# -- custom range ------------------------------------------------------------


def test_custom_range(client: _FakeClient, table: ReportTable) -> None:
    d = Digitizer(client, table, x_max=1920, y_max=1080, pressure_max=1023)
    d.down(x=1.0, y=1.0, pressure=1.0)
    assert d.position == (1920, 1080)
    assert d.pressure == 1023


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")


# -- helpers -----------------------------------------------------------------


def _s8(b: int) -> int:
    return b - 256 if b >= 128 else b
