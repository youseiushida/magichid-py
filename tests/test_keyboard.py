"""Tests for the keyboard/mouse convenience builders (examples/_keyboard.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from examples._keyboard import (
    KEY_MOD, char_to_keycode, keyboard_report, mouse_report,
)


def test_keyboard_layout():
    r = keyboard_report([0x04, 0x05], modifier=KEY_MOD.LSHIFT)
    assert r == bytes([0x02, 0, 0x04, 0x05, 0, 0, 0, 0])


def test_keyboard_empty():
    assert keyboard_report() == bytes(8)


def test_keyboard_too_many_keys():
    with pytest.raises(ValueError):
        keyboard_report(tuple(range(7)))


def test_mouse_signed():
    assert mouse_report(buttons=1, x=-1, y=2, wheel=-3).hex() == "01ff02fd00"


def test_mouse_defaults():
    assert mouse_report() == bytes(5)


def test_char_lower():
    assert char_to_keycode("a") == (0, 0x04)
    assert char_to_keycode("z") == (0, 0x1D)


def test_char_upper():
    assert char_to_keycode("A") == (KEY_MOD.LSHIFT, 0x04)


def test_char_digits():
    assert char_to_keycode("1") == (0, 0x1E)
    assert char_to_keycode("0") == (0, 0x27)


def test_char_symbols():
    assert char_to_keycode(" ") == (0, 0x2C)
    assert char_to_keycode("\n") == (0, 0x28)


def test_char_unknown():
    with pytest.raises(KeyError):
        char_to_keycode("@")
