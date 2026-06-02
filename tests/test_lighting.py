"""Tests for LampArray class (6B OUTPUT + 14B FEATURE, report ID 23)."""

from __future__ import annotations

import pytest

from hid import IHidClient, LampArray
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
def la(client: _FakeClient, table: ReportTable) -> LampArray:
    return LampArray(client, table)


# -- OUTPUT: lamp update from host -------------------------------------------


def test_receive_lamp_update(la: LampArray) -> None:
    ev = HostEventReceived(
        report_id=23, report_type=HidReportType.OUTPUT,
        data=bytes([0x05, 0x00, 0xFF, 0x00, 0x00, 0x80])
    )
    la.handle_host_event(ev)
    assert la.lamp_id == 5
    assert la.rgb == (255, 0, 0)
    assert la.intensity == 0x80


# -- FEATURE: geometry -------------------------------------------------------


def test_set_geometry(la: LampArray, client: _FakeClient) -> None:
    la.set_geometry(lamp_count=64, width=800, height=600, depth=10)
    assert la.lamp_count == 64
    assert la.width == 800 and la.height == 600 and la.depth == 10
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 23
    # lamp_count = 64 → LE [0x40, 0x00]
    assert p[1] == 0x40 and p[2] == 0x00
    # width = 800 = 0x320 → LE [0x20, 0x03, 0x00, 0x00]
    assert p[3] == 0x20 and p[4] == 0x03


def test_feature_reliable(la: LampArray, client: _FakeClient) -> None:
    la.set_geometry(lamp_count=1)
    _, _, reliable = client.last
    assert reliable is True


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
