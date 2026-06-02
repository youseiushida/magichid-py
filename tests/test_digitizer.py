"""Tests for Digitizer class (touch screen, 9-byte, report ID 13)."""

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


def test_down_sets_flags(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    assert dig.is_touching
    assert dig.in_range
    p = client.last[1]
    assert p[0] == 13           # report ID
    assert p[1] == 0x03          # tip_switch + in_range


def test_move_while_down(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.0, y=0.0)
    dig.move(x=1.0, y=1.0)
    assert dig.is_touching
    assert client.last[1][1] == 0x03  # flags unchanged


def test_up_clears_flags(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    dig.up()
    assert not dig.is_touching
    assert not dig.in_range
    assert dig.contact_count == 0


def test_up_when_idle_noop(dig: Digitizer, client: _FakeClient) -> None:
    n = len(client.calls)
    dig.up()
    assert len(client.calls) == n


# -- contact -----------------------------------------------------------------


def test_contact_id(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, contact_id=42)
    assert dig.contact_id == 42
    assert client.last[1][2] == 42  # byte 1 = contact_identifier


def test_contact_count(dig: Digitizer) -> None:
    dig.down(x=0.5, y=0.5)
    assert dig.contact_count == 1


# -- coordinates -------------------------------------------------------------


def test_position_raw(dig: Digitizer) -> None:
    """x_max=32767, 0.5 → 16384."""
    dig.down(x=0.5, y=0.0)
    assert dig.position == (16384, 0)


def test_coord_wire_bytes(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=1.0, y=1.0)
    p = client.last[1]
    # X at bytes 3-4 (LE): 32767 = 0x7FFF → [0xFF, 0x7F]
    assert p[3] == 0xFF and p[4] == 0x7F


# -- pressure ----------------------------------------------------------------


def test_pressure(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5, pressure=1.0)
    assert dig.pressure == 32767
    p = client.last[1]
    assert p[7] == 0xFF and p[8] == 0x7F  # bytes 7-8 = pressure


# -- reliable ----------------------------------------------------------------


def test_not_reliable(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    _, _, reliable = client.last
    assert reliable is False


# -- payload -----------------------------------------------------------------


def test_payload_length(dig: Digitizer, client: _FakeClient) -> None:
    dig.down(x=0.5, y=0.5)
    assert len(client.last[1]) == 1 + 9


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
