from __future__ import annotations
import pytest
from hid import IHidClient, BatterySystem
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
def bat(client, table): return BatterySystem(client, table)

def test_set(bat, client):
    bat.set(remaining_capacity=4000, full_charge_capacity=5000,
            run_time_to_empty=7200, cycle_count=150,
            state_of_charge=80, charging=True, ac_present=True)
    p = client.last[1]
    assert p[0] == 28
    # remaining=4000 → LE [0xA0, 0x0F]
    assert p[1] == 0xA0 and p[2] == 0x0F
    # charge pct at offset 8
    assert p[9] == 80
    # flags at offset 9: charging(1) + ac_present(4) = 5
    assert p[10] == 0x05

def test_fake(): (lambda c: c.request(0x01, b"\x00"))(_FakeClient())
