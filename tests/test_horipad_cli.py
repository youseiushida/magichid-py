"""CLI helpers for HORIPAD profile."""

from __future__ import annotations

import argparse

import pytest

from cli import _horipad


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))


def test_hold_l_and_r_refreshes_then_releases(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(_horipad.time, "sleep", sleeps.append)

    client = _FakeClient()
    args = argparse.Namespace(
        action="hold",
        buttons=["l", "r"],
        duration_ms=250.0,
        interval_ms=100.0,
        json=True,
    )

    _horipad.run(args, client)
    capsys.readouterr()

    assert sleeps == [0.1, 0.1, 0.1, 0.05]
    assert len(client.calls) == 5
    assert client.calls[0][1] == b"\x00\x00\x0f\x80\x80\x80\x80\x00"  # neutral
    assert client.calls[1][1][0] == 0x30  # press L+R
    assert client.calls[2][1][0] == 0x30  # refresh
    assert client.calls[3][1][0] == 0x30  # refresh
    assert client.calls[4][1][0] == 0x00  # release
