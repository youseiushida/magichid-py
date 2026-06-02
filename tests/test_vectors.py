"""Conformance tests: every line of spec/protocol_vectors.txt must be reproduced
byte-for-byte, plus a CRC-16/CCITT-FALSE known-answer test anchored to the world
(crc16(b"123456789") == 0x29B1) that breaks the circularity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.codec import build_frame, cobs_decode, cobs_encode, crc16, parse_frame

_VECTORS = (Path(__file__).parent / "protocol_vectors.txt").read_text(encoding="utf-8")


def _payload(token: str) -> bytes:
    return b"" if token == "-" else bytes.fromhex(token)


def _load():
    frames, cobses = [], []
    for n, raw in enumerate(_VECTORS.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "FRAME":
            frames.append((n, int(parts[1], 16), int(parts[2]), _payload(parts[3]), parts[4].lower()))
        elif parts[0] == "COBS":
            cobses.append((n, bytes.fromhex(parts[1]), parts[2].lower()))
    return frames, cobses


FRAMES, COBSES = _load()


def _fid(v):
    return f"L{v[0]}-t{v[1]:02x}-s{v[2]}"


def _cid(v):
    return f"L{v[0]}-{len(v[1])}B"


# -- file loaded -----------------------------------------------------------
def test_vectors_loaded():
    assert FRAMES and COBSES


# -- CRC-16/CCITT-FALSE known answer ---------------------------------------
def test_crc16_check_value():
    assert crc16(b"123456789") == 0x29B1


def test_crc16_empty():
    assert crc16(b"") == 0xFFFF


# -- FRAME: build matches vector, parse round-trips ------------------------
@pytest.mark.parametrize("v", FRAMES, ids=_fid)
def test_build_frame(v):
    _, t, s, p, fhex = v
    assert build_frame(t, s, p).hex() == fhex


@pytest.mark.parametrize("v", FRAMES, ids=_fid)
def test_parse_frame(v):
    _, t, s, p, fhex = v
    frame = bytes.fromhex(fhex)
    assert frame[-1] == 0x00
    assert parse_frame(frame[:-1]) == (t, s, p)


# -- COBS: encode matches, decode inverts ----------------------------------
@pytest.mark.parametrize("v", COBSES, ids=_cid)
def test_cobs_encode(v):
    _, inp, ehex = v
    assert cobs_encode(inp).hex() == ehex


@pytest.mark.parametrize("v", COBSES, ids=_cid)
def test_cobs_decode(v):
    _, inp, ehex = v
    assert cobs_decode(bytes.fromhex(ehex)) == inp
    assert 0x00 not in bytes.fromhex(ehex)


# -- structural ------------------------------------------------------------
def test_frame_ends_with_delimiter():
    f = build_frame(0x02, 1, b"")
    assert f[-1] == 0x00 and 0x00 not in f[:-1]


def test_parse_rejects_bad_crc():
    f = bytearray(build_frame(0x01, 7, b"\x01\x02\x03"))
    f[1] ^= 0x01
    with pytest.raises(ValueError):
        parse_frame(bytes(f[:-1]))
