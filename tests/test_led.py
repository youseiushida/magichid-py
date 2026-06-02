"""Tests for LED class (4-byte OUTPUT, report ID 8)."""

from __future__ import annotations

import pytest

from hid import IHidClient, LED
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
def led(client: _FakeClient, table: ReportTable) -> LED:
    return LED(client, table)


def test_flags(led: LED) -> None:
    ev = HostEventReceived(report_id=8, report_type=HidReportType.OUTPUT, data=bytes([0x07, 0, 0, 0]))
    led.handle_host_event(ev)
    assert led.num_lock and led.caps_lock and led.scroll_lock
    assert not led.mute


def test_rgb_channels(led: LED) -> None:
    ev = HostEventReceived(
        report_id=8, report_type=HidReportType.OUTPUT,
        data=bytes([0x00, 0xFF, 0x80, 0x00])
    )
    led.handle_host_event(ev)
    assert led.rgb == (255, 128, 0)


def test_ignores_other_report(led: LED) -> None:
    ev = HostEventReceived(report_id=7, report_type=HidReportType.OUTPUT, data=bytes([0xFF, 0, 0, 0]))
    led.handle_host_event(ev)
    assert not led.num_lock


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
