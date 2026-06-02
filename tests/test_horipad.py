"""Tests for the HORIPAD convenience builder (examples/_horipad.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examples._horipad import (
    HORIPAD_NEUTRAL, HORIPAD_BUTTONS, HORIPAD_DPAD, horipad_report,
)


def test_neutral_matches_spec():
    # spec/horipad.md "Neutral state"
    assert HORIPAD_NEUTRAL.hex() == "00000f8080808000"
    assert horipad_report() == HORIPAD_NEUTRAL


def test_press_a():
    # spec/horipad.md example: A (bit 2) -> 04 00 0F 80 80 80 80 00
    assert horipad_report(("A",)).hex() == "04000f8080808000"


def test_a_plus_stick_right():
    # spec/horipad.md example: A + left stick fully right
    assert horipad_report(("A",), lx=0xFF).hex() == "04000fff80808000"


def test_high_bit_button():
    # Plus is bit 9 -> byte 1, bit 1
    assert horipad_report(("PLUS",)).hex() == "00020f8080808000"


def test_multiple_buttons():
    r = horipad_report(("A", "B", "X", "Y"))  # bits 2,1,3,0 = 0x000F
    assert r[0] == 0x0F and r[1] == 0x00


def test_dpad():
    assert horipad_report(dpad="UP")[2] == 0
    assert horipad_report(dpad="DOWN")[2] == 4
    assert horipad_report(dpad="CENTER")[2] == 0x0F


def test_button_names_match_spec():
    # All names in HORIPAD_BUTTONS are valid and in 0..13 range
    assert all(0 <= v <= 13 for v in HORIPAD_BUTTONS.values())


def test_dpad_names_match_spec():
    assert HORIPAD_DPAD["UP"] == 0
    assert HORIPAD_DPAD["CENTER"] == 0x0F
