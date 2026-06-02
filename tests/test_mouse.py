"""Tests for Mouse class (boot-mouse 5-byte relative report)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Mouse, MouseButton
from core.reports import MOUSE, ReportTable


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
def mouse(client: _FakeClient, table: ReportTable) -> Mouse:
    return Mouse(client, table)


# -- movement ----------------------------------------------------------------


def test_move_sends_reliable(mouse: Mouse, client: _FakeClient) -> None:
    mouse.move(x=10, y=-5)
    _, _, reliable = client.last
    assert reliable is True  # mouse is RELATIVE → MUST use reliable


def test_move_payload(mouse: Mouse, client: _FakeClient) -> None:
    mouse.move(x=10, y=-5)
    p = client.last[1]
    assert p[0] == MOUSE                           # report ID
    assert p[1] == 0x00                            # buttons
    assert _s8(p[2]) == 10                         # X
    assert _s8(p[3]) == -5                         # Y
    assert p[4] == 0 and p[5] == 0                 # wheel, pan
    assert len(p) == 1 + 5                         # report_id + 5 bytes


def test_scroll(mouse: Mouse, client: _FakeClient) -> None:
    mouse.scroll(wheel=-1, pan=3)
    p = client.last[1]
    assert _s8(p[4]) == -1   # wheel
    assert _s8(p[5]) == 3    # pan


def test_move_clamps_values(mouse: Mouse, client: _FakeClient) -> None:
    mouse.move(x=200, y=-200)
    p = client.last[1]
    assert _s8(p[2]) == 127
    assert _s8(p[3]) == -127


# -- buttons -----------------------------------------------------------------


def test_press_button(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT)
    p = client.last[1]
    assert p[1] == 0x01  # left button bit
    assert mouse.is_pressed(MouseButton.LEFT)
    assert not mouse.is_pressed(MouseButton.RIGHT)


def test_release_button(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT)
    mouse.release(MouseButton.LEFT)
    assert client.last[1][1] == 0x00  # no buttons
    assert not mouse.is_pressed(MouseButton.LEFT)


def test_multiple_buttons(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT, MouseButton.RIGHT)
    assert client.last[1][1] == 0x03  # bits 0 + 1
    assert mouse.is_pressed(MouseButton.LEFT)
    assert mouse.is_pressed(MouseButton.RIGHT)


def test_release_one_keeps_other(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT, MouseButton.RIGHT)
    mouse.release(MouseButton.LEFT)
    assert client.last[1][1] == 0x02  # only right remains
    assert not mouse.is_pressed(MouseButton.LEFT)
    assert mouse.is_pressed(MouseButton.RIGHT)


def test_click(mouse: Mouse, client: _FakeClient) -> None:
    n = len(client.calls)
    mouse.click(MouseButton.MIDDLE)
    assert len(client.calls) == n + 2  # press + release
    assert not mouse.is_pressed(MouseButton.MIDDLE)


def test_release_all(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE)
    assert mouse.buttons == 0x07
    mouse.release_all()
    assert mouse.buttons == 0
    assert client.last[1][1] == 0x00


# -- hold (drag) -------------------------------------------------------------


def test_hold_context(mouse: Mouse, client: _FakeClient) -> None:
    with mouse.hold(MouseButton.LEFT):
        assert mouse.is_pressed(MouseButton.LEFT)
        mouse.move(x=100, y=0)
        # the move should include the button
        assert client.last[1][1] == 0x01
        assert _s8(client.last[1][2]) == 100

    # after exit: button released
    assert not mouse.is_pressed(MouseButton.LEFT)
    assert client.last[1][1] == 0x00


def test_hold_multiple_buttons(mouse: Mouse, client: _FakeClient) -> None:
    with mouse.hold(MouseButton.LEFT, MouseButton.RIGHT):
        assert mouse.buttons == 0x03
    assert mouse.buttons == 0x00


# -- movement preserves button state -----------------------------------------


def test_move_after_press_keeps_button(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.RIGHT)
    mouse.move(x=5, y=10)
    p = client.last[1]
    assert p[1] == 0x02  # button held
    assert _s8(p[2]) == 5


# -- no-op guards ------------------------------------------------------------


def test_press_no_args_noop(mouse: Mouse, client: _FakeClient) -> None:
    n = len(client.calls)
    mouse.press()  # no buttons = no-op
    assert len(client.calls) == n


def test_release_no_args_noop(mouse: Mouse, client: _FakeClient) -> None:
    n = len(client.calls)
    mouse.release()
    assert len(client.calls) == n


def test_press_already_pressed_noop(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT)
    n = len(client.calls)
    mouse.press(MouseButton.LEFT)  # already held → no-op
    assert len(client.calls) == n


def test_release_not_pressed_noop(mouse: Mouse, client: _FakeClient) -> None:
    n = len(client.calls)
    mouse.release(MouseButton.RIGHT)  # not pressed → no-op
    assert len(client.calls) == n


def test_release_all_when_empty_noop(mouse: Mouse, client: _FakeClient) -> None:
    n = len(client.calls)
    mouse.release_all()
    assert len(client.calls) == n  # nothing to release


# -- scroll preserves button state -------------------------------------------


def test_scroll_preserves_buttons(mouse: Mouse, client: _FakeClient) -> None:
    mouse.press(MouseButton.LEFT)
    mouse.scroll(wheel=-2, pan=1)
    p = client.last[1]
    assert p[1] == 0x01               # LEFT still held
    assert _s8(p[4]) == -2            # wheel
    assert _s8(p[5]) == 1             # pan


# -- MouseButton -------------------------------------------------------------


def test_button_bits() -> None:
    assert MouseButton.LEFT.bit() == 0x01
    assert MouseButton.RIGHT.bit() == 0x02
    assert MouseButton.MIDDLE.bit() == 0x04
    assert MouseButton.BACK.bit() == 0x08
    assert MouseButton.FORWARD.bit() == 0x10


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")


# -- helpers -----------------------------------------------------------------


def _s8(b: int) -> int:
    """Interpret unsigned byte as signed int8."""
    return b - 256 if b >= 128 else b
