"""Tests for Gamepad class (3D Game Controller, 6-axis s8 relative)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Gamepad
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
def ctl(client: _FakeClient, table: ReportTable) -> Gamepad:
    return Gamepad(client, table)


def test_turn(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.turn(10)
    p = client.last[1]
    assert p[0] == 5          # report ID
    assert _s8(p[1]) == 10    # turn (byte 0)
    assert p[2:7] == b"\x00" * 5


def test_pitch(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.pitch(-5)
    assert _s8(client.last[1][2]) == -5


def test_roll(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.roll(3)
    assert _s8(client.last[1][3]) == 3


def test_move(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.move(right=5, forward=10, up=-2)
    p = client.last[1]
    assert _s8(p[4]) == 5    # move right-left
    assert _s8(p[5]) == 10   # move forward-backward
    assert _s8(p[6]) == -2   # move up-down


def test_reset(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.turn(50)
    ctl.reset()
    assert client.last[1][1:7] == b"\x00" * 6


def test_clamp_to_s8_range(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.turn(200)
    assert _s8(client.last[1][1]) == 127
    ctl.turn(-200)
    assert _s8(client.last[1][1]) == -127


def test_reliable(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.turn(0)
    _, _, reliable = client.last
    assert reliable is True


def test_payload_length(ctl: Gamepad, client: _FakeClient) -> None:
    ctl.turn(5)
    assert len(client.last[1]) == 1 + 6


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")


def _s8(b: int) -> int:
    return b - 256 if b >= 128 else b
