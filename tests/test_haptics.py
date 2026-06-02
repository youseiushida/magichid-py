"""Tests for Haptics class (2B OUTPUT + 2B FEATURE, report ID 14)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Haptics
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
def hap(client: _FakeClient, table: ReportTable) -> Haptics:
    return Haptics(client, table)


# -- OUTPUT: trigger from host -----------------------------------------------


def test_receive_trigger(hap: Haptics) -> None:
    ev = HostEventReceived(
        report_id=14, report_type=HidReportType.OUTPUT, data=bytes([0x80, 0xFF])
    )
    hap.handle_host_event(ev)
    assert hap.triggered
    assert hap.trigger_value == 0x80
    assert hap.intensity == 0xFF


def test_zero_trigger_not_triggered(hap: Haptics) -> None:
    ev = HostEventReceived(
        report_id=14, report_type=HidReportType.OUTPUT, data=bytes([0x00, 0x00])
    )
    hap.handle_host_event(ev)
    assert not hap.triggered


def test_ignores_input(hap: Haptics) -> None:
    ev = HostEventReceived(report_id=14, report_type=HidReportType.INPUT, data=bytes([0xFF, 0xFF]))
    hap.handle_host_event(ev)
    assert not hap.triggered


# -- FEATURE: waveform / duration --------------------------------------------


def test_set_waveform(hap: Haptics, client: _FakeClient) -> None:
    hap.set(waveform=3, duration=50)
    assert hap.waveform == 3 and hap.duration == 50
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 14 and p[1] == 3 and p[2] == 50


def test_feature_reliable(hap: Haptics, client: _FakeClient) -> None:
    hap.set(waveform=0)
    _, _, reliable = client.last
    assert reliable is True


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
