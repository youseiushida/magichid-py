"""Tests for CameraControl class (1-byte trigger, report ID 32)."""

from __future__ import annotations

import pytest

from hid import IHidClient, CameraAction, CameraControl
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


# -- basic triggers ----------------------------------------------------------


def test_trigger_autofocus(cam: CameraControl, client: _FakeClient) -> None:
    cam.trigger(CameraAction.AUTO_FOCUS)
    p = client.last[1]
    assert p[0] == 32       # report ID
    assert p[1] == 0x20     # AUTO_FOCUS


def test_trigger_shutter(cam: CameraControl, client: _FakeClient) -> None:
    cam.trigger(CameraAction.SHUTTER)
    assert client.last[1][1] == 0x21


# -- payload structure -------------------------------------------------------


def test_payload_length(cam: CameraControl, client: _FakeClient) -> None:
    cam.trigger(CameraAction.SHUTTER)
    assert len(client.last[1]) == 1 + 1  # report_id + 1 byte


# -- reliable flag -----------------------------------------------------------


def test_camera_not_reliable(cam: CameraControl, client: _FakeClient) -> None:
    cam.trigger(CameraAction.AUTO_FOCUS)
    _, _, reliable = client.last
    assert reliable is False


# -- CameraAction enum -------------------------------------------------------


def test_action_values() -> None:
    assert CameraAction.AUTO_FOCUS == 0x20
    assert CameraAction.SHUTTER == 0x21


# -- IHidClient protocol -----------------------------------------------------


def test_fake_client_satisfies_protocol() -> None:
    c: IHidClient = _FakeClient()
    c.request(0x01, b"\x00")
