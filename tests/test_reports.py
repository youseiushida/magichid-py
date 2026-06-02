"""Core report table tests (ReportSpec, ReportTable, pad_input)."""

from __future__ import annotations

import pytest

from magichid.reports import MOUSE, KEYBOARD, ReportTable


def test_universal_table():
    t = ReportTable.universal()
    assert len(t) == 35
    assert t[MOUSE].relative          # mouse is RELATIVE
    assert not t[KEYBOARD].relative   # keyboard is absolute
    assert t[KEYBOARD].in_len == 8
    assert t[MOUSE].in_len == 5


def test_horipad_table():
    t = ReportTable.horipad()
    assert len(t) == 1
    s = t[0]
    assert s.in_len == 8
    assert s.out_len == 0
    assert s.feat_len == 0
    assert not s.relative


def test_sendable():
    t = ReportTable.universal()
    assert t[KEYBOARD].sendable       # in_len > 0
    assert not t[8].sendable          # LED: OUTPUT-only, in_len=0


def test_pad_input():
    t = ReportTable.universal()
    assert t.pad_input(KEYBOARD, b"\x02\x00\x04").hex() == "0200040000000000"


def test_pad_rejects_overlong():
    with pytest.raises(ValueError):
        ReportTable.universal().pad_input(KEYBOARD, b"\x00" * 9)


def test_pad_rejects_non_sendable():
    with pytest.raises(ValueError):
        ReportTable.universal().pad_input(8, b"")  # LED is output-only


def test_from_caps():
    from magichid.events import CapsReceived, ReportCap
    caps = CapsReceived(seq=1, entries=(
        ReportCap(1, 5, 0, 0, 0x01),
        ReportCap(7, 8, 1, 0, 0x00),
    ))
    t = ReportTable.from_caps(caps)
    assert t[1].relative and t[1].in_len == 5
    assert not t[7].relative and t[7].out_len == 1


def test_contains_and_get():
    t = ReportTable.universal()
    assert 7 in t and 99 not in t
    assert t.get(7) is not None and t.get(99) is None
