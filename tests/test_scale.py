"""Tests for Scale class (6B INPUT + 1B OUTPUT, report ID 30)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Scale
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
def scale(client: _FakeClient, table: ReportTable) -> Scale:
    return Scale(client, table)


def test_set_weight(scale: Scale, client: _FakeClient) -> None:
    scale.set(weight=150000)
    assert scale.weight == 150000
    p = client.last[1]
    assert p[0] == 30  # report ID
    # 150000 = 0x249F0 → LE [0xF0, 0x49, 0x02, 0x00]
    assert p[1] == 0xF0 and p[2] == 0x49 and p[3] == 0x02


def test_set_scaling(scale: Scale, client: _FakeClient) -> None:
    scale.set(scaling=-2)
    assert scale.scaling == -2
    assert client.last[1][5] == 0xFE  # byte 4, s8: -2 = 0xFE


def test_set_status(scale: Scale, client: _FakeClient) -> None:
    scale.set(status=0xAB)
    assert scale.status == 0xAB
    assert client.last[1][6] == 0xAB  # byte 5


def test_zero_requested(scale: Scale) -> None:
    ev = HostEventReceived(report_id=30, report_type=HidReportType.OUTPUT, data=bytes([0x01]))
    scale.handle_host_event(ev)
    assert scale.zero_requested


def test_not_reliable(scale: Scale, client: _FakeClient) -> None:
    scale.set(weight=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
