"""Thin-edge integration tests over the FakeDevice (no hardware)."""

from __future__ import annotations

import pytest

from core import events as ev
from core.connection import Connection
from core.io.blocking import BlockingClient, BlockingError, ProtocolVersionError
from core.wire import MsgType

from .fake_device import FakeDevice


def _client(dev=None, **kw):
    dev = dev or FakeDevice()
    return BlockingClient(transport=dev, **kw)


def test_handshake():
    with _client() as c:
        s = c.handshake(timeout=2.0)
        assert s.mounted and s.ready


def test_handshake_waits_until_ready():
    dev = FakeDevice(flags=0)
    import threading, time as _t
    with _client(dev) as c:
        def make_ready():
            _t.sleep(0.2); dev.flags = 0x05
        threading.Thread(target=make_ready, daemon=True).start()
        s = c.handshake(timeout=3.0, ping_interval=0.1)
        assert s.ready


def test_handshake_version_mismatch():
    with _client(FakeDevice(proto_version=99)) as c:
        with pytest.raises(ProtocolVersionError):
            c.handshake(timeout=2.0)


def test_handshake_no_session_reply_fails_fast():
    """A device that never answers SESSION_OPEN (pre-v3 firmware / dead bridge)
    must fail explicitly on the session step, not silently fall back to a
    session-less handshake (which would reintroduce the cross-connection dedup
    hazard). The session budget must also not consume the whole timeout."""
    from core.io.blocking import CommandTimeout

    dev = FakeDevice(); dev.support_session = False

    class Clock:
        def __init__(self): self.t = 0.0
        def __call__(self): return self.t
        def advance(self, dt): self.t += dt

    clk = Clock()
    with _client(dev, clock=clk, sleep=lambda _s: clk.advance(0.05)) as c:
        # Drive the fake clock forward as the edge polls, so the bounded
        # session_timeout elapses without real waiting.
        orig_read = dev.read
        def read_advancing(n):
            clk.advance(0.02)
            return orig_read(n)
        dev.read = read_advancing
        with pytest.raises(CommandTimeout) as ei:
            c.handshake(timeout=5.0, session_timeout=0.5, ping_interval=0.1)
        assert ei.value.kind == MsgType.SESSION_OPEN
        # The device DID receive SESSION_OPEN frames (retransmitted), proving we
        # tried — it just never replied.
        assert any(t == MsgType.SESSION_OPEN for t, _, _ in dev.received)


def test_request_acks():
    with _client() as c:
        c.handshake(timeout=2.0)
        ack = c.request(MsgType.SEND_REPORT, bytes([7]) + b"\x00" * 8)
        assert isinstance(ack, ev.Acknowledged)


def test_retransmit_same_seq():
    dev = FakeDevice(); dev.drop_first_ack = True
    with _client(dev, connection=Connection(ack_timeout=0.1, retransmit_limit=10)) as c:
        c.handshake(timeout=2.0)
        ack = c.request(MsgType.SEND_REPORT, bytes([7]), timeout=3.0)
        seqs = [s for t, s, _ in dev.received if t == MsgType.SEND_REPORT]
        assert seqs.count(ack.seq) >= 2


def test_nack_raises():
    dev = FakeDevice()
    with _client(dev) as c:
        c.handshake(timeout=2.0)
        next_seq = (c.conn._seq % 255) + 1
        dev.nack_seqs.add(next_seq)
        with pytest.raises(BlockingError, match="rejected"):
            c.request(MsgType.SEND_REPORT, bytes([7]))


def test_get_caps():
    caps_payload = bytes([1, 5, 0, 0, 0x01, 7, 8, 1, 0, 0x00])
    with _client(FakeDevice(caps_payload=caps_payload)) as c:
        c.handshake(timeout=2.0)
        caps = c.get_caps(timeout=2.0)
        assert len(caps.entries) == 2
        assert caps.entries[0].relative


def test_release_all_on_exit():
    dev = FakeDevice()
    with _client(dev) as c:
        c.handshake(timeout=2.0)
    assert any(t == MsgType.RELEASE_ALL for t, _, _ in dev.received)
    assert dev.closed


def test_set_identity_acks_then_close():
    dev = FakeDevice()
    with _client(dev) as c:
        c.handshake(timeout=2.0)
        ack = c.request(MsgType.SET_IDENTITY,
                         bytes([0x0D, 0x0F, 0xC1, 0x00, 0x00, 0x01, 0x01]))
        assert isinstance(ack, ev.Acknowledged)
    # SET_IDENTITY was received with correct payload
    ident = [p for t, _, p in dev.received if t == MsgType.SET_IDENTITY]
    assert ident and ident[0] == bytes([0x0D, 0x0F, 0xC1, 0x00, 0x00, 0x01, 0x01])
