"""The sans-I/O protocol core.

:class:`Connection` is a pure state machine — no serial, no threads, no sleeps.
Time enters through an injected ``clock`` callable so retransmission and expiry
are deterministic and unit-testable with a fake clock.

``send(type, payload) -> (seq, frame_bytes)``    intent -> bytes
``receive_bytes(data) -> list[Event]``           bytes -> events
``check_timeouts() -> Timers``                   retransmit/fail policy
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass

from . import events as ev
from .codec import CodecError, build_frame, parse_frame
from .wire import DEDUP_WINDOW, MAX_PAYLOAD, MsgType, PROTO_VERSION


@dataclass
class _Pending:
    seq: int
    kind: int          # MsgType of the request
    frame: bytes
    deadline: float
    attempts: int      # transmissions so far (1 = initial send)


@dataclass(frozen=True)
class Timers:
    retransmit: tuple[bytes, ...]
    failed: tuple[int, ...]


class Connection:
    """Pure sans-I/O protocol core."""

    def __init__(self, *, clock=_time.monotonic, ack_timeout: float = 0.2,
                 retransmit_limit: int = 5, max_in_flight: int = 1,
                 target_version: int = PROTO_VERSION):
        self._clock = clock
        self._ack_timeout = ack_timeout
        self._retransmit_limit = retransmit_limit
        self._max_in_flight = min(max_in_flight, DEDUP_WINDOW // 2)
        self._target_version = target_version

        self._seq = 0
        self._rx = bytearray()
        self._pending: dict[int, _Pending] = {}
        self._version_checked = False
        self.latest_status: ev.StatusReceived | None = None

    # -- intent -> bytes ---------------------------------------------------- #
    def _next_seq(self) -> int:
        self._seq = (self._seq % 255) + 1
        return self._seq

    @property
    def inflight(self) -> frozenset[int]:
        return frozenset(self._pending)

    @property
    def has_capacity(self) -> bool:
        return len(self._pending) < self._max_in_flight

    def send(self, type_: int, payload: bytes = b"", *, reliable: bool = True) -> tuple[int, bytes] | None:
        """Build a wire frame.  Returns ``(seq, frame)``, or ``None`` if
        *reliable* and the in-flight window is full."""
        if reliable and not self.has_capacity:
            return None
        if len(payload) > MAX_PAYLOAD:
            raise ValueError(f"payload {len(payload)} > {MAX_PAYLOAD}")
        seq = self._next_seq()
        frame = build_frame(type_, seq, payload)
        if reliable:
            self._pending[seq] = _Pending(
                seq=seq, kind=type_, frame=frame,
                deadline=self._clock() + self._ack_timeout, attempts=1)
        return seq, frame

    def ping(self) -> bytes:
        """Fire-and-forget PING (no SEQ tracking)."""
        seq = self._next_seq()
        return build_frame(MsgType.PING, seq, b"")

    # -- bytes -> events ---------------------------------------------------- #
    def receive_bytes(self, data: bytes) -> list[ev.Event]:
        if not data:
            return []
        self._rx += data
        if b"\x00" not in self._rx:
            return []
        *chunks, tail = self._rx.split(b"\x00")
        self._rx = bytearray(tail)
        out: list[ev.Event] = []
        for chunk in chunks:
            if not chunk:
                continue
            try:
                t, s, p = parse_frame(bytes(chunk))
            except CodecError as e:
                out.append(ev.FrameError(detail=str(e)))
                continue
            out.extend(self._on_frame(t, s, p))
        return out

    def _on_frame(self, type_: int, seq: int, payload: bytes) -> list[ev.Event]:
        # -- STATUS (unsolicited / reply to PING) --
        if type_ == MsgType.STATUS and len(payload) >= 2:
            st = ev.StatusReceived(flags=payload[0], proto_version=payload[1])
            self.latest_status = st
            out: list[ev.Event] = [st]
            if not self._version_checked:
                self._version_checked = True
                if st.proto_version != self._target_version:
                    out.append(ev.VersionMismatch(st.proto_version, self._target_version))
            return out

        # -- ACK / NACK (resolve pending requests) --
        # Firmware encodes the acked/rejected seq in the frame SEQ field, not the payload.
        if type_ == MsgType.ACK:
            self._pending.pop(seq, None)
            return [ev.Acknowledged(seq=seq)]

        if type_ == MsgType.NACK:
            if seq == 0:
                reason = payload[0] if len(payload) >= 1 else 0
                return [ev.NackUnmatched(reason=reason)]
            self._pending.pop(seq, None)
            reason = payload[0] if len(payload) >= 1 else 0
            return [ev.Rejected(seq=seq, reason=reason)]

        # -- CAPS (reply to GET_CAPS, carries the request SEQ) --
        if type_ == MsgType.CAPS and len(payload) >= 5:
            rem = len(payload) - (len(payload) % 5)
            entries = tuple(
                ev.ReportCap(payload[i], payload[i + 1], payload[i + 2],
                             payload[i + 3], payload[i + 4])
                for i in range(0, rem, 5)
            )
            # CAPS carries the GET_CAPS SEQ — resolve the pending request
            self._pending.pop(seq, None)
            return [ev.CapsReceived(seq=seq, entries=entries)]

        # -- unsolicited notifications (seq=0) --
        if type_ == MsgType.HOST_EVENT and len(payload) >= 2:
            return [ev.HostEventReceived(payload[0], payload[1], bytes(payload[2:]))]

        if type_ == MsgType.LOG:
            return [ev.LogReceived(payload.decode("ascii", "replace"))]

        return [ev.UnknownFrame(type=type_, seq=seq, payload=bytes(payload))]

    # -- timing policy ------------------------------------------------------ #
    def check_timeouts(self) -> Timers:
        now = self._clock()
        retrans, failed = [], []
        for seq, p in list(self._pending.items()):
            if now < p.deadline:
                continue
            if p.attempts > self._retransmit_limit:
                failed.append(seq)
                del self._pending[seq]
            else:
                p.attempts += 1
                p.deadline = now + self._ack_timeout
                retrans.append(p.frame)
        return Timers(retransmit=tuple(retrans), failed=tuple(failed))
