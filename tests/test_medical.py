"""Tests for MedicalUltrasound class (5-byte INPUT, report ID 21)."""

from __future__ import annotations

import pytest

from hid import IHidClient, MedicalUltrasound
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
def us(client: _FakeClient, table: ReportTable) -> MedicalUltrasound:
    return MedicalUltrasound(client, table)


def test_set_flags(us: MedicalUltrasound, client: _FakeClient) -> None:
    us.set(vcr_acquisition=True, freeze=True)
    assert us.vcr_acquisition and us.freeze
    assert client.last[1][1] == 0x03  # bits 0,1


def test_set_controls(us: MedicalUltrasound) -> None:
    us.set(depth=50, focus=30, transmit_power=80, cine=100)
    assert us.depth == 50 and us.focus == 30
    assert us.transmit_power == 80 and us.cine == 100


def test_payload_structure(us: MedicalUltrasound, client: _FakeClient) -> None:
    us.set(vcr_acquisition=True, depth=0xAB, focus=0xCD, transmit_power=0xEF, cine=0x12)
    p = client.last[1]
    assert p[0] == 21
    assert p[1] == 0x01   # vcr flag
    assert p[2] == 0xAB   # depth
    assert p[3] == 0xCD   # focus
    assert p[4] == 0xEF   # power
    assert p[5] == 0x12   # cine


def test_payload_length(us: MedicalUltrasound, client: _FakeClient) -> None:
    us.set()
    assert len(client.last[1]) == 1 + 5


def test_not_reliable(us: MedicalUltrasound, client: _FakeClient) -> None:
    us.set(depth=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
