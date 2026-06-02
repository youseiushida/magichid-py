"""Tests for high-level Keyboard class (stateful 6KRO, LED, rollover)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Keycode, Keyboard, KeycodeError
from core.events import HostEventReceived
from core.reports import KEYBOARD, ReportTable
from core.wire import HidReportType, MsgType

# -- fake client --------------------------------------------------------------


class _FakeClient:
    """Records the last request for inspection."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))

    @property
    def last_payload(self) -> bytes:
        return self.calls[-1][1] if self.calls else b""


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def table() -> ReportTable:
    return ReportTable.universal()


@pytest.fixture
def kb(client: _FakeClient, table: ReportTable) -> Keyboard:
    return Keyboard(client, table)


# -- basic press / release ----------------------------------------------------


def test_press_single_key(kb: Keyboard, client: _FakeClient) -> None:
    kb.press(Keycode.A)
    assert kb.is_pressed(Keycode.A)
    assert kb.keys == (0x04,)
    assert kb.modifier == 0
    assert len(client.calls) == 1


def test_release_single_key(kb: Keyboard, client: _FakeClient) -> None:
    kb.press(Keycode.A)
    kb.release(Keycode.A)
    assert not kb.is_pressed(Keycode.A)
    assert kb.keys == ()
    assert len(client.calls) == 2


def test_press_already_pressed_noop(kb: Keyboard, client: _FakeClient) -> None:
    kb.press(Keycode.A)
    n = len(client.calls)
    kb.press(Keycode.A)
    assert len(client.calls) == n
    assert kb.keys == (0x04,)


def test_release_unpressed_noop(kb: Keyboard, client: _FakeClient) -> None:
    n = len(client.calls)
    kb.release(Keycode.Z)
    assert len(client.calls) == n


# -- modifiers ----------------------------------------------------------------


def test_modifier_byte(kb: Keyboard) -> None:
    kb.press(Keycode.LEFT_SHIFT)
    assert kb.modifier == 0x02
    assert kb.keys == ()


def test_modifier_and_key(kb: Keyboard) -> None:
    kb.press(Keycode.LEFT_SHIFT, Keycode.A)
    assert kb.modifier == 0x02
    assert kb.keys == (0x04,)


def test_release_modifier(kb: Keyboard) -> None:
    kb.press(Keycode.LEFT_SHIFT, Keycode.LEFT_CONTROL)
    assert kb.modifier == 0x03
    kb.release(Keycode.LEFT_SHIFT)
    assert kb.modifier == 0x01
    kb.release(Keycode.LEFT_CONTROL)
    assert kb.modifier == 0


def test_is_pressed_modifier(kb: Keyboard) -> None:
    assert not kb.is_pressed(Keycode.LEFT_SHIFT)
    kb.press(Keycode.LEFT_SHIFT)
    assert kb.is_pressed(Keycode.LEFT_SHIFT)


# -- 6KRO ---------------------------------------------------------------------


def test_six_keys_allowed(kb: Keyboard) -> None:
    keys = [Keycode(k) for k in range(0x04, 0x0A)]  # A-F = 6
    kb.press(*keys)
    assert len(kb.keys) == 6


def test_seventh_key_raises(kb: Keyboard) -> None:
    keys = [Keycode(k) for k in range(0x04, 0x0A)]
    kb.press(*keys)
    with pytest.raises(KeycodeError, match="6KRO"):
        kb.press(Keycode.G)


def test_six_keys_with_modifiers_succeeds(kb: Keyboard) -> None:
    keys = [Keycode(k) for k in range(0x04, 0x0A)]
    kb.press(Keycode.LEFT_SHIFT, Keycode.LEFT_CONTROL)
    kb.press(*keys)
    assert len(kb.keys) == 6
    assert kb.modifier == 0x03


def test_rollover_sends_error_rollover(
    client: _FakeClient, table: ReportTable,
) -> None:
    """HID spec: 7th key → all 6 slots report ErrorRollOver (0x01)."""
    kb = Keyboard(client, table, rollover=True)
    keys = [Keycode(k) for k in range(0x04, 0x0A)]  # A-F
    kb.press(*keys)  # 6 keys OK
    kb.press(Keycode.G)  # 7th → rollover
    assert kb.keys == (0x01,) * 6  # all ErrorRollOver
    # payload bytes 3-8 should all be 0x01
    p = client.last_payload
    assert p[3:9] == bytes([0x01] * 6)


# -- batch mode ---------------------------------------------------------------


def test_batch_defers_flush(kb: Keyboard, client: _FakeClient) -> None:
    n = len(client.calls)
    with kb.batch():
        kb.press(Keycode.A)
        kb.press(Keycode.B)
        assert len(client.calls) == n
    assert len(client.calls) == n + 1


def test_batch_flushes_on_dirty_only(kb: Keyboard, client: _FakeClient) -> None:
    n = len(client.calls)
    with kb.batch():
        pass
    assert len(client.calls) == n


# -- release_all --------------------------------------------------------------


def test_release_all(kb: Keyboard) -> None:
    kb.press(Keycode.LEFT_SHIFT, Keycode.A, Keycode.B)
    assert kb.keys and kb.modifier
    kb.release_all()
    assert kb.keys == ()
    assert kb.modifier == 0


# -- tap ----------------------------------------------------------------------


def test_tap(kb: Keyboard, client: _FakeClient) -> None:
    kb.tap(Keycode.A)
    assert not kb.is_pressed(Keycode.A)
    assert len(client.calls) == 2


# -- payload structure --------------------------------------------------------


def test_payload_has_keyboard_report_id(kb: Keyboard, client: _FakeClient) -> None:
    kb.press(Keycode.A)
    assert client.last_payload[0] == KEYBOARD
    assert len(client.last_payload) == 1 + 8  # report_id + 8 report bytes


def test_payload_structure(kb: Keyboard, client: _FakeClient) -> None:
    kb.press(Keycode.LEFT_SHIFT, Keycode.B)
    p = client.last_payload
    assert p[1] == 0x02  # modifier
    assert p[2] == 0x00  # reserved
    assert p[3] == 0x05  # B
    assert all(b == 0 for b in p[4:])


# -- LED state (Boot Keyboard OUTPUT report) ----------------------------------


def test_led_initial_state(kb: Keyboard) -> None:
    assert kb.led_byte == 0
    assert not kb.num_lock_on
    assert not kb.caps_lock_on
    assert not kb.scroll_lock_on
    assert not kb.compose_on
    assert not kb.kana_on


def test_handle_host_event_led(kb: Keyboard) -> None:
    ev = HostEventReceived(
        report_id=KEYBOARD,
        report_type=HidReportType.OUTPUT,
        data=bytes([0x02]),  # CapsLock = bit 1
    )
    kb.handle_host_event(ev)
    assert kb.led_byte == 0x02
    assert not kb.num_lock_on
    assert kb.caps_lock_on
    assert not kb.scroll_lock_on


def test_handle_host_event_all_leds(kb: Keyboard) -> None:
    ev = HostEventReceived(
        report_id=KEYBOARD,
        report_type=HidReportType.OUTPUT,
        data=bytes([0x07]),  # NumLock + CapsLock + ScrollLock
    )
    kb.handle_host_event(ev)
    assert kb.num_lock_on
    assert kb.caps_lock_on
    assert kb.scroll_lock_on


def test_handle_host_event_ignores_non_keyboard(kb: Keyboard) -> None:
    """Only KEYBOARD report ID with OUTPUT type updates LED state."""
    ev = HostEventReceived(
        report_id=99,
        report_type=HidReportType.OUTPUT,
        data=bytes([0xFF]),
    )
    kb.handle_host_event(ev)
    assert kb.led_byte == 0  # unchanged


def test_handle_host_event_ignores_input(kb: Keyboard) -> None:
    """INPUT reports should not change LED state."""
    ev = HostEventReceived(
        report_id=KEYBOARD,
        report_type=HidReportType.INPUT,
        data=bytes([0xFF]),
    )
    kb.handle_host_event(ev)
    assert kb.led_byte == 0


# -- IHidClient protocol ------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")


# -- Keycode enum -------------------------------------------------------------


def test_keycode_is_modifier() -> None:
    assert Keycode.LEFT_CONTROL.is_modifier
    assert Keycode.RIGHT_GUI.is_modifier
    assert not Keycode.A.is_modifier
    assert not Keycode.F1.is_modifier


def test_modifier_bit_mapping() -> None:
    assert Keycode.LEFT_CONTROL.modifier_bit() == 0x01
    assert Keycode.LEFT_SHIFT.modifier_bit() == 0x02
    assert Keycode.LEFT_ALT.modifier_bit() == 0x04
    assert Keycode.LEFT_GUI.modifier_bit() == 0x08
    assert Keycode.RIGHT_CONTROL.modifier_bit() == 0x10
    assert Keycode.RIGHT_SHIFT.modifier_bit() == 0x20
    assert Keycode.RIGHT_ALT.modifier_bit() == 0x40
    assert Keycode.RIGHT_GUI.modifier_bit() == 0x80


def test_keycode_wire_values() -> None:
    """Spot-check HUT §10 conformance."""
    assert Keycode.A == 0x04
    assert Keycode.Z == 0x1D
    assert Keycode.ONE == 0x1E
    assert Keycode.ZERO == 0x27
    assert Keycode.RETURN == 0x28
    assert Keycode.ESCAPE == 0x29
    assert Keycode.SPACEBAR == 0x2C
    assert Keycode.F1 == 0x3A
    assert Keycode.F12 == 0x45
    assert Keycode.UP_ARROW == 0x52
    assert Keycode.LEFT_CONTROL == 0xE0
    assert Keycode.RIGHT_GUI == 0xE7
