from __future__ import annotations
import pytest
from hid import IHidClient, EyeTracker
from core.reports import ReportTable

class _FakeClient:
    def __init__(self): self.calls = []
    def request(self, t, p, *, reliable=True): self.calls.append((t, p, reliable))
    @property
    def last(self): return self.calls[-1]

@pytest.fixture
def client(): return _FakeClient()
@pytest.fixture
def table(): return ReportTable.universal()
@pytest.fixture
def et(client, table): return EyeTracker(client, table)

def test_set(et, client):
    et.set(timestamp=12345678, x=100, y=-50)
    p = client.last[1]
    assert p[0] == 18
    # timestamp: 12345678 = 0xBC614E → LE [0x4E, 0x61, 0xBC, 0x00]
    assert p[1] == 0x4E and p[2] == 0x61 and p[3] == 0xBC
    # x=100 → LE [0x64, 0x00], y=-50 → LE [0xCE, 0xFF]
    assert p[5] == 0x64 and p[7] == 0xCE

def test_fake(): (lambda c: c.request(0x01, b"\x00"))(_FakeClient())
