"""Tests for VRHeadset class (7-byte, VR HMD rotation + flags, report ID 3)."""

from __future__ import annotations

import pytest

from hid import IHidClient, VRHeadset
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
def hmd(client: _FakeClient, table: ReportTable) -> VRHeadset:
    return VRHeadset(client, table)


def test_set_rotation(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set(rx=100, ry=-50, rz=32767)
    assert hmd.rx == 100 and hmd.ry == -50 and hmd.rz == 32767
    p = client.last[1]
    assert p[0] == 3  # report ID
    # rx = 100 → LE [0x64, 0x00]
    assert p[1] == 0x64 and p[2] == 0x00
    # ry = -50 = 0xFFCE → LE [0xCE, 0xFF]
    assert p[3] == 0xCE and p[4] == 0xFF


def test_stereo_flag(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set(stereo=True)
    assert hmd.stereo
    assert client.last[1][7] == 0x01  # byte 6, bit 0


def test_display_flag(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set(display=True)
    assert client.last[1][7] == 0x02  # byte 6, bit 1


def test_both_flags(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set(stereo=True, display=True)
    assert client.last[1][7] == 0x03


def test_clamp(hmd: VRHeadset) -> None:
    hmd.set(rx=50000, ry=-50000)
    assert hmd.rx == 32767 and hmd.ry == -32768


def test_payload_length(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set()
    assert len(client.last[1]) == 1 + 7


def test_not_reliable(hmd: VRHeadset, client: _FakeClient) -> None:
    hmd.set(rx=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
