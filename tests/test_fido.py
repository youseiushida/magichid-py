"""Tests for FIDO class (64-byte INPUT + OUTPUT packets, report ID 35)."""

from __future__ import annotations

import pytest

from hid import IHidClient, FIDO
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
def fido(client: _FakeClient, table: ReportTable) -> FIDO:
    return FIDO(client, table)


# -- send --------------------------------------------------------------------


def test_send_exact_64(fido: FIDO, client: _FakeClient) -> None:
    data = bytes(range(64))
    fido.send(data)
    p = client.last[1]
    assert p[0] == 35                  # report ID
    assert client.last[0] == MsgType.SEND_REPORT
    assert p[1:65] == data             # 64 bytes unchanged


def test_send_pads_short_data(fido: FIDO, client: _FakeClient) -> None:
    fido.send(b"\xAA\xBB")
    p = client.last[1]
    assert p[1] == 0xAA and p[2] == 0xBB
    assert all(b == 0 for b in p[3:65])  # rest zero
    assert len(p) == 1 + 64             # report_id + 64 bytes


def test_send_rejects_overlong(fido: FIDO) -> None:
    with pytest.raises(ValueError, match="exceeds 64"):
        fido.send(bytes([0xFF]) * 100)


# -- payload structure -------------------------------------------------------


def test_payload_length(fido: FIDO, client: _FakeClient) -> None:
    fido.send(b"\x00" * 64)
    assert len(client.last[1]) == 1 + 64


# -- reliable flag -----------------------------------------------------------


def test_fido_not_reliable(fido: FIDO, client: _FakeClient) -> None:
    fido.send(b"\x00" * 64)
    _, _, reliable = client.last
    assert reliable is False


# -- handle_host_event (receive) ---------------------------------------------


def test_handle_fido_output(fido: FIDO) -> None:
    cmd = bytes([0x01]) + b"\x00" * 63  # 64 bytes
    ev = HostEventReceived(
        report_id=35,
        report_type=HidReportType.OUTPUT,
        data=cmd,
    )
    result = fido.handle_host_event(ev)
    assert result is not None
    assert len(result) == 64
    assert result[0] == 0x01


def test_handle_host_event_pads_short(fido: FIDO) -> None:
    ev = HostEventReceived(
        report_id=35,
        report_type=HidReportType.OUTPUT,
        data=b"\xFE",
    )
    result = fido.handle_host_event(ev)
    assert result is not None
    assert len(result) == 64
    assert result[0] == 0xFE
    assert result[1] == 0x00  # padded


def test_handle_host_event_ignores_input(fido: FIDO) -> None:
    ev = HostEventReceived(
        report_id=35,
        report_type=HidReportType.INPUT,
        data=bytes(64),
    )
    assert fido.handle_host_event(ev) is None


def test_handle_host_event_ignores_other_report(fido: FIDO) -> None:
    ev = HostEventReceived(
        report_id=7,  # keyboard
        report_type=HidReportType.OUTPUT,
        data=bytes(64),
    )
    assert fido.handle_host_event(ev) is None


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
