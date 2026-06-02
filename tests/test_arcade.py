"""Tests for ArcadeIO class (2B INPUT + 2B OUTPUT GPIO, report ID 33)."""

from __future__ import annotations

import pytest

from hid import IHidClient, ArcadeIO
from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType


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
def io(client: _FakeClient, table: ReportTable) -> ArcadeIO:
    return ArcadeIO(client, table)


# -- INPUT -------------------------------------------------------------------


def test_set_input_digital(io: ArcadeIO, client: _FakeClient) -> None:
    io.set_input(digital=0b10101010)
    assert io.digital_in == 0xAA
    p = client.last[1]
    assert p[0] == 33            # report ID
    assert p[1] == 0xAA          # digital byte


def test_set_input_analog(io: ArcadeIO, client: _FakeClient) -> None:
    io.set_input(analog=200)
    assert io.analog_in == 200
    assert client.last[1][2] == 200


def test_set_input_both(io: ArcadeIO, client: _FakeClient) -> None:
    io.set_input(digital=0x0F, analog=128)
    assert io.digital_in == 0x0F
    assert io.analog_in == 128


def test_analog_clamped(io: ArcadeIO) -> None:
    io.set_input(analog=300)
    assert io.analog_in == 255


def test_payload_length(io: ArcadeIO, client: _FakeClient) -> None:
    io.set_input()
    assert len(client.last[1]) == 1 + 2


# -- OUTPUT ------------------------------------------------------------------


def test_host_digital_output(io: ArcadeIO) -> None:
    ev = HostEventReceived(report_id=33, report_type=HidReportType.OUTPUT, data=bytes([0xFF, 0x00]))
    io.handle_host_event(ev)
    assert io.host_digital == 0xFF
    assert not io.coin_lockout


def test_coin_lockout(io: ArcadeIO) -> None:
    ev = HostEventReceived(report_id=33, report_type=HidReportType.OUTPUT, data=bytes([0x00, 0x01]))
    io.handle_host_event(ev)
    assert io.coin_lockout


def test_handle_host_event_ignores_input(io: ArcadeIO) -> None:
    ev = HostEventReceived(report_id=33, report_type=HidReportType.INPUT, data=bytes([0xFF, 0xFF]))
    io.handle_host_event(ev)
    assert io.host_digital == 0  # unchanged


# -- reliable ----------------------------------------------------------------


def test_not_reliable(io: ArcadeIO, client: _FakeClient) -> None:
    io.set_input()
    _, _, reliable = client.last
    assert reliable is False


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
