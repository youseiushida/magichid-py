"""Telephony device (report ID 11, 2-byte INPUT + 1-byte OUTPUT).

Conforms to:
* universal_reports.yaml — report ID 11, Page 0x000B (Telephony Device), Phone

Wire format:
  INPUT:  ``[flags][keypad_value]``
    flags: bit 0=hook_switch, 1=flash, 2=hold, 3=phone_mute, 4=send, 5-7=padding
    keypad_value: 0-12 selector mapping to phone keys 0xB0-0xBB
  OUTPUT: ``[led_flags]``
    bits: 0=off_hook, 1=ring, 2=message_waiting, 3-7=padding
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 11

# -- INPUT flag bits ----------------------------------------------------------
_F_HOOK_SWITCH = 1 << 0
_F_FLASH = 1 << 1
_F_HOLD = 1 << 2
_F_PHONE_MUTE = 1 << 3
_F_SEND = 1 << 4

# -- OUTPUT LED bits ----------------------------------------------------------
_L_OFF_HOOK = 1 << 0
_L_RING = 1 << 1
_L_MESSAGE_WAITING = 1 << 2

# -- keypad mapping: value 0-12 → phone key usage 0xB0-0xBB
_KP_NAMES = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#", "A"]

_KEYPAD_MAP: dict[int, int] = {i: 0xB0 + i for i in range(13)}


class Telephony:
    """Phone device (report ID 11) — hook control + keypad.

    Usage::

        tel = Telephony(client, ReportTable.universal())

        tel.hook_switch = True           # off-hook
        tel.mute = True
        tel.keypad_press(5)              # dial '5'
        tel.send()                       # send report

        # receive LED state from host
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                tel.handle_host_event(ev)
        print(tel.message_waiting)
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._flags: int = 0
        self._keypad: int = 0  # 0 = no key pressed
        # LED state from host
        self._off_hook: bool = False
        self._ring: bool = False
        self._message_waiting: bool = False

    # -- INPUT state ---------------------------------------------------------- #

    @property
    def hook_switch(self) -> bool:
        return bool(self._flags & _F_HOOK_SWITCH)

    @hook_switch.setter
    def hook_switch(self, on: bool) -> None:
        self._flags = _set_bit(self._flags, _F_HOOK_SWITCH, on)

    @property
    def flash(self) -> bool:
        return bool(self._flags & _F_FLASH)

    @flash.setter
    def flash(self, on: bool) -> None:
        self._flags = _set_bit(self._flags, _F_FLASH, on)

    @property
    def hold(self) -> bool:
        return bool(self._flags & _F_HOLD)

    @hold.setter
    def hold(self, on: bool) -> None:
        self._flags = _set_bit(self._flags, _F_HOLD, on)

    @property
    def mute(self) -> bool:
        return bool(self._flags & _F_PHONE_MUTE)

    @mute.setter
    def mute(self, on: bool) -> None:
        self._flags = _set_bit(self._flags, _F_PHONE_MUTE, on)

    @property
    def send_key(self) -> bool:
        return bool(self._flags & _F_SEND)

    @send_key.setter
    def send_key(self, on: bool) -> None:
        self._flags = _set_bit(self._flags, _F_SEND, on)

    @property
    def keypad(self) -> int:
        """Current keypad value (0-12 = phone keys 0-9, *, #, A).  0 = no key."""
        return self._keypad

    def keypad_press(self, key: int) -> None:
        """Set keypad to *key* (0-12).  0 = no key pressed."""
        if not (0 <= key <= 12):
            raise ValueError(f"keypad key must be 0-12, got {key}")
        self._keypad = key
        self._send()

    # -- OUTPUT state (from host) --------------------------------------------- #

    @property
    def off_hook(self) -> bool:
        """True if host says the phone is off-hook."""
        return self._off_hook

    @property
    def ring(self) -> bool:
        """True if host says the phone is ringing."""
        return self._ring

    @property
    def message_waiting(self) -> bool:
        """True if host says a message is waiting."""
        return self._message_waiting

    def handle_host_event(self, event: HostEventReceived) -> None:
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            b = event.data[0]
            self._off_hook = bool(b & _L_OFF_HOOK)
            self._ring = bool(b & _L_RING)
            self._message_waiting = bool(b & _L_MESSAGE_WAITING)

    # -- internals ------------------------------------------------------------ #

    def send(self) -> None:
        """Send the current INPUT report."""
        self._send()

    def _send(self) -> None:
        report = bytes([self._flags & 0xFF, self._keypad & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)


def _set_bit(flags: int, mask: int, on: bool) -> int:
    return flags | mask if on else flags & ~mask
