"""CLI helpers for USB identity/profile selection."""

from __future__ import annotations

import argparse

import pytest

from cli import _identity
from core.wire import MsgType


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, bool]] = []

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        self.calls.append((type_, payload, reliable))


def test_set_horipad_profile(capsys) -> None:
    client = _FakeClient()
    args = argparse.Namespace(
        action="set",
        profile="horipad",
        vid=0,
        pid=0,
        bcd=0,
        json=True,
    )

    _identity.run(args, client)
    capsys.readouterr()

    assert client.calls == [(MsgType.SET_IDENTITY, b"\x00\x00\x00\x00\x00\x00\x01", True)]


def test_u16_accepts_hex() -> None:
    assert _identity._u16("0x0F0D") == 0x0F0D


def test_u16_rejects_out_of_range() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _identity._u16("0x10000")
