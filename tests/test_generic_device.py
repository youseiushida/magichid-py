from __future__ import annotations
import pytest
from hid import IHidClient, GenericDevice
from core.reports import ReportTable
from core.wire import MsgType

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
def gd(client, table): return GenericDevice(client, table)

def test_set(gd, client):
    gd.set(battery_strength=80, wireless_channel=3, rf_signal=200, sequence_id=1)
    p = client.last[1]
    assert p[0] == 6 and p[1:5] == bytes([80, 3, 200, 1])

def test_wireless_id(gd, client):
    gd.set_wireless_id(0x12345678)
    assert client.last[0] == MsgType.SET_FEATURE
    p = client.last[1]
    assert p[0] == 6 and p[1] == 0x78 and p[2] == 0x56  # LE

def test_fake(): (lambda c: c.request(0x01, b"\x00"))(_FakeClient())
