"""Tests for UPS class (8-byte INPUT, 1-byte OUTPUT, report ID 27)."""

from __future__ import annotations

import pytest

from hid import IHidClient, UPS
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
def ups(client: _FakeClient, table: ReportTable) -> UPS:
    return UPS(client, table)


# -- INPUT -------------------------------------------------------------------


def test_set_voltage(ups: UPS, client: _FakeClient) -> None:
    ups.set(voltage=12000)
    assert ups.voltage == 12000
    p = client.last[1]
    assert p[0] == 27              # report ID
    # 12000 = 0x2EE0 → LE [0xE0, 0x2E]
    assert p[1] == 0xE0 and p[2] == 0x2E


def test_set_all_metrics(ups: UPS, client: _FakeClient) -> None:
    ups.set(voltage=100, current=50, frequency=600, percent_load=4500)
    p = client.last[1]
    # verify positioning
    assert p[1] == 100 and p[2] == 0       # voltage = 100
    assert p[3] == 50 and p[4] == 0        # current = 50
    assert p[5] == 0x58 and p[6] == 0x02   # frequency = 600
    assert p[7] == 0x94 and p[8] == 0x11   # percent_load = 4500


def test_set_partial(ups: UPS) -> None:
    ups.set(voltage=220000)
    assert ups.voltage == 65535  # clamped
    assert ups.current == 0      # unchanged


def test_payload_length(ups: UPS, client: _FakeClient) -> None:
    ups.set(voltage=100)
    assert len(client.last[1]) == 1 + 8


# -- OUTPUT host control -----------------------------------------------------


def test_switch_on(ups: UPS) -> None:
    ev = HostEventReceived(report_id=27, report_type=HidReportType.OUTPUT, data=bytes([0x01]))
    ups.handle_host_event(ev)
    assert ups.switch_on
    assert not ups.switch_off


def test_switch_off(ups: UPS) -> None:
    ev = HostEventReceived(report_id=27, report_type=HidReportType.OUTPUT, data=bytes([0x02]))
    ups.handle_host_event(ev)
    assert ups.switch_off


def test_handle_host_event_ignores_input(ups: UPS) -> None:
    ev = HostEventReceived(report_id=27, report_type=HidReportType.INPUT, data=bytes([0xFF]))
    ups.handle_host_event(ev)
    assert not ups.switch_on


# -- reliable ----------------------------------------------------------------


def test_ups_not_reliable(ups: UPS, client: _FakeClient) -> None:
    ups.set(voltage=100)
    _, _, reliable = client.last
    assert reliable is False


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
