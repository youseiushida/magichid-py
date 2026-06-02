"""In-process fake of the MagicHID device for edge testing (no hardware)."""

from __future__ import annotations

import threading

from magichid.codec import build_frame, parse_frame
from magichid.wire import MsgType, NackReason, StatusFlag


class FakeDevice:
    """Serial-like transport: ``read`` / ``write`` / ``in_waiting`` / ``close``."""

    def __init__(self, *, proto_version: int = 2,
                 flags: int = StatusFlag.MOUNTED | StatusFlag.READY,
                 caps_payload: bytes = b"", timeout: float = 0.05):
        self.timeout = timeout; self.proto_version = proto_version
        self.flags = flags; self.caps_payload = caps_payload
        self._rx = bytearray()
        self._cond = threading.Condition()
        self._buf = bytearray()  # frame accumulator
        self.received: list[tuple[int, int, bytes]] = []
        self.nack_seqs: set[int] = set()
        self.drop_first_ack = False
        self._acked: set[int] = set()
        self.closed = False

    @property
    def in_waiting(self) -> int:
        with self._cond: return len(self._rx)

    def read(self, n: int) -> bytes:
        with self._cond:
            if not self._rx:
                self._cond.wait(timeout=self.timeout)
            if not self._rx:
                return b""
            data = bytes(self._rx[:n]); del self._rx[:n]
            return data

    def write(self, frame: bytes) -> None:
        self._buf += frame
        if b"\x00" not in self._buf:
            return
        *chunks, tail = self._buf.split(b"\x00")
        self._buf = bytearray(tail)
        for chunk in chunks:
            if not chunk:
                continue
            t, s, p = parse_frame(bytes(chunk))
            self._on_command(t, s, p)

    def flush(self) -> None: pass

    def close(self) -> None:
        self.closed = True
        with self._cond: self._cond.notify_all()

    def _enqueue(self, frame: bytes) -> None:
        with self._cond:
            self._rx += frame; self._cond.notify_all()

    def push_host_event(self, rid: int, rtype: int, data: bytes) -> None:
        self._enqueue(build_frame(MsgType.HOST_EVENT, 0,
                                   bytes([rid, rtype]) + data))

    def push_log(self, text: str) -> None:
        self._enqueue(build_frame(MsgType.LOG, 0, text.encode()))

    def _status(self) -> bytes:
        return build_frame(MsgType.STATUS, 0,
                           bytes([self.flags, self.proto_version]))

    def _on_command(self, t: int, s: int, p: bytes) -> None:
        self.received.append((t, s, bytes(p)))
        if t == MsgType.PING:
            self._enqueue(self._status())
        elif t == MsgType.GET_CAPS:
            self._enqueue(build_frame(MsgType.CAPS, s, self.caps_payload))
        elif t in (MsgType.SEND_REPORT, MsgType.RELEASE_ALL, MsgType.SET_FEATURE):
            if s in self.nack_seqs:
                self._enqueue(build_frame(MsgType.NACK, 0, bytes([s, NackReason.BAD_LEN])))
                return
            if self.drop_first_ack and s not in self._acked:
                self._acked.add(s); return
            self._enqueue(build_frame(MsgType.ACK, 0, bytes([s])))
        elif t == MsgType.SET_IDENTITY:
            self._enqueue(build_frame(MsgType.ACK, 0, bytes([s])))
