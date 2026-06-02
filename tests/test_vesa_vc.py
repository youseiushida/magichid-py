"""Tests for VESAVC class (1B OUTPUT + 10B FEATURE, report ID 26)."""

from __future__ import annotations

import pytest

from hid import IHidClient, VESAVC
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
def vc(client: _FakeClient, table: ReportTable) -> VESAVC:
    return VESAVC(client, table)


# -- FEATURE: brightness -----------------------------------------------------


def test_set_brightness(vc: VESAVC, client: _FakeClient) -> None:
    vc.set(brightness=32768)
    assert vc.brightness == 32768
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 26               # report ID
    # brightness at offset 0: 32768 = 0x8000 → LE [0x00, 0x80]
    assert p[1] == 0x00 and p[2] == 0x80


def test_set_contrast(vc: VESAVC, client: _FakeClient) -> None:
    vc.set(contrast=100)
    assert vc.contrast == 100
    p = client.last[1]
    assert p[3] == 100 and p[4] == 0  # contrast at offset 2


def test_set_rgb_gains(vc: VESAVC, client: _FakeClient) -> None:
    vc.set(red_gain=100, green_gain=200, blue_gain=300)
    p = client.last[1]
    assert p[5] == 100 and p[6] == 0    # red at offset 4
    assert p[7] == 200 and p[8] == 0    # green at offset 6
    assert p[9] == 0x2C and p[10] == 0x01  # blue=300 → LE [0x2C, 0x01]


def test_set_all(vc: VESAVC) -> None:
    vc.set(brightness=1, contrast=2, red_gain=3, green_gain=4, blue_gain=5)
    assert (vc.brightness, vc.contrast, vc.red_gain, vc.green_gain, vc.blue_gain) \
           == (1, 2, 3, 4, 5)


def test_set_clamps(vc: VESAVC) -> None:
    vc.set(brightness=100000)
    assert vc.brightness == 65535


def test_payload_length(vc: VESAVC, client: _FakeClient) -> None:
    vc.set(brightness=0)
    assert len(client.last[1]) == 1 + 10  # report_id + 10 bytes


# -- OUTPUT: degauss ---------------------------------------------------------


def test_degauss_requested(vc: VESAVC) -> None:
    assert not vc.degauss_requested
    ev = HostEventReceived(report_id=26, report_type=HidReportType.OUTPUT, data=bytes([0x01]))
    vc.handle_host_event(ev)
    assert vc.degauss_requested


def test_degauss_ignores_input(vc: VESAVC) -> None:
    ev = HostEventReceived(report_id=26, report_type=HidReportType.INPUT, data=bytes([0x01]))
    vc.handle_host_event(ev)
    assert not vc.degauss_requested


# -- reliable ----------------------------------------------------------------


def test_feature_reliable(vc: VESAVC, client: _FakeClient) -> None:
    vc.set(brightness=1)
    _, _, reliable = client.last
    assert reliable is True


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
