"""Tests for GamingDevice class (8B INPUT + 8B OUTPUT pipe, report ID 34)."""

from __future__ import annotations

import pytest

from hid import IHidClient, GamingDevice
from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType


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
def gd(client: _FakeClient, table: ReportTable) -> GamingDevice:
    return GamingDevice(client, table)


# -- send --------------------------------------------------------------------


def test_send_exact_8(gd: GamingDevice, client: _FakeClient) -> None:
    data = bytes(range(8))
    gd.send(data)
    p = client.last[1]
    assert p[0] == 34
    assert p[1:9] == data


def test_send_pads_short(gd: GamingDevice, client: _FakeClient) -> None:
    gd.send(b"\xAA")
    p = client.last[1]
    assert p[1] == 0xAA
    assert all(b == 0 for b in p[2:9])


def test_send_rejects_overlong(gd: GamingDevice) -> None:
    with pytest.raises(ValueError):
        gd.send(bytes(9))


def test_payload_length(gd: GamingDevice, client: _FakeClient) -> None:
    gd.send(bytes(8))
    assert len(client.last[1]) == 1 + 8


# -- receive -----------------------------------------------------------------


def test_receive_output(gd: GamingDevice) -> None:
    ev = HostEventReceived(
        report_id=34, report_type=HidReportType.OUTPUT,
        data=bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80])
    )
    result = gd.handle_host_event(ev)
    assert result == bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80])


def test_receive_short_padded(gd: GamingDevice) -> None:
    ev = HostEventReceived(report_id=34, report_type=HidReportType.OUTPUT, data=b"\xFF")
    result = gd.handle_host_event(ev)
    assert len(result) == 8
    assert result[0] == 0xFF
    assert result[1] == 0x00


def test_receive_ignores_input(gd: GamingDevice) -> None:
    ev = HostEventReceived(report_id=34, report_type=HidReportType.INPUT, data=bytes(8))
    assert gd.handle_host_event(ev) is None


def test_receive_ignores_other_report(gd: GamingDevice) -> None:
    ev = HostEventReceived(report_id=99, report_type=HidReportType.OUTPUT, data=bytes(8))
    assert gd.handle_host_event(ev) is None


# -- reliable ----------------------------------------------------------------


def test_not_reliable(gd: GamingDevice, client: _FakeClient) -> None:
    gd.send(bytes(8))
    _, _, reliable = client.last
    assert reliable is False


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
