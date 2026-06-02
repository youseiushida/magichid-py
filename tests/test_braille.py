"""Tests for BrailleDisplay class (1B INPUT + 8B OUTPUT + 1B FEATURE, report ID 22)."""

from __future__ import annotations

import pytest

from hid import IHidClient, BrailleDisplay
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
def brl(client: _FakeClient, table: ReportTable) -> BrailleDisplay:
    return BrailleDisplay(client, table)


# -- INPUT: dot keys ---------------------------------------------------------


def test_set_dots(brl: BrailleDisplay, client: _FakeClient) -> None:
    brl.set_dots(dot_1=True, dot_3=True)
    assert brl.dots == 0x05  # bits 0 and 2
    assert client.last[1][1] == 0x05


def test_release_dot(brl: BrailleDisplay, client: _FakeClient) -> None:
    brl.set_dots(dot_1=True, dot_2=True)
    brl.set_dots(dot_1=False)
    assert brl.dots == 0x02


def test_set_dots_no_args_noop(brl: BrailleDisplay, client: _FakeClient) -> None:
    n = len(client.calls)
    brl.set_dots()
    assert len(client.calls) == n


# -- OUTPUT: braille cells from host -----------------------------------------


def test_receive_cells(brl: BrailleDisplay) -> None:
    ev = HostEventReceived(
        report_id=22, report_type=HidReportType.OUTPUT,
        data=bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
    )
    brl.handle_host_event(ev)
    assert brl.cells == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])


# -- FEATURE: cell count -----------------------------------------------------


def test_set_cell_count(brl: BrailleDisplay, client: _FakeClient) -> None:
    brl.set_cell_count(40)
    assert brl.cell_count == 40
    assert client.last[0] == MsgType.SET_FEATURE
    assert client.last[1][1] == 40


# -- reliable ----------------------------------------------------------------


def test_input_not_reliable(brl: BrailleDisplay, client: _FakeClient) -> None:
    brl.set_dots(dot_1=True)
    _, _, reliable = client.last
    assert reliable is False


def test_feature_reliable(brl: BrailleDisplay, client: _FakeClient) -> None:
    brl.set_cell_count(0)
    _, _, reliable = client.last
    assert reliable is True


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
