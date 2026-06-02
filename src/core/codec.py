"""Wire codec: CRC-16/CCITT-FALSE + COBS + framing.

Port of the reference C implementation ``spec/mh_protocol.h``.
The golden oracle is ``spec/protocol_vectors.txt`` —
``tests/test_vectors.py`` proves byte-for-byte conformance.

Wire frame::

    wire = COBS( BODY ) ++ 0x00
    BODY = TYPE(1) SEQ(1) PAYLOAD(0..N) CRC16(2, little-endian)
"""

from __future__ import annotations

__all__ = ["DELIMITER", "MAX_PAYLOAD", "CodecError", "crc16", "cobs_encode", "cobs_decode",
           "build_frame", "parse_frame"]

DELIMITER = 0x00
MAX_PAYLOAD = 192


class CodecError(ValueError):
    """A frame failed COBS structure or CRC validation."""


# -- CRC-16/CCITT-FALSE ----------------------------------------------------
def crc16(data: bytes) -> int:
    """poly=0x1021 init=0xFFFF no-reflection xorout=0.
    KAT: crc16(b"123456789") == 0x29B1."""
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


# -- COBS ------------------------------------------------------------------
def cobs_encode(data: bytes) -> bytes:
    """COBS-encode, no delimiter appended.  Output never contains 0x00."""
    out = bytearray(b"\x00")
    code_i, code = 0, 1
    for b in data:
        if b == 0:
            out[code_i] = code; code_i = len(out); out.append(0); code = 1
        else:
            out.append(b); code += 1
            if code == 0xFF:
                out[code_i] = code; code_i = len(out); out.append(0); code = 1
    out[code_i] = code
    return bytes(out)


def cobs_decode(data: bytes) -> bytes:
    """Inverse of cobs_encode.  Raises CodecError on malformed block."""
    out, i, n = bytearray(), 0, len(data)
    while i < n:
        code = data[i]; i += 1
        if code == 0:
            raise CodecError("0x00 inside COBS block")
        for _ in range(1, code):
            if i >= n:
                raise CodecError("COBS block overruns input")
            out.append(data[i]); i += 1
        if code != 0xFF and i < n:
            out.append(0)
    return bytes(out)


# -- framing ---------------------------------------------------------------
def build_frame(type_: int, seq: int, payload: bytes = b"") -> bytes:
    """Build one wire frame: COBS body + trailing 0x00."""
    if not (0 <= type_ <= 0xFF and 0 <= seq <= 0xFF):
        raise ValueError("type/seq out of range")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload {len(payload)} > {MAX_PAYLOAD}")
    body = bytearray((type_, seq)) + payload
    c = crc16(bytes(body))
    body += bytes([c & 0xFF, (c >> 8) & 0xFF])
    return cobs_encode(bytes(body)) + b"\x00"


def parse_frame(chunk: bytes) -> tuple[int, int, bytes]:
    """Parse a de-framed COBS chunk (no trailing 0x00).
    Returns (type, seq, payload).  Raises CodecError on COBS/CRC failure."""
    dec = cobs_decode(chunk)
    if len(dec) < 4:
        raise CodecError("frame too short")
    if crc16(dec[:-2]) != (dec[-2] | (dec[-1] << 8)):
        raise CodecError("CRC mismatch")
    return dec[0], dec[1], bytes(dec[2:-2])
