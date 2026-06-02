"""Tests for PID class (4-byte OUTPUT force feedback, report ID 15)."""

from __future__ import annotations

import pytest

from hid import IHidClient, PID
from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def table() -> ReportTable:
    return ReportTable.universal()


@pytest.fixture
def pid(client: _FakeClient, table: ReportTable) -> PID:
    return PID(client, table)


def test_receive_force(pid: PID) -> None:
    ev = HostEventReceived(
        report_id=15, report_type=HidReportType.OUTPUT,
        data=bytes([0x01, 0xE8, 0x03, 0xFF])
    )
    result = pid.handle_host_event(ev)
    assert result == (1, 1000, 255)  # effect=1(constant), dur=0x03E8=1000, gain=0xFF
    assert pid.effect_type == 1
    assert pid.duration == 1000
    assert pid.gain == 255


def test_ignores_input(pid: PID) -> None:
    ev = HostEventReceived(report_id=15, report_type=HidReportType.INPUT, data=bytes(4))
    assert pid.handle_host_event(ev) is None


def test_ignores_other_report(pid: PID) -> None:
    ev = HostEventReceived(report_id=99, report_type=HidReportType.OUTPUT, data=bytes(4))
    assert pid.handle_host_event(ev) is None


def test_clamps_effect_type(pid: PID) -> None:
    ev = HostEventReceived(
        report_id=15, report_type=HidReportType.OUTPUT, data=bytes([9, 0, 0, 0])
    )
    pid.handle_host_event(ev)
    assert pid.effect_type == 3  # clamped to max 3


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
