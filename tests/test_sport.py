"""Tests for GolfClub class (8-byte, golf swing metrics, report ID 4)."""

from __future__ import annotations

import pytest

from hid import IHidClient, GolfClub
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
def club(client: _FakeClient, table: ReportTable) -> GolfClub:
    return GolfClub(client, table)


def test_set_speed(club: GolfClub, client: _FakeClient) -> None:
    club.set(speed=12000)
    assert club.speed == 12000
    p = client.last[1]
    assert p[0] == 4  # report ID
    # 12000 = 0x2EE0 → LE [0xE0, 0x2E]
    assert p[1] == 0xE0 and p[2] == 0x2E


def test_set_all(club: GolfClub) -> None:
    club.set(speed=1, face_angle=2, heel_toe=3, tempo=4)
    assert (club.speed, club.face_angle, club.heel_toe, club.tempo) == (1, 2, 3, 4)


def test_negative(club: GolfClub, client: _FakeClient) -> None:
    club.set(face_angle=-200)
    # -200 = 0xFF38 → LE [0x38, 0xFF]
    assert client.last[1][3] == 0x38 and client.last[1][4] == 0xFF


def test_clamp(club: GolfClub) -> None:
    club.set(speed=50000, tempo=-50000)
    assert club.speed == 32767 and club.tempo == -32768


def test_payload_length(club: GolfClub, client: _FakeClient) -> None:
    club.set()
    assert len(client.last[1]) == 1 + 8


def test_not_reliable(club: GolfClub, client: _FakeClient) -> None:
    club.set(speed=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
