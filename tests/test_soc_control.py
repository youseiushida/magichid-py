"""Tests for SoCControl class (firmware update, 41-byte FEATURE, report ID 17)."""

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


def test_send_chunk(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_firmware_chunk(firmware_id=1, offset=0, payload=b"\xAA" * 32, is_last=True)
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 17               # report ID
    # firmware_id: 1 → [0x01, 0x00]
    assert p[1] == 0x01 and p[2] == 0x00
    # offset: 0 → [0x00, 0x00, 0x00, 0x00]
    assert p[3:7] == b"\x00" * 4
    # payload_size: 32 → [0x20, 0x00]
    assert p[7] == 0x20 and p[8] == 0x00
    # payload: 32 bytes of 0xAA
    assert p[9:41] == b"\xAA" * 32
    # last flag: 1
    assert p[41] == 0x01


def test_padded_payload(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_firmware_chunk(firmware_id=0, offset=1024, payload=b"\xFF")
    p = client.last[1]
    assert p[9] == 0xFF               # first payload byte
    assert p[10] == 0x00              # padded
    assert len(p) == 1 + 41           # report_id + feat_len


def test_rejects_oversize_payload(soc: SoCControl) -> None:
    with pytest.raises(ValueError):
        soc.set_firmware_chunk(payload=b"\x00" * 33)


def test_reliable(soc: SoCControl, client: _FakeClient) -> None:
    soc.set_firmware_chunk()
    _, _, reliable = client.last
    assert reliable is True


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
