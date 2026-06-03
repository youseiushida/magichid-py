"""Pure sans-I/O core tests — fake clock, zero I/O, zero threads."""

from __future__ import annotations

import pytest

from core.codec import build_frame
from core.connection import Connection, Timers
from core.events import (
    Acknowledged, CapsReceived, FrameError, HostEventReceived, LogReceived,
    NackUnmatched, Rejected, ReportCap, StatusReceived, VersionMismatch,
)
from core.wire import MsgType, StatusFlag


class FakeClock:
    def __init__(self, t: float = 0.0): self.t = t

    def __call__(self) -> float: return self.t

    def advance(self, dt: float) -> None: self.t += dt


def df(type_: int, payload: bytes = b"") -> bytes:
    """device->operator frame (seq=0)."""
    return build_frame(type_, 0, payload)


# -- send -------------------------------------------------------------------
def test_send_tracks_reliable():
    c = Connection()
    seq, f = c.send(MsgType.SEND_REPORT, b"\x07")
    assert f.endswith(b"\x00") and seq in c.inflight


def test_send_fire_and_forget_not_tracked():
    c = Connection()
    seq, _ = c.send(MsgType.PING, b"", reliable=False)
    assert seq not in c.inflight


def test_send_window_full_returns_none():
    c = Connection(max_in_flight=1)
    c.send(MsgType.SEND_REPORT, b"", reliable=True)
    assert c.send(MsgType.SEND_REPORT, b"", reliable=True) is None


def test_seq_wraps_never_zero():
    c = Connection()
    seqs = set()
    for _ in range(300):
        seqs.add(c.send(MsgType.PING, reliable=False)[0])
    assert 0 not in seqs and seqs == set(range(1, 256))


def test_ping_returns_frame_not_tracked():
    c = Connection()
    f = c.ping()
    assert f.endswith(b"\x00") and not c.inflight


# -- receive: events --------------------------------------------------------
def test_status_event():
    c = Connection()
    [s] = c.receive_bytes(df(MsgType.STATUS, bytes([0x05, 2])))
    assert isinstance(s, StatusReceived) and s.mounted and s.ready
    assert s.proto_version == 2


def test_ack_clears_inflight():
    c = Connection()
    seq, _ = c.send(MsgType.SEND_REPORT, b"", reliable=True)
    [a] = c.receive_bytes(build_frame(MsgType.ACK, seq, b""))
    assert isinstance(a, Acknowledged) and a.seq == seq and not c.inflight


def test_nack_resolves():
    c = Connection()
    seq, _ = c.send(MsgType.SEND_REPORT, b"", reliable=True)
    [r] = c.receive_bytes(build_frame(MsgType.NACK, seq, bytes([3])))
    assert isinstance(r, Rejected) and r.reason_name == "UNKNOWN_ID"


def test_nack_seq0_unmatched():
    c = Connection()
    [u] = c.receive_bytes(build_frame(MsgType.NACK, 0, bytes([1])))
    assert isinstance(u, NackUnmatched) and u.reason_name == "BAD_CRC"


def test_caps_matches_seq():
    c = Connection()
    seq, _ = c.send(MsgType.GET_CAPS, b"", reliable=True)
    payload = bytes([1, 5, 0, 0, 0x01, 7, 8, 1, 0, 0x00])
    [caps] = c.receive_bytes(build_frame(MsgType.CAPS, seq, payload))
    assert isinstance(caps, CapsReceived) and caps.seq == seq
    assert caps.entries[0].relative and not caps.entries[1].relative


def test_host_event_and_log():
    c = Connection()
    [he] = c.receive_bytes(df(MsgType.HOST_EVENT, bytes([8, 2]) + b"\x01"))
    assert isinstance(he, HostEventReceived) and he.type_name == "OUTPUT"
    [lg] = c.receive_bytes(df(MsgType.LOG, b"hi"))
    assert isinstance(lg, LogReceived) and lg.text == "hi"


def test_corrupt_frame_event():
    c = Connection()
    frame = bytearray(df(MsgType.ACK, bytes([1])))
    frame[1] ^= 0xFF  # corrupt body
    [e] = c.receive_bytes(bytes(frame))
    assert isinstance(e, FrameError)


def test_version_mismatch_once():
    c = Connection(target_version=2)
    batch = c.receive_bytes(df(MsgType.STATUS, bytes([0x05, 99])))
    assert any(isinstance(e, VersionMismatch) for e in batch)
    again = c.receive_bytes(df(MsgType.STATUS, bytes([0x05, 99])))
    assert not any(isinstance(e, VersionMismatch) for e in again)


# -- incremental framing ----------------------------------------------------
def test_partial_reassembly():
    c = Connection()
    frame = df(MsgType.STATUS, bytes([0x05, 2]))
    assert c.receive_bytes(frame[:3]) == []
    [s] = c.receive_bytes(frame[3:])
    assert isinstance(s, StatusReceived)


def test_two_frames_one_chunk():
    c = Connection()
    buf = df(MsgType.ACK, bytes([5])) + df(MsgType.LOG, b"x")
    events = c.receive_bytes(buf)
    assert [type(e).__name__ for e in events] == ["Acknowledged", "LogReceived"]


# -- timing (fake clock, no real waiting) -----------------------------------
def test_retransmit_then_fail():
    clock = FakeClock()
    c = Connection(clock=clock, ack_timeout=0.2, retransmit_limit=2)
    seq, frame = c.send(MsgType.SEND_REPORT, b"", reliable=True)

    early = c.check_timeouts()
    assert early.retransmit == () and early.failed == ()

    clock.advance(0.2)
    t1 = c.check_timeouts()  # retransmit #1
    assert t1.retransmit == (frame,) and t1.failed == ()

    clock.advance(0.2)
    t2 = c.check_timeouts()  # retransmit #2
    assert t2.retransmit == (frame,) and t2.failed == ()

    clock.advance(0.2)
    t3 = c.check_timeouts()  # budget exhausted
    assert t3.retransmit == () and t3.failed == (seq,)


def test_ack_cancels_retransmit():
    clock = FakeClock()
    c = Connection(clock=clock, ack_timeout=0.2)
    seq, _ = c.send(MsgType.SEND_REPORT, b"", reliable=True)
    c.receive_bytes(build_frame(MsgType.ACK, seq, b""))
    clock.advance(10.0)
    t = c.check_timeouts()
    assert t.retransmit == () and t.failed == ()
