"""Tests for Telephony class (flags byte + keypad selector, report ID 11)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Telephony
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
def tel(client: _FakeClient, table: ReportTable) -> Telephony:
    return Telephony(client, table)


# -- flags -------------------------------------------------------------------


def test_hook_switch(tel: Telephony, client: _FakeClient) -> None:
    tel.hook_switch = True
    tel.send()
    assert client.last[1][1] == 0x01
    assert tel.hook_switch


def test_multiple_flags(tel: Telephony, client: _FakeClient) -> None:
    tel.hook_switch = True
    tel.mute = True
    tel.send()
    assert client.last[1][1] == 0x09  # bits 0 and 3


def test_flash_momentary(tel: Telephony, client: _FakeClient) -> None:
    tel.flash = True
    tel.send()
    assert client.last[1][1] == 0x02
    tel.flash = False
    tel.send()
    assert client.last[1][1] == 0x00


# -- keypad ------------------------------------------------------------------


def test_keypad_press(tel: Telephony, client: _FakeClient) -> None:
    tel.keypad_press(5)
    assert tel.keypad == 5
    assert client.last[1][2] == 5  # byte 1 = keypad value


def test_keypad_zero_means_no_key(tel: Telephony) -> None:
    assert tel.keypad == 0  # default: no key


def test_keypad_rejects_invalid(tel: Telephony) -> None:
    with pytest.raises(ValueError):
        tel.keypad_press(13)


# -- OUTPUT LED state --------------------------------------------------------


def test_off_hook_led(tel: Telephony) -> None:
    ev = HostEventReceived(report_id=11, report_type=HidReportType.OUTPUT, data=bytes([0x01]))
    tel.handle_host_event(ev)
    assert tel.off_hook


def test_ring_led(tel: Telephony) -> None:
    ev = HostEventReceived(report_id=11, report_type=HidReportType.OUTPUT, data=bytes([0x02]))
    tel.handle_host_event(ev)
    assert tel.ring


def test_message_waiting_led(tel: Telephony) -> None:
    ev = HostEventReceived(report_id=11, report_type=HidReportType.OUTPUT, data=bytes([0x04]))
    tel.handle_host_event(ev)
    assert tel.message_waiting


def test_handle_host_event_ignores_input(tel: Telephony) -> None:
    ev = HostEventReceived(report_id=11, report_type=HidReportType.INPUT, data=bytes([0xFF]))
    tel.handle_host_event(ev)
    assert not tel.message_waiting


def test_handle_host_event_ignores_other_report(tel: Telephony) -> None:
    ev = HostEventReceived(report_id=99, report_type=HidReportType.OUTPUT, data=bytes([0xFF]))
    tel.handle_host_event(ev)
    assert not tel.message_waiting


# -- payload -----------------------------------------------------------------


def test_payload_length(tel: Telephony, client: _FakeClient) -> None:
    tel.send()
    assert len(client.last[1]) == 1 + 2


def test_reliable(tel: Telephony, client: _FakeClient) -> None:
    tel.send()
    _, _, reliable = client.last
    assert reliable is False


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
