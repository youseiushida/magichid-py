"""Tests for FlightSim class (11-byte, flight simulation controls, report ID 2)."""

from __future__ import annotations

import pytest

from hid import IHidClient, FlightSim
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
def sim(client: _FakeClient, table: ReportTable) -> FlightSim:
    return FlightSim(client, table)


def test_set_aileron(sim: FlightSim, client: _FakeClient) -> None:
    sim.set(aileron=10000)
    assert sim.aileron == 10000
    p = client.last[1]
    assert p[0] == 2            # report ID
    # aileron = 10000 = 0x2710 → LE [0x10, 0x27]
    assert p[1] == 0x10 and p[2] == 0x27


def test_set_all_axes(sim: FlightSim, client: _FakeClient) -> None:
    sim.set(aileron=1, elevator=2, rudder=3, throttle=4, flaps=5)
    assert (sim.aileron, sim.elevator, sim.rudder, sim.throttle, sim.flaps) == (1, 2, 3, 4, 5)


def test_trigger(sim: FlightSim, client: _FakeClient) -> None:
    sim.set(trigger=True)
    assert sim.trigger
    p = client.last[1]
    assert p[11] == 0x01  # byte 10, bit 0


def test_negative_values(sim: FlightSim, client: _FakeClient) -> None:
    sim.set(rudder=-100)
    assert sim.rudder == -100
    p = client.last[1]
    # rudder at offset 4: -100 = 0xFF9C → LE [0x9C, 0xFF]
    assert p[5] == 0x9C and p[6] == 0xFF


def test_clamp(sim: FlightSim) -> None:
    sim.set(aileron=50000, elevator=-50000)
    assert sim.aileron == 32767
    assert sim.elevator == -32768


def test_payload_length(sim: FlightSim, client: _FakeClient) -> None:
    sim.set()
    assert len(client.last[1]) == 1 + 11


def test_not_reliable(sim: FlightSim, client: _FakeClient) -> None:
    sim.set(aileron=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
