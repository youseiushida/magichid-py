"""Tests for SoCControl class (41-byte FEATURE report, report ID 17)."""

from __future__ import annotations

import pytest

from hid import IHidClient, SoCControl
from core.reports import ReportTable
from core.wire import MsgType


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
def soc(client: _FakeClient, table: ReportTable) -> SoCControl:
    return SoCControl(client, table)


# -- basic set_feature -------------------------------------------------------


def test_set_feature_sends_payload(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_feature(bytes([0xAA, 0xBB]))
    assert client.last[0] == MsgType.SET_FEATURE  # msg type
    p = client.last[1]
    assert p[0] == 17       # report ID
    assert p[1] == 0xAA     # data byte 0
    assert p[2] == 0xBB     # data byte 1


def test_set_feature_padded_to_41(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_feature(b"\x01")
    assert len(client.last[1]) == 1 + 41  # report_id + feat_len


def test_set_feature_trailing_zeros(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_feature(b"\xFF\xFF")
    p = client.last[1]
    assert p[1] == 0xFF and p[2] == 0xFF   # data
    assert all(b == 0 for b in p[3:42])     # rest zero-padded


def test_set_feature_reliable(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_feature(b"\x01")
    _, _, reliable = client.last
    assert reliable is True  # FEATURE → reliable


# -- error: exceeds feat_len -------------------------------------------------


def test_set_feature_rejects_overlong(table: ReportTable, client: _FakeClient) -> None:
    soc = SoCControl(client, table)
    with pytest.raises(ValueError, match="feat_len"):
        soc.set_feature(b"\x00" * 42)


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
