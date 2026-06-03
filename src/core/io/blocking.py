"""A thin, single-threaded blocking edge over the sans-I/O :class:`Connection`.

No background threads. The caller drives everything by calling ``poll()`` /
``request()`` / ``handshake()``. All protocol logic lives in the core.
"""

from __future__ import annotations

import time as _time
from typing import Optional

from .. import events as ev
from ..connection import Connection
from ..wire import MsgType, NackReason, StatusFlag

try:
    import serial as _serial
except ImportError:  # pragma: no cover
    _serial = None


class BlockingError(Exception):
    """Base for blocking-edge errors."""


class CommandTimeout(BlockingError):
    def __init__(self, seq: int, kind: int):
        self.seq = seq; self.kind = kind
        super().__init__(f"no response for seq={seq} kind={kind:#04x}")


class ProtocolVersionError(BlockingError):
    def __init__(self, got: int, expected: int):
        self.got = got; self.expected = expected
        super().__init__(f"device proto_version={got}, client targets {expected}")


class _Disconnected(Exception):
    """Internal: serial read returned nothing."""


class BlockingClient:
    """Drive a :class:`Connection` over a pyserial transport."""

    def __init__(self, port: Optional[str] = None, *,
                 baudrate: int = 1_000_000, timeout: float = 0.1,
                 connection: Optional[Connection] = None,
                 transport=None, clock=_time.monotonic, sleep=_time.sleep):
        self._clock = clock
        self._sleep = sleep
        self.conn = connection or Connection(clock=clock)
        self._inbox: list[ev.Event] = []
        self._failed: set[int] = set()
        self.session_epoch: int | None = None   # set by handshake() via SESSION_OPEN

        if transport is not None:
            self._ser = transport
        elif port is not None:
            if _serial is None:  # pragma: no cover
                raise BlockingError("pyserial not installed")
            self._ser = _serial.Serial(
                port, baudrate, bytesize=_serial.EIGHTBITS,
                parity=_serial.PARITY_NONE, stopbits=_serial.STOPBITS_ONE,
                timeout=timeout, rtscts=False, dsrdtr=False, xonxoff=False)
        else:
            raise BlockingError("port or transport required")

    # -- lifecycle ---------------------------------------------------------- #
    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:  # pragma: no cover
            pass

    def __enter__(self) -> "BlockingClient":
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.send(MsgType.RELEASE_ALL, b"", reliable=False)
        except Exception:  # pragma: no cover
            pass
        self.close()

    # -- primitives --------------------------------------------------------- #
    def send(self, type_: int, payload: bytes = b"", *, reliable: bool = False) -> int:
        result = self.conn.send(type_, payload, reliable=reliable)
        if result is None:
            raise BlockingError("send window full")
        seq, frame = result
        self._ser.write(frame)
        return seq

    def _read(self) -> bytes:
        n = getattr(self._ser, "in_waiting", 0) or 0
        data = self._ser.read(n if n > 0 else 1)
        if not data:
            raise _Disconnected
        return data

    def _service(self) -> list[ev.Event]:
        """One read + feed + retransmit cycle."""
        out: list[ev.Event] = []
        try:
            data = self._read()
        except _Disconnected:
            data = b""
        if data:
            out.extend(self.conn.receive_bytes(data))
        timers = self.conn.check_timeouts()
        for f in timers.retransmit:
            self._ser.write(f)
        self._failed.update(timers.failed)
        return out

    def poll(self) -> list[ev.Event]:
        """Run one service cycle; return new events."""
        return self._service()

    def drain_events(self) -> list[ev.Event]:
        buf, self._inbox = self._inbox, []
        return buf

    # -- request / handshake ------------------------------------------------ #
    def request(self, type_: int, payload: bytes = b"", *, reliable: bool = True,
                timeout: float = 2.0, not_ready_retries: int = 20) -> ev.Acknowledged:
        """Send reliably and block until the matching ACK (or error).

        A NOT_READY NACK means the device's USB IN endpoint had not yet been
        polled by the host (it polls every ``HID_POLL_MS``). That is transient,
        so we briefly back off and resend the same report rather than failing —
        otherwise back-to-back reports (e.g. ``keyboard type``) silently drop.
        """
        attempts = not_ready_retries
        while True:
            try:
                return self._request_once(type_, payload, timeout=timeout)
            except BlockingError as exc:
                if getattr(exc, "reason", None) == NackReason.NOT_READY and attempts > 0:
                    attempts -= 1
                    self._sleep(0.004)   # ~2x HID_POLL_MS, let the host poll once
                    continue
                raise

    def _request_once(self, type_: int, payload: bytes, *, timeout: float) -> ev.Acknowledged:
        deadline = self._clock() + timeout
        while True:
            r = self.conn.send(type_, payload, reliable=True)
            if r is not None:
                seq, frame = r
                break
            # window full — spin one cycle to make room
            self._service()
        self._ser.write(frame)
        if seq in self._failed:
            self._failed.discard(seq)
        while self._clock() < deadline:
            for e in self._service():
                if isinstance(e, ev.VersionMismatch):
                    raise ProtocolVersionError(e.got, e.expected)
                if isinstance(e, ev.Acknowledged) and e.seq == seq:
                    return e
                if isinstance(e, ev.Rejected) and e.seq == seq:
                    err = BlockingError(f"rejected seq={seq} reason={e.reason_name}")
                    err.reason = e.reason
                    raise err
                self._inbox.append(e)
            if seq in self._failed:
                self._failed.discard(seq)
                raise CommandTimeout(seq, type_)
        raise CommandTimeout(seq, type_)

    def get_caps(self, *, timeout: float = 2.0) -> ev.CapsReceived:
        """Send GET_CAPS reliably and block until the CAPS reply."""
        deadline = self._clock() + timeout
        while True:
            r = self.conn.send(MsgType.GET_CAPS, b"", reliable=True)
            if r is not None:
                seq, frame = r
                break
            self._service()
        self._ser.write(frame)
        while self._clock() < deadline:
            for e in self._service():
                if isinstance(e, ev.VersionMismatch):
                    raise ProtocolVersionError(e.got, e.expected)
                if isinstance(e, ev.CapsReceived) and e.seq == seq:
                    return e
                self._inbox.append(e)
            if seq in self._failed:
                self._failed.discard(seq)
                raise CommandTimeout(seq, MsgType.GET_CAPS)
        raise CommandTimeout(seq, MsgType.GET_CAPS)

    def handshake(self, *, timeout: float = 5.0, ping_interval: float = 0.2,
                  session_timeout: float = 1.0) -> ev.StatusReceived:
        """Open a session, then PING until STATUS reports MOUNTED|READY.

        Two distinct waits, each with its own budget:

        1. SESSION_OPEN -> SESSION: an operator<->bridge round-trip the firmware
           answers immediately, regardless of target-host mount state. It makes
           the device mint a fresh epoch and clear its per-session SEQ dedup
           window, so this client's SEQ counter (which restarts at 1 each
           process) can't collide with a previous connection's remembered SEQs.
           Bounded by ``session_timeout``; SESSION_OPEN is resent every
           ``ping_interval`` (it is idempotent) until the SESSION reply arrives.
           No reply within the budget means the bridge is dead or running
           pre-v3 firmware -> raise (we do NOT silently fall back to a
           session-less handshake, which would reintroduce the dedup hazard).

        2. PING -> STATUS(MOUNTED|READY): waits for the *target host* to
           enumerate the device, which can take seconds. Gets the remaining
           budget after the session is established.
        """
        deadline = self._clock() + timeout
        session_deadline = min(self._clock() + session_timeout, deadline)
        self.session_epoch = self._open_session(session_deadline, ping_interval)
        next_ping = 0.0
        while self._clock() < deadline:
            now = self._clock()
            if now >= next_ping:
                self._ser.write(self.conn.ping())
                next_ping = now + ping_interval
            batch = self._service()
            for e in batch:
                if isinstance(e, ev.VersionMismatch):
                    raise ProtocolVersionError(e.got, e.expected)
            for e in batch:
                if isinstance(e, ev.StatusReceived) and e.mounted and e.ready:
                    return e
                self._inbox.append(e)
        raise CommandTimeout(0, MsgType.PING)

    def _open_session(self, deadline: float, retry_interval: float) -> int:
        """Send SESSION_OPEN until the SESSION reply arrives; return the epoch.

        Raises CommandTimeout if no SESSION reply arrives before *deadline*
        (a dead bridge or pre-v3 firmware that does not implement SESSION_OPEN).
        """
        next_send = 0.0
        while self._clock() < deadline:
            now = self._clock()
            if now >= next_send:
                self._ser.write(self.conn.session_open())
                next_send = now + retry_interval
            for e in self._service():
                if isinstance(e, ev.VersionMismatch):
                    raise ProtocolVersionError(e.got, e.expected)
                if isinstance(e, ev.SessionOpened):
                    return e.epoch
                self._inbox.append(e)
        raise CommandTimeout(0, MsgType.SESSION_OPEN)
