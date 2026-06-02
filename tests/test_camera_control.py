"""Tests for CameraControl class (1-byte flags, report ID 32)."""

from __future__ import annotations

import pytest

from hid import IHidClient, CameraControl
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
def cam(client: _FakeClient, table: ReportTable) -> CameraControl:
    return CameraControl(client, table)


def test_auto_focus(cam: CameraControl, client: _FakeClient) -> None:
    cam.auto_focus()
    p = client.last[1]
    assert p[0] == 32       # report ID
    assert p[1] == 0x01     # auto_focus bit


def test_shutter(cam: CameraControl, client: _FakeClient) -> None:
    cam.shutter()
    assert client.last[1][1] == 0x02  # shutter bit


def test_payload_length(cam: CameraControl, client: _FakeClient) -> None:
    cam.shutter()
    assert len(client.last[1]) == 1 + 1


def test_not_reliable(cam: CameraControl, client: _FakeClient) -> None:
    cam.auto_focus()
    _, _, reliable = client.last
    assert reliable is False


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
