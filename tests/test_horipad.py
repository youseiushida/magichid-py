"""Tests for Horipad class (profile 1, Nintendo Switch wired gamepad)."""

from __future__ import annotations

import pytest

from hid import IHidClient
from hid.horipad.controller import (
    Horipad, HoripadButton, HoripadDpad,
    _NEUTRAL, _float_to_stick, _stick_to_float, _clamp_u8,
)
from core.reports import ReportTable
from core.wire import MsgType


# ---------------------------------------------------------------------------
# Fake client
# ---------------------------------------------------------------------------


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
    return ReportTable.horipad()


@pytest.fixture
def pad(client: _FakeClient, table: ReportTable) -> Horipad:
    return Horipad(client, table)


# ---------------------------------------------------------------------------
# Spec examples — wire format
# ---------------------------------------------------------------------------


def test_neutral_matches_spec(pad: Horipad, client: _FakeClient) -> None:
    """spec/horipad.md neutral: 00 00 0F 80 80 80 80 00"""
    pad.release_all()                            # forces a flush
    p = client.last[1]
    assert p == _NEUTRAL                         # bare 8 bytes, no report_id
    assert p.hex() == "00000f8080808000"


def test_press_a(pad: Horipad, client: _FakeClient) -> None:
    """spec/horipad.md: Press A (bit 2) → 04 00 0F 80 80 80 80 00"""
    pad.press(HoripadButton.A)
    p = client.last[1]
    assert p[0] == 0x04                          # A = bit 2 in byte 0
    assert p[1] == 0x00                          # buttons high
    assert p[2] == 0x0F                          # dpad centre
    assert p[3:] == bytes([0x80, 0x80, 0x80, 0x80, 0x00])


def test_a_plus_stick_right(pad: Horipad, client: _FakeClient) -> None:
    """spec/horipad.md: A + left stick fully right → 04 00 0F FF 80 80 80 00"""
    pad.press(HoripadButton.A)
    pad.set_stick_left_raw(x=0xFF)
    p = client.last[1]
    assert p[0] == 0x04
    assert p[3] == 0xFF                          # LX fully right
    assert p[4] == 0x80                          # LY centre


# ---------------------------------------------------------------------------
# SEND_REPORT — payload has no report_id byte
# ---------------------------------------------------------------------------


def test_payload_is_bare_eight_bytes(pad: Horipad, client: _FakeClient) -> None:
    """HORIPAD descriptor has no Report ID — payload is exactly 8 bytes."""
    pad.press(HoripadButton.B)
    p = client.last[1]
    assert len(p) == 8
    # SEND_REPORT with report_id=0 means no report-id byte on the wire
    _, payload, _ = client.last
    assert payload == pad._table.pad_input(0, p)


def test_send_report_type(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A)
    t, _, _ = client.last
    assert t == MsgType.SEND_REPORT


def test_send_not_reliable(pad: Horipad, client: _FakeClient) -> None:
    """All horipad fields are absolute — fire-and-forget is safe."""
    pad.press(HoripadButton.A)
    _, _, reliable = client.last
    assert reliable is False


# ---------------------------------------------------------------------------
# Buttons — press / release / state tracking
# ---------------------------------------------------------------------------


def test_press_button_sets_bit(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A)
    assert pad.is_pressed(HoripadButton.A)
    assert pad.buttons == HoripadButton.A.bit()
    assert client.last[1][0] == 0x04             # bit 2


def test_press_multiple_buttons(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A, HoripadButton.B, HoripadButton.X, HoripadButton.Y)
    # bits 0,1,2,3 → 0x0F
    assert client.last[1][0] == 0x0F
    assert client.last[1][1] == 0x00
    assert pad.buttons == 0x000F


def test_high_bit_button(pad: Horipad, client: _FakeClient) -> None:
    """PLUS is bit 9 → byte 1, bit 1."""
    pad.press(HoripadButton.PLUS)
    assert client.last[1][0] == 0x00             # byte 0 empty
    assert client.last[1][1] == 0x02             # bit 1 in byte 1
    assert pad.is_pressed(HoripadButton.PLUS)


def test_all_high_buttons(pad: Horipad, client: _FakeClient) -> None:
    """All buttons in byte 1 (bits 8-13)."""
    pad.press(
        HoripadButton.MINUS, HoripadButton.PLUS,
        HoripadButton.L_STICK, HoripadButton.R_STICK,
        HoripadButton.HOME, HoripadButton.CAPTURE,
    )
    # bits 8-13 → byte 1 = 0x3F
    assert client.last[1][1] == 0x3F
    assert client.last[1][0] == 0x00


def test_release_button(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A)
    pad.release(HoripadButton.A)
    assert client.last[1][0] == 0x00
    assert not pad.is_pressed(HoripadButton.A)


def test_release_one_keeps_others(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A, HoripadButton.B)
    pad.release(HoripadButton.A)
    assert client.last[1][0] == 0x02              # only B remains
    assert not pad.is_pressed(HoripadButton.A)
    assert pad.is_pressed(HoripadButton.B)


def test_tap(pad: Horipad, client: _FakeClient) -> None:
    """Tap = press + release, final state has no button held."""
    n = len(client.calls)
    pad.tap(HoripadButton.X)
    assert len(client.calls) == n + 2             # press + release
    assert not pad.is_pressed(HoripadButton.X)
    assert client.last[1][0] == 0x00


def test_hold_context(pad: Horipad, client: _FakeClient) -> None:
    with pad.hold(HoripadButton.ZL):
        assert pad.is_pressed(HoripadButton.ZL)
        pad.set_stick_left(x=1.0)
        # the move should include the button
        assert client.last[1][0] == 0x40          # ZL = bit 6
    # after exit: button released
    assert not pad.is_pressed(HoripadButton.ZL)
    assert client.last[1][0] == 0x00


def test_hold_multiple_buttons(pad: Horipad, client: _FakeClient) -> None:
    with pad.hold(HoripadButton.A, HoripadButton.B):
        assert pad.buttons == 0x0006              # bits 1+2
    assert pad.buttons == 0x0000


# ---------------------------------------------------------------------------
# No-op guards
# ---------------------------------------------------------------------------


def test_press_no_args_noop(pad: Horipad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.press()
    assert len(client.calls) == n


def test_release_no_args_noop(pad: Horipad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.release()
    assert len(client.calls) == n


def test_press_already_pressed_noop(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A)
    n = len(client.calls)
    pad.press(HoripadButton.A)                   # already held
    assert len(client.calls) == n


def test_buttons_unchanged_no_flush(pad: Horipad, client: _FakeClient) -> None:
    """press+release of same button in sequence = no net change."""
    pad.press(HoripadButton.A)                   # this flushes
    n = len(client.calls)
    pad.release(HoripadButton.L)                 # L not pressed → no state change → no flush
    assert len(client.calls) == n


# ---------------------------------------------------------------------------
# release_all
# ---------------------------------------------------------------------------


def test_release_all_resets_everything(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A, HoripadButton.B)
    pad.set_dpad(HoripadDpad.UP)
    pad.set_stick_left(x=0.5, y=-0.5)
    pad.set_stick_right(x=1.0, y=0.0)
    pad.release_all()

    p = client.last[1]
    assert p == _NEUTRAL
    assert pad.buttons == 0
    assert pad.dpad == HoripadDpad.CENTER
    assert pad.stick_left == (0.0, 0.0)
    assert pad.stick_right == (0.0, 0.0)


def test_release_all_when_empty_still_sends(pad: Horipad, client: _FakeClient) -> None:
    """release_all always flushes, even if nothing is held."""
    # _dirty is False initially; release_all sets everything and flushes unconditionally
    pad.release_all()
    assert client.last[1] == _NEUTRAL


# ---------------------------------------------------------------------------
# D-pad
# ---------------------------------------------------------------------------


def test_dpad_values(pad: Horipad, client: _FakeClient) -> None:
    directions = [
        (HoripadDpad.UP, 0x00),
        (HoripadDpad.UP_RIGHT, 0x01),
        (HoripadDpad.RIGHT, 0x02),
        (HoripadDpad.DOWN_RIGHT, 0x03),
        (HoripadDpad.DOWN, 0x04),
        (HoripadDpad.DOWN_LEFT, 0x05),
        (HoripadDpad.LEFT, 0x06),
        (HoripadDpad.UP_LEFT, 0x07),
        (HoripadDpad.CENTER, 0x0F),
    ]
    for direction, expected in directions:
        pad.set_dpad(direction)
        assert client.last[1][2] == expected


def test_clear_dpad(pad: Horipad, client: _FakeClient) -> None:
    pad.set_dpad(HoripadDpad.DOWN)
    assert client.last[1][2] == 0x04
    pad.clear_dpad()
    assert client.last[1][2] == 0x0F


def test_dpad_property_returns_enum(pad: Horipad) -> None:
    """dpad property returns HoripadDpad enum when valid, None when unknown."""
    pad.set_dpad(HoripadDpad.UP)
    assert pad.dpad == HoripadDpad.UP
    pad.clear_dpad()
    assert pad.dpad == HoripadDpad.CENTER


# ---------------------------------------------------------------------------
# Sticks — normalised float
# ---------------------------------------------------------------------------


def test_stick_float_centre(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_left(x=0.0, y=0.0)
    assert client.last[1][3] == 0x80              # LX centre
    assert client.last[1][4] == 0x80              # LY centre


def test_stick_float_extremes(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_left(x=1.0, y=-1.0)
    assert client.last[1][3] == 0xFF              # max right
    assert client.last[1][4] == 0x00              # max up


def test_stick_float_clamps(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_right(x=2.0, y=-2.0)
    assert client.last[1][5] == 0xFF              # clamped to max
    assert client.last[1][6] == 0x00              # clamped to min


def test_stick_float_readback(pad: Horipad) -> None:
    pad.set_stick_left(x=0.5, y=-0.25)
    px, py = pad.stick_left
    assert 0.49 < px < 0.51
    assert -0.26 < py < -0.24


def test_centre_sticks(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_left(x=0.8, y=-0.3)
    pad.set_stick_right(x=-1.0, y=1.0)
    pad.centre_sticks()
    p = client.last[1]
    assert p[3] == 0x80 and p[4] == 0x80          # left centred
    assert p[5] == 0x80 and p[6] == 0x80          # right centred


def test_set_stick_left_only_x_preserves_y(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_left(x=0.0, y=0.5)              # initial
    pad.set_stick_left(x=-1.0, y=0.5)             # only change x, preserve y
    p = client.last[1]
    assert p[3] == 0x00                           # x = -1.0 → 0x00
    assert p[4] == 0xC0                           # y still 0.5 → ~0xC0


# ---------------------------------------------------------------------------
# Sticks — raw
# ---------------------------------------------------------------------------


def test_stick_raw(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_left_raw(x=0x00, y=0xFF)
    assert client.last[1][3] == 0x00
    assert client.last[1][4] == 0xFF


def test_stick_raw_clamps(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_right_raw(x=300, y=-10)
    assert client.last[1][5] == 255
    assert client.last[1][6] == 0


def test_stick_raw_readback(pad: Horipad) -> None:
    pad.set_stick_left_raw(x=0x40, y=0xC0)
    assert pad.stick_left_raw == (0x40, 0xC0)


# ---------------------------------------------------------------------------
# Batch context
# ---------------------------------------------------------------------------


def test_batch_defers_flush(pad: Horipad, client: _FakeClient) -> None:
    with pad.batch():
        pad.press(HoripadButton.A)
        pad.press(HoripadButton.B)
        # no calls yet
        assert len(client.calls) == 0
    # one flush on exit
    assert len(client.calls) == 1
    assert client.last[1][0] == 0x06               # A(0x04) + B(0x02)


def test_batch_no_change_no_flush(pad: Horipad, client: _FakeClient) -> None:
    n = len(client.calls)
    with pad.batch():
        pass                                       # nothing changed
    assert len(client.calls) == n                  # no flush


def test_batch_press_release_same_button_no_net_change(pad: Horipad, client: _FakeClient) -> None:
    """Pressing and releasing the same button within a batch — state is neutral."""
    with pad.batch():
        pad.press(HoripadButton.A)
        pad.release(HoripadButton.A)
    # flushes once on exit (dirty was set), but final state is neutral
    assert len(client.calls) == 1
    assert client.last[1] == _NEUTRAL
    assert pad.buttons == 0


# ---------------------------------------------------------------------------
# Button enum
# ---------------------------------------------------------------------------


def test_button_enum_values() -> None:
    assert HoripadButton.Y == 0
    assert HoripadButton.A == 2
    assert HoripadButton.ZR == 7
    assert HoripadButton.MINUS == 8
    assert HoripadButton.HOME == 12
    assert HoripadButton.CAPTURE == 13


def test_button_enum_bit() -> None:
    assert HoripadButton.Y.bit() == 0x0001
    assert HoripadButton.B.bit() == 0x0002
    assert HoripadButton.A.bit() == 0x0004
    assert HoripadButton.X.bit() == 0x0008
    assert HoripadButton.L.bit() == 0x0010
    assert HoripadButton.R.bit() == 0x0020
    assert HoripadButton.ZL.bit() == 0x0040
    assert HoripadButton.ZR.bit() == 0x0080
    assert HoripadButton.MINUS.bit() == 0x0100
    assert HoripadButton.PLUS.bit() == 0x0200
    assert HoripadButton.L_STICK.bit() == 0x0400
    assert HoripadButton.R_STICK.bit() == 0x0800
    assert HoripadButton.HOME.bit() == 0x1000
    assert HoripadButton.CAPTURE.bit() == 0x2000


def test_button_enum_count() -> None:
    assert len(HoripadButton) == 14                # spec: 14 buttons (bits 0-13)


# ---------------------------------------------------------------------------
# D-pad enum
# ---------------------------------------------------------------------------


def test_dpad_enum_values() -> None:
    assert HoripadDpad.UP == 0
    assert HoripadDpad.RIGHT == 2
    assert HoripadDpad.DOWN == 4
    assert HoripadDpad.LEFT == 6
    assert HoripadDpad.CENTER == 0x0F


def test_dpad_enum_count() -> None:
    assert len(HoripadDpad) == 9                   # 8 directions + centre


# ---------------------------------------------------------------------------
# Stick conversion helpers
# ---------------------------------------------------------------------------


def test_float_to_stick_round_trip() -> None:
    """Every raw value must round-trip through float and back."""
    for raw in range(0x100):
        f = _stick_to_float(raw)
        r = _float_to_stick(f)
        assert r == raw, f"round-trip failed at raw=0x{raw:02X}: float={f}, back={r}"


def test_stick_float_edges() -> None:
    # raw 0x00 → -1.0
    assert _stick_to_float(0x00) == -1.0
    # raw 0x80 → 0.0
    assert _stick_to_float(0x80) == 0.0
    # raw 0xFF → 1.0
    assert _stick_to_float(0xFF) == 1.0


def test_clamp_u8() -> None:
    assert _clamp_u8(-1) == 0
    assert _clamp_u8(0) == 0
    assert _clamp_u8(128) == 128
    assert _clamp_u8(255) == 255
    assert _clamp_u8(256) == 255


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(MsgType.SEND_REPORT, b"\x00")


# ---------------------------------------------------------------------------
# Movement preserves button/dpad state (full-state principle)
# ---------------------------------------------------------------------------


def test_move_preserves_buttons(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.L, HoripadButton.R)
    pad.set_stick_left(x=0.3, y=-0.7)
    p = client.last[1]
    assert p[0] == 0x30                            # L + R = bits 4+5
    assert p[3] != 0x80                            # stick moved


def test_dpad_preserves_buttons(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.ZL, HoripadButton.ZR)
    pad.set_dpad(HoripadDpad.DOWN)
    p = client.last[1]
    assert p[0] == 0xC0                            # ZL + ZR = bits 6+7
    assert p[2] == 0x04                            # DOWN


def test_button_action_preserves_stick(pad: Horipad, client: _FakeClient) -> None:
    pad.set_stick_right(x=-0.5, y=0.8)
    pad.press(HoripadButton.A)
    p = client.last[1]
    assert p[0] == 0x04                            # A pressed
    assert p[5] != 0x80                            # right stick still held


# ---------------------------------------------------------------------------
# vendor byte
# ---------------------------------------------------------------------------


def test_vendor_byte_always_zero(pad: Horipad, client: _FakeClient) -> None:
    pad.press(HoripadButton.A)
    pad.set_stick_left(x=1.0, y=1.0)
    pad.set_stick_right(x=-1.0, y=-1.0)
    assert client.last[1][7] == 0x00

    pad.release_all()
    assert client.last[1][7] == 0x00
