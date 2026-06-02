"""Tests for Telephony class (2-byte report, telephony control + keypad)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Telephony, TelephonyUsage
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


# -- press / release ---------------------------------------------------------


def test_press_sends_usage(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.HOOK_SWITCH)
    assert tel.is_active
    p = client.last[1]
    assert p[0] == 11            # report ID
    assert p[1] == 0x20          # HOOK_SWITCH low
    assert p[2] == 0x00          # high byte


def test_release_sends_zero(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.HOLD)
    tel.release()
    assert not tel.is_active
    assert client.last[1][1] == 0x00 and client.last[1][2] == 0x00


def test_tap(tel: Telephony, client: _FakeClient) -> None:
    n = len(client.calls)
    tel.tap(TelephonyUsage.REDIAL)
    assert len(client.calls) == n + 2
    assert not tel.is_active


def test_release_when_idle_noop(tel: Telephony, client: _FakeClient) -> None:
    n = len(client.calls)
    tel.release()
    assert len(client.calls) == n


def test_press_same_key_noop(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.MUTE)
    n = len(client.calls)
    tel.press(TelephonyUsage.MUTE)
    assert len(client.calls) == n


def test_press_new_key_replaces_old(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.HOOK_SWITCH)
    tel.press(TelephonyUsage.SPEAKER_PHONE)
    assert tel.current == 0x2B


# -- keypad ------------------------------------------------------------------


def test_keypad_key(tel: Telephony, client: _FakeClient) -> None:
    tel.tap(TelephonyUsage.KEY_5)
    assert len(client.calls) == 2  # press + release


def test_keypad_star_pound(tel: Telephony, client: _FakeClient) -> None:
    tel.tap(TelephonyUsage.KEY_STAR)
    assert client.calls[0][1][1] == 0xBA


# -- payload structure -------------------------------------------------------


def test_payload_length(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.HOOK_SWITCH)
    assert len(client.last[1]) == 1 + 2  # report_id + 2 bytes


# -- reliable flag -----------------------------------------------------------


def test_telephony_not_reliable(tel: Telephony, client: _FakeClient) -> None:
    tel.press(TelephonyUsage.REDIAL)
    _, _, reliable = client.last
    assert reliable is False


# -- LED message indicator ---------------------------------------------------


def test_led_byte_initial(tel: Telephony) -> None:
    assert tel.led_byte == 0


def test_message_waiting_initial(tel: Telephony) -> None:
    assert not tel.message_waiting


def test_message_waiting_from_host(tel: Telephony) -> None:
    ev = HostEventReceived(
        report_id=11,
        report_type=HidReportType.OUTPUT,
        data=bytes([0x01]),
    )
    tel.handle_host_event(ev)
    assert tel.message_waiting


def test_message_waiting_ignores_other_reports(tel: Telephony) -> None:
    ev = HostEventReceived(
        report_id=99,
        report_type=HidReportType.OUTPUT,
        data=bytes([0xFF]),
    )
    tel.handle_host_event(ev)
    assert not tel.message_waiting


# -- TelephonyUsage values ---------------------------------------------------


def test_usage_values() -> None:
    assert TelephonyUsage.HOOK_SWITCH == 0x20
    assert TelephonyUsage.KEY_0 == 0xB0
    assert TelephonyUsage.KEY_9 == 0xB9
    assert TelephonyUsage.KEY_STAR == 0xBA
    assert TelephonyUsage.KEY_POUND == 0xBB


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
