"""Tests for Ordinal class (4-byte INPUT, report ID 10)."""

from __future__ import annotations

import pytest

from hid import IHidClient, Ordinal
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
def ord(client: _FakeClient, table: ReportTable) -> Ordinal:
    return Ordinal(client, table)


def test_set_values(ord: Ordinal, client: _FakeClient) -> None:
    ord.set(instance_1=10, instance_2=20, instance_3=30, instance_4=40)
    assert ord.instance_1 == 10 and ord.instance_2 == 20
    assert ord.instance_3 == 30 and ord.instance_4 == 40
    p = client.last[1]
    assert p[0] == 10
    assert p[1:5] == bytes([10, 20, 30, 40])


def test_set_partial(ord: Ordinal, client: _FakeClient) -> None:
    ord.set(instance_1=5)
    assert ord.instance_1 == 5
    assert ord.instance_2 == 0  # unchanged default


def test_payload_length(ord: Ordinal, client: _FakeClient) -> None:
    ord.set()
    assert len(client.last[1]) == 1 + 4


def test_not_reliable(ord: Ordinal, client: _FakeClient) -> None:
    ord.set(instance_1=1)
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
