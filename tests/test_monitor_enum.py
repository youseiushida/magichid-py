from __future__ import annotations
import pytest
from hid import IHidClient, MonitorEnum
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
def me(client, table): return MonitorEnum(client, table)

def test_set(me, client):
    me.set(3)
    assert me.usage == 3
    assert client.last[0] == MsgType.SET_FEATURE
    assert client.last[1][1] == 3

def test_clamp(me):
    me.set(20)
    assert me.usage == 16

def test_fake(): (lambda c: c.request(0x01, b"\x00"))(_FakeClient())
