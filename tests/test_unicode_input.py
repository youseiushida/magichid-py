"""Tests for UnicodeInput class (12-byte UTF-16LE, report ID 16)."""

from __future__ import annotations

import pytest

from hid import IHidClient, UnicodeInput
from core.reports import ReportTable


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def table() -> ReportTable:
    return ReportTable.universal()


@pytest.fixture
def uni(client: _FakeClient, table: ReportTable) -> UnicodeInput:
    return UnicodeInput(client, table)


# -- basic typing ------------------------------------------------------------


def test_single_character(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("A")
    assert len(client.calls) == 1
    p = client.calls[0][1]
    assert p[0] == 16            # report ID
    # UTF-16LE: 'A' = U+0041 → [0x41, 0x00]
    assert p[1] == 0x41
    assert p[2] == 0x00
    # rest zero
    assert all(b == 0 for b in p[3:])


def test_multiple_characters_one_report(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("abcde")  # 5 chars = 10 bytes, fits in one report
    assert len(client.calls) == 1
    p = client.calls[0][1]
    # 'a'=0x61 'b'=0x62 'c'=0x63 'd'=0x64 'e'=0x65
    assert p[1] == 0x61 and p[2] == 0x00
    assert p[3] == 0x62 and p[4] == 0x00
    assert p[5] == 0x63 and p[6] == 0x00


def test_exactly_six_chars(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("abcdef")  # exactly 6 → 1 report
    assert len(client.calls) == 1


def test_seven_chars_splits(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("abcdefg")  # 7 chars → 2 reports
    assert len(client.calls) == 2
    # first report: "abcdef" (6 chars)
    p0 = client.calls[0][1]
    assert p0[1] == 0x61  # 'a'
    assert p0[11] == 0x66 and p0[12] == 0x00  # 'f' low byte then high
    # second report: "g" + padding
    p1 = client.calls[1][1]
    assert p1[1] == 0x67  # 'g'


def test_empty_string_noop(uni: UnicodeInput, client: _FakeClient) -> None:
    n = len(client.calls)
    uni.type("")
    assert len(client.calls) == n


# -- non-BMP (surrogate pairs) -----------------------------------------------


def test_emoji_surrogate_pair(uni: UnicodeInput, client: _FakeClient) -> None:
    """\U0001f389 = U+1F389 → UTF-16LE surrogate pair [0x3C, 0xD8, 0x89, 0xDF]."""
    uni.type("🎉")
    assert len(client.calls) == 1
    p = client.calls[0][1]
    assert p[1] == 0x3C and p[2] == 0xD8  # high surrogate D83C
    assert p[3] == 0x89 and p[4] == 0xDF  # low surrogate DF89


def test_mixed_bmp_and_emoji(uni: UnicodeInput, client: _FakeClient) -> None:
    """'A🎉' = 1 BMP + 1 surrogate pair = 3 code units → 1 report."""
    uni.type("A🎉")
    assert len(client.calls) == 1


# -- padding -----------------------------------------------------------------


def test_payload_always_12_bytes(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("X")
    assert len(client.calls[0][1]) == 1 + 12  # report_id + 12 bytes


def test_trailing_zeros_after_text(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("AB")  # 2 chars → 4 bytes, rest zero
    p = client.calls[0][1]
    # bytes 1-4: 'A' 'B'
    assert p[1] == 0x41 and p[3] == 0x42
    # bytes 5-12: all zero
    assert all(b == 0 for b in p[5:])


# -- reliable flag -----------------------------------------------------------


def test_unicode_not_reliable(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("A")
    _, _, reliable = client.calls[0]
    assert reliable is False


# -- long text ---------------------------------------------------------------


def test_twelve_chars(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("abcdefghijkl")  # 12 chars → 2 reports
    assert len(client.calls) == 2


def test_thirteen_chars(uni: UnicodeInput, client: _FakeClient) -> None:
    uni.type("abcdefghijklm")  # 13 chars → 3 reports
    assert len(client.calls) == 3


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
