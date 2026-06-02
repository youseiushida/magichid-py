"""Tests for Monitor class (130-byte FEATURE EDID, report ID 24)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Monitor
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
def mon(client: _FakeClient, table: ReportTable) -> Monitor:
    return Monitor(client, table)


# -- set_edid ----------------------------------------------------------------


def test_set_edid(mon: Monitor, client: _FakeClient) -> None:
    data = bytes(range(128))
    mon.set_edid(data)
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 24                   # report ID
    assert p[1:129] == data             # EDID bytes
    assert p[129] == 0 and p[130] == 0  # VESA version zeros


def test_set_edid_pads_short(mon: Monitor, client: _FakeClient) -> None:
    mon.set_edid(b"\xAA\xBB")
    p = client.last[1]
    assert p[1] == 0xAA and p[2] == 0xBB
    assert all(b == 0 for b in p[3:129])


def test_set_edid_rejects_overlong(mon: Monitor) -> None:
    with pytest.raises(ValueError):
        mon.set_edid(bytes(129))


# -- set_vesa_version --------------------------------------------------------


def test_set_vesa_version(mon: Monitor, client: _FakeClient) -> None:
    mon.set_vesa_version(0x0103)
    p = client.last[1]
    assert p[129] == 0x03 and p[130] == 0x01  # LE: 0x0103


# -- set combined ------------------------------------------------------------


def test_set_both(mon: Monitor, client: _FakeClient) -> None:
    edid = b"\x00" * 128
    mon.set(edid=edid, vesa_version=0x0200)
    p = client.last[1]
    assert p[129] == 0x00 and p[130] == 0x02


def test_set_no_args_noop(mon: Monitor, client: _FakeClient) -> None:
    n = len(client.calls)
    mon.set()
    assert len(client.calls) == n


# -- payload -----------------------------------------------------------------


def test_payload_length(mon: Monitor, client: _FakeClient) -> None:
    mon.set_edid(bytes(128))
    assert len(client.last[1]) == 1 + 130


def test_reliable(mon: Monitor, client: _FakeClient) -> None:
    mon.set_edid(bytes(128))
    _, _, reliable = client.last
    assert reliable is True  # FEATURE → reliable


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
