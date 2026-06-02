"""Tests for ConsumerControl class (2-byte Consumer Page, report ID 12)."""

from __future__ import annotations

import pytest

from hid import IHidClient, ConsumerControl, ConsumerUsage
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
def cc(client: _FakeClient, table: ReportTable) -> ConsumerControl:
    return ConsumerControl(client, table)


# -- basic press / release ---------------------------------------------------


def test_press_sends_usage(cc: ConsumerControl, client: _FakeClient) -> None:
    cc.press(ConsumerUsage.PLAY)
    assert cc.is_active
    assert cc.current == 0x00B0
    p = client.last[1]
    assert p[0] == 12               # report ID
    assert p[1] == 0xB0             # low byte
    assert p[2] == 0x00             # high byte


def test_press_16bit_usage(cc: ConsumerControl, client: _FakeClient) -> None:
    """High-byte usages (0x0200+) send both bytes correctly."""
    cc.press(ConsumerUsage.AC_BACK)  # 0x0224
    p = client.last[1]
    assert p[1] == 0x24             # low
    assert p[2] == 0x02             # high


def test_release_sends_zero(cc: ConsumerControl, client: _FakeClient) -> None:
    cc.press(ConsumerUsage.PLAY)
    cc.release()
    assert not cc.is_active
    assert cc.current == 0
    p = client.last[1]
    assert p[1] == 0x00
    assert p[2] == 0x00


def test_tap(cc: ConsumerControl, client: _FakeClient) -> None:
    n = len(client.calls)
    cc.tap(ConsumerUsage.MUTE)
    assert len(client.calls) == n + 2  # press + release
    assert not cc.is_active


def test_release_when_idle_noop(cc: ConsumerControl, client: _FakeClient) -> None:
    n = len(client.calls)
    cc.release()
    assert len(client.calls) == n


# -- press switching ---------------------------------------------------------


def test_press_new_key_replaces_old(cc: ConsumerControl, client: _FakeClient) -> None:
    cc.press(ConsumerUsage.VOLUME_INCREMENT)
    cc.press(ConsumerUsage.VOLUME_DECREMENT)  # replaces, no release needed
    assert cc.current == 0x00EA
    # should send the new usage, not intermediate release
    p = client.last[1]
    assert p[1] == 0xEA


def test_press_same_key_noop(cc: ConsumerControl, client: _FakeClient) -> None:
    cc.press(ConsumerUsage.PLAY_PAUSE)
    n = len(client.calls)
    cc.press(ConsumerUsage.PLAY_PAUSE)  # already holding
    assert len(client.calls) == n


# -- payload structure -------------------------------------------------------


def test_payload_length(cc: ConsumerControl, client: _FakeClient) -> None:
    """Consumer report in_len=2, so payload = [report_id][2 bytes]."""
    cc.press(ConsumerUsage.PLAY)
    assert len(client.last[1]) == 1 + 2  # report_id + 2 bytes


# -- reliable flag -----------------------------------------------------------


def test_consumer_not_reliable(cc: ConsumerControl, client: _FakeClient) -> None:
    cc.press(ConsumerUsage.PLAY)
    _, _, reliable = client.last
    assert reliable is False


# -- ConsumerUsage enum ------------------------------------------------------


def test_usage_values() -> None:
    assert ConsumerUsage.PLAY == 0x00B0
    assert ConsumerUsage.PLAY_PAUSE == 0x00CD
    assert ConsumerUsage.MUTE == 0x00E2
    assert ConsumerUsage.VOLUME_INCREMENT == 0x00E9
    assert ConsumerUsage.AC_SEARCH == 0x0221
    assert ConsumerUsage.AC_BACK == 0x0224
    assert ConsumerUsage.AL_CALCULATOR == 0x0192
    assert ConsumerUsage.POWER == 0x0030
    assert ConsumerUsage.SLEEP == 0x0032
    assert ConsumerUsage.MENU == 0x0040
    assert ConsumerUsage.AL_NEXT_TASK == 0x01A3
    assert ConsumerUsage.AL_PREV_TASK == 0x01A4


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
