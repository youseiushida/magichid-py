"""Tests for AuxDisplay class (16B OUTPUT + 2B FEATURE, report ID 19)."""

from __future__ import annotations

import pytest

from hid import IHidClient, AuxDisplay
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
def disp(client: _FakeClient, table: ReportTable) -> AuxDisplay:
    return AuxDisplay(client, table)


# -- OUTPUT: display text from host ------------------------------------------


def test_receive_text(disp: AuxDisplay) -> None:
    ev = HostEventReceived(
        report_id=19, report_type=HidReportType.OUTPUT,
        data=b"Hello, World!   "  # 16 bytes
    )
    disp.handle_host_event(ev)
    assert disp.text == b"Hello, World!   "


def test_receive_short_text_padded(disp: AuxDisplay) -> None:
    ev = HostEventReceived(
        report_id=19, report_type=HidReportType.OUTPUT,
        data=b"Hi"
    )
    disp.handle_host_event(ev)
    assert len(disp.text) == 16
    assert disp.text[:2] == b"Hi"
    assert disp.text[2:] == b"\x00" * 14


def test_receive_ignores_input(disp: AuxDisplay) -> None:
    ev = HostEventReceived(
        report_id=19, report_type=HidReportType.INPUT,
        data=b"X" * 16
    )
    disp.handle_host_event(ev)
    assert disp.text == b""  # unchanged


def test_receive_ignores_other_report(disp: AuxDisplay) -> None:
    ev = HostEventReceived(
        report_id=99, report_type=HidReportType.OUTPUT,
        data=b"X" * 16
    )
    disp.handle_host_event(ev)
    assert disp.text == b""


# -- FEATURE: brightness / contrast ------------------------------------------


def test_set_brightness(disp: AuxDisplay, client: _FakeClient) -> None:
    disp.set(brightness=80)
    assert disp.brightness == 80
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 19 and p[1] == 80 and p[2] == 0


def test_set_contrast(disp: AuxDisplay, client: _FakeClient) -> None:
    disp.set(contrast=50)
    assert disp.contrast == 50
    assert client.last[1][2] == 50


def test_set_clamps(disp: AuxDisplay) -> None:
    disp.set(brightness=200, contrast=-10)
    assert disp.brightness == 100
    assert disp.contrast == 0


# -- payload -----------------------------------------------------------------


def test_feature_payload_length(disp: AuxDisplay, client: _FakeClient) -> None:
    disp.set(brightness=50)
    assert len(client.last[1]) == 1 + 2


def test_feature_reliable(disp: AuxDisplay, client: _FakeClient) -> None:
    disp.set(brightness=50)
    _, _, reliable = client.last
    assert reliable is True


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
