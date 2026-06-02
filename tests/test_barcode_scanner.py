"""Tests for BarcodeScanner class (33B INPUT + 1B OUTPUT + 1B FEATURE, report ID 29)."""

from __future__ import annotations

import pytest

from hid import IHidClient, BarcodeScanner
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
def scanner(client: _FakeClient, table: ReportTable) -> BarcodeScanner:
    return BarcodeScanner(client, table)


# -- INPUT: send decoded data ------------------------------------------------


def test_send_barcode(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.send(b"4901234567890")
    assert scanner.triggered
    assert scanner.data == b"4901234567890"
    p = client.last[1]
    assert p[0] == 29                   # report ID
    assert p[1] == 0x01                 # trigger flag
    # data starts at byte 2
    assert p[2:15] == b"4901234567890"


def test_send_not_triggered(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.send(b"X", triggered=False)
    assert not scanner.triggered
    assert client.last[1][1] == 0x00     # no trigger flag


def test_send_pads_to_32(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.send(b"AB")
    p = client.last[1]
    assert p[2] == 0x41 and p[3] == 0x42  # 'A', 'B'
    assert all(b == 0 for b in p[4:34])   # rest zero-padded


def test_send_rejects_overlong(scanner: BarcodeScanner) -> None:
    with pytest.raises(ValueError):
        scanner.send(bytes(33))


def test_payload_length(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.send(b"")
    assert len(client.last[1]) == 1 + 33


# -- OUTPUT: scan trigger ----------------------------------------------------


def test_scan_requested(scanner: BarcodeScanner) -> None:
    assert not scanner.scan_requested
    ev = HostEventReceived(report_id=29, report_type=HidReportType.OUTPUT, data=bytes([0x01]))
    scanner.handle_host_event(ev)
    assert scanner.scan_requested


def test_scan_ignores_input(scanner: BarcodeScanner) -> None:
    ev = HostEventReceived(report_id=29, report_type=HidReportType.INPUT, data=bytes([0x01]))
    scanner.handle_host_event(ev)
    assert not scanner.scan_requested


# -- FEATURE: aiming pointer -------------------------------------------------


def test_set_aiming_pointer(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.set_aiming_pointer(True)
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 29
    assert p[1] == 0x01  # aiming bit


def test_set_aiming_pointer_off(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.set_aiming_pointer(True)
    scanner.set_aiming_pointer(False)
    assert client.last[1][1] == 0x00


# -- reliable ----------------------------------------------------------------


def test_input_not_reliable(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.send(b"")
    _, _, reliable = client.last
    assert reliable is False


def test_feature_reliable(scanner: BarcodeScanner, client: _FakeClient) -> None:
    scanner.set_aiming_pointer(True)
    _, _, reliable = client.last
    assert reliable is True


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
