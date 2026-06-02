"""Tests for MSR class (229-byte INPUT, magnetic stripe reader, report ID 31)."""

from __future__ import annotations

import pytest

from hid import IHidClient, MSR
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
def msr(client: _FakeClient, table: ReportTable) -> MSR:
    return MSR(client, table)


# -- send --------------------------------------------------------------------


def test_send_track1(msr: MSR, client: _FakeClient) -> None:
    data = b"%B123456^DOE/JOHN^01011010000?"
    msr.send(track1=data)
    p = client.last[1]
    assert p[0] == 31                   # report ID
    assert p[1] == len(data)            # track1 length
    assert p[2] == 0                    # track2 length = 0
    assert p[3] == 0                    # track3 length = 0
    # data starts at offset 3
    assert p[4:4 + len(data)] == data


def test_send_track2(msr: MSR, client: _FakeClient) -> None:
    msr.send(track2=b";123456=01011010000?")
    p = client.last[1]
    assert p[2] == 20  # track2 length


def test_send_all_tracks(msr: MSR, client: _FakeClient) -> None:
    msr.send(track1=b"T1", track2=b"T2", track3=b"T3")
    p = client.last[1]
    assert p[1] == 2 and p[2] == 2 and p[3] == 2
    # track1 at offset 3
    assert p[4:6] == b"T1"
    # track2 at offset 3 + 79 = 82
    assert p[83:85] == b"T2"
    # track3 at offset 3 + 79 + 40 = 122
    assert p[123:125] == b"T3"


def test_rejects_overlong_track(msr: MSR) -> None:
    with pytest.raises(ValueError):
        msr.send(track1=bytes(80))


def test_payload_length(msr: MSR, client: _FakeClient) -> None:
    msr.send()
    assert len(client.last[1]) == 1 + 229


def test_not_reliable(msr: MSR, client: _FakeClient) -> None:
    msr.send()
    _, _, reliable = client.last
    assert reliable is False


# -- protocol ----------------------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
