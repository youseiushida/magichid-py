"""Tests for Gamepad class (6-byte report, dual sticks, 12 buttons, 8-way D-pad)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Gamepad, GamepadButton, GamepadDPad
from core.reports import ReportTable


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
def pad(client: _FakeClient, table: ReportTable) -> Gamepad:
    return Gamepad(client, table)


# -- helpers -----------------------------------------------------------------

def _approx(f: float) -> float:
    """128/255 ≈ 0.502, not exactly 0.5."""
    return pytest.approx(f, abs=0.01)


# -- basic press / release ---------------------------------------------------


def test_press_button(pad: Gamepad, client: _FakeClient) -> None:
    pad.press(GamepadButton.SOUTH)
    assert pad.is_pressed(GamepadButton.SOUTH)
    p = client.last[1]
    assert p[0] == 5                   # report ID
    assert p[1] == 0x01                # SOUTH (button 1) → bit 0


def test_release_button(pad: Gamepad, client: _FakeClient) -> None:
    pad.press(GamepadButton.SOUTH)
    pad.release(GamepadButton.SOUTH)
    assert not pad.is_pressed(GamepadButton.SOUTH)
    assert client.last[1][1] == 0x00


def test_multiple_buttons(pad: Gamepad, client: _FakeClient) -> None:
    pad.press(GamepadButton.SOUTH, GamepadButton.EAST, GamepadButton.L1)
    assert client.last[1][1] == 0x13  # bits 0, 1, 4


def test_high_button(pad: Gamepad, client: _FakeClient) -> None:
    """Buttons 9+ go to byte 2 (buttons_high) bits 0-3."""
    pad.press(GamepadButton.START)   # button 10 → bit 9 → byte 2 bit 1
    b_high = client.last[1][2]
    assert (b_high & 0x02) == 0x02   # START bit present


def test_click(pad: Gamepad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.click(GamepadButton.NORTH)
    assert len(client.calls) == n + 2
    assert not pad.is_pressed(GamepadButton.NORTH)


def test_release_all(pad: Gamepad) -> None:
    pad.press(GamepadButton.SOUTH, GamepadButton.L1)
    pad.set_stick(left_x=1.0, left_y=0.0)
    pad.set_dpad(GamepadDPad.UP)
    pad.release_all()
    assert pad.buttons == 0
    assert pad.left_stick == (_approx(0.5), _approx(0.5))
    assert pad.dpad == 0x0F


# -- no-op guards ------------------------------------------------------------


def test_press_no_args_noop(pad: Gamepad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.press()
    assert len(client.calls) == n


def test_press_already_pressed_noop(pad: Gamepad, client: _FakeClient) -> None:
    pad.press(GamepadButton.SOUTH)
    n = len(client.calls)
    pad.press(GamepadButton.SOUTH)
    assert len(client.calls) == n


def test_release_not_pressed_noop(pad: Gamepad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.release(GamepadButton.L2)
    assert len(client.calls) == n


# -- sticks ------------------------------------------------------------------


def test_set_stick(pad: Gamepad, client: _FakeClient) -> None:
    pad.set_stick(left_x=1.0, left_y=0.0)
    p = client.last[1]
    assert p[3] == 0xFF  # lx: 1.0 → 255
    assert p[4] == 0x00  # ly: 0.0 → 0
    assert p[5] == 0x80  # rx unchanged (center)
    assert p[6] == 0x80  # ry unchanged


def test_set_stick_partial(pad: Gamepad) -> None:
    """Only changed axes are updated."""
    pad.set_stick(left_x=0.0)
    assert pad.left_stick == (_approx(0.0), _approx(0.5))


def test_stick_clamp(pad: Gamepad, client: _FakeClient) -> None:
    pad.set_stick(left_x=2.0, left_y=-1.0)
    p = client.last[1]
    assert p[3] == 0xFF  # clamped to 1.0
    assert p[4] == 0x00  # clamped to 0.0


def test_set_stick_no_args_noop(pad: Gamepad, client: _FakeClient) -> None:
    n = len(client.calls)
    pad.set_stick()
    assert len(client.calls) == n


def test_release_all_neutral_noop(pad: Gamepad, client: _FakeClient) -> None:
    """Calling release_all on a fresh gamepad should not send anything."""
    n = len(client.calls)
    pad.release_all()
    assert len(client.calls) == n


def test_stick_query(pad: Gamepad) -> None:
    pad.set_stick(left_x=0.0, left_y=1.0)
    assert pad.left_stick == (_approx(0.0), _approx(1.0))
    assert pad.right_stick == (_approx(0.5), _approx(0.5))


# -- dpad --------------------------------------------------------------------


def test_set_dpad(pad: Gamepad, client: _FakeClient) -> None:
    """Set non-center to ensure a report is sent."""
    pad.set_dpad(GamepadDPad.RIGHT)
    p = client.last[1]
    # dpad in byte 2 (buttons_high) bits 4-7
    assert (p[2] >> 4) & 0x0F == 2   # RIGHT = 2


def test_dpad_center_default(pad: Gamepad) -> None:
    """Default D-pad is CENTER (0x0F)."""
    assert pad.dpad == 0x0F


def test_dpad_center_after_active(pad: Gamepad, client: _FakeClient) -> None:
    """Setting CENTER after UP sends a report."""
    pad.set_dpad(GamepadDPad.UP)
    pad.set_dpad(GamepadDPad.CENTER)
    assert (client.last[1][2] >> 4) & 0x0F == 0x0F


def test_dpad_same_direction_noop(pad: Gamepad, client: _FakeClient) -> None:
    pad.set_dpad(GamepadDPad.DOWN)
    n = len(client.calls)
    pad.set_dpad(GamepadDPad.DOWN)
    assert len(client.calls) == n


# -- reliable flag -----------------------------------------------------------


def test_gamepad_sends_reliable(pad: Gamepad, client: _FakeClient) -> None:
    pad.press(GamepadButton.SOUTH)
    _, _, reliable = client.last
    assert reliable is True  # RELATIVE → MUST use reliable


# -- payload structure -------------------------------------------------------


def test_payload_length(pad: Gamepad, client: _FakeClient) -> None:
    pad.set_stick(left_x=0.5, left_y=0.5)
    assert len(client.last[1]) == 1 + 6  # report_id + 6 bytes


# -- GamepadButton enum ------------------------------------------------------


def test_button_bits() -> None:
    assert GamepadButton.SOUTH.bit() == 0x01
    assert GamepadButton.EAST.bit() == 0x02
    assert GamepadButton.WEST.bit() == 0x04
    assert GamepadButton.NORTH.bit() == 0x08
    assert GamepadButton.L1.bit() == 0x10
    assert GamepadButton.START.bit() == 0x200  # button 10 → bit 9


# -- GamepadDPad enum --------------------------------------------------------


def test_dpad_values() -> None:
    assert GamepadDPad.UP == 0
    assert GamepadDPad.DOWN == 4
    assert GamepadDPad.CENTER == 0x0F


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
