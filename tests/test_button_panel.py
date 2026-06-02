"""Tests for ButtonPanel class (1-byte button bitmap, report ID 9)."""

from __future__ import annotations

import pytest

from hid import IHidClient, ButtonPanel, PanelButton
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
def panel(client: _FakeClient, table: ReportTable) -> ButtonPanel:
    return ButtonPanel(client, table)


# -- basic press / release ---------------------------------------------------


def test_press_single_button(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1)
    assert panel.is_pressed(PanelButton.B1)
    assert client.last[1][1] == 0x01  # payload byte 1 = state bitmap


def test_release_button(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1)
    panel.release(PanelButton.B1)
    assert not panel.is_pressed(PanelButton.B1)
    assert client.last[1][1] == 0x00


def test_multiple_buttons(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1, PanelButton.B3, PanelButton.B5)
    assert client.last[1][1] == 0x15  # bits 0, 2, 4
    assert panel.pressed_count == 3


def test_release_one_keeps_others(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1, PanelButton.B2, PanelButton.B3)
    panel.release(PanelButton.B2)
    assert client.last[1][1] == 0x05  # bits 0 and 2 remain
    assert panel.pressed_count == 2


def test_click(panel: ButtonPanel, client: _FakeClient) -> None:
    n = len(client.calls)
    panel.click(PanelButton.B4)
    assert len(client.calls) == n + 2  # press + release
    assert not panel.is_pressed(PanelButton.B4)


def test_release_all(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1, PanelButton.B2, PanelButton.B3)
    assert panel.state == 0x07
    panel.release_all()
    assert panel.state == 0
    assert panel.pressed_count == 0


# -- no-op guards ------------------------------------------------------------


def test_press_no_args_noop(panel: ButtonPanel, client: _FakeClient) -> None:
    n = len(client.calls)
    panel.press()
    assert len(client.calls) == n


def test_release_no_args_noop(panel: ButtonPanel, client: _FakeClient) -> None:
    n = len(client.calls)
    panel.release()
    assert len(client.calls) == n


def test_press_already_pressed_noop(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1)
    n = len(client.calls)
    panel.press(PanelButton.B1)
    assert len(client.calls) == n


def test_release_not_pressed_noop(panel: ButtonPanel, client: _FakeClient) -> None:
    n = len(client.calls)
    panel.release(PanelButton.B5)
    assert len(client.calls) == n


def test_release_all_when_empty_noop(panel: ButtonPanel, client: _FakeClient) -> None:
    n = len(client.calls)
    panel.release_all()
    assert len(client.calls) == n


# -- payload structure -------------------------------------------------------


def test_payload_report_id(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B1)
    assert client.last[1][0] == 9  # REPORT_ID_BUTTON


def test_payload_is_one_byte_padded(panel: ButtonPanel, client: _FakeClient) -> None:
    """Button report in_len=1, so payload = [report_id][1 byte]."""
    panel.press(PanelButton.B1)
    assert len(client.last[1]) == 1 + 1  # report_id + 1 byte


def test_payload_state_byte(panel: ButtonPanel, client: _FakeClient) -> None:
    panel.press(PanelButton.B8)  # bit 7 → 0x80
    assert client.last[1][1] == 0x80


# -- reliable flag -----------------------------------------------------------


def test_button_not_reliable(panel: ButtonPanel, client: _FakeClient) -> None:
    """Button report is not relative → reliable=False."""
    panel.press(PanelButton.B1)
    _, _, reliable = client.last
    assert reliable is False


# -- PanelButton enum --------------------------------------------------------


def test_button_bits() -> None:
    assert PanelButton.B1.bit() == 0x01
    assert PanelButton.B2.bit() == 0x02
    assert PanelButton.B3.bit() == 0x04
    assert PanelButton.B4.bit() == 0x08
    assert PanelButton.B5.bit() == 0x10
    assert PanelButton.B6.bit() == 0x20
    assert PanelButton.B7.bit() == 0x40
    assert PanelButton.B8.bit() == 0x80


def test_button_values() -> None:
    assert PanelButton.B1 == 1
    assert PanelButton.B8 == 8


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
