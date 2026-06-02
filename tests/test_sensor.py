"""Tests for Accelerometer class (7B INPUT + 4B FEATURE, report ID 20)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Accelerometer
from core.reports import ReportTable
from core.wire import MsgType


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
def accel(client: _FakeClient, table: ReportTable) -> Accelerometer:
    return Accelerometer(client, table)


def test_set_acceleration(accel: Accelerometer, client: _FakeClient) -> None:
    accel.set(x=100, y=-50, z=9800, sensor_state=1)
    p = client.last[1]
    assert p[0] == 20           # report ID
    assert p[1] == 1            # sensor_state
    # x=100 → LE [0x64, 0x00]
    assert p[2] == 0x64 and p[3] == 0x00
    # y=-50 → LE [0xCE, 0xFF]
    assert p[4] == 0xCE and p[5] == 0xFF
    # z=9800=0x2648 → LE [0x48, 0x26]
    assert p[6] == 0x48 and p[7] == 0x26


def test_set_interval(accel: Accelerometer, client: _FakeClient) -> None:
    accel.set_interval(100)
    assert accel.interval == 100
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 20
    # 100 → LE [0x64, 0x00, 0x00, 0x00]
    assert p[1] == 0x64 and p[2:5] == b"\x00\x00\x00"


def test_clamp(accel: Accelerometer) -> None:
    accel.set(x=50000, y=-50000)
    assert accel.x == 32767 and accel.y == -32768


def test_input_not_reliable(accel: Accelerometer, client: _FakeClient) -> None:
    accel.set(x=1)
    _, _, reliable = client.last
    assert reliable is False


def test_feature_reliable(accel: Accelerometer, client: _FakeClient) -> None:
    accel.set_interval(0)
    _, _, reliable = client.last
    assert reliable is True


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
