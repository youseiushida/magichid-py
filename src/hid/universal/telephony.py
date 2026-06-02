"""Telephony device (report ID 11, 2-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §14 (Telephony Device Page 0x0B)

Wire format: single 16-bit Telephony Page usage ID (little-endian).
Press sends the usage ID; release sends 0x0000.  One action at a time.

Some usages are OSC (one-shot: Flash, Redial, Send), others are
OOC (stateful: Hook Switch, Hold, Mute, Speaker Phone).
The API handles both — use :meth:`tap` for OSC, :meth:`press`/:meth:`release` for OOC.

The report also has ``output_bytes=1`` for line-status LED indicators
(see :meth:`handle_host_event`).
"""

from __future__ import annotations

from enum import IntEnum

from core.events import HostEventReceived
from core.reports import ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient

_REPORT_ID = 11  # REPORT_ID_TELEPHONY


class TelephonyUsage(IntEnum):
    """HID Telephony Device Page (0x0B) usage IDs — call control, keypad, and messaging."""

    # -- call control (§14.3) -------------------------------------------------
    HOOK_SWITCH = 0x20       # OOC: off-hook / on-hook
    FLASH = 0x21             # MC: flash hook (momentary)
    FEATURE = 0x22           # OSC
    HOLD = 0x23              # OOC
    REDIAL = 0x24            # OSC
    TRANSFER = 0x25          # OSC
    DROP = 0x26              # OSC: hang up / drop call
    PARK = 0x27              # OOC
    FORWARD_CALLS = 0x28     # OOC
    ALTERNATE_FUNCTION = 0x29  # MC
    LINE = 0x2A              # OSC/NAry: select line
    SPEAKER_PHONE = 0x2B     # OOC
    CONFERENCE = 0x2C        # OOC
    RING_ENABLE = 0x2D       # OOC
    RING_SELECT = 0x2E       # OSC
    MUTE = 0x2F              # OOC: phone mute
    CALLER_ID = 0x30         # MC
    SEND = 0x31              # OOC: dial / send

    # -- speed dial (§14.4) ---------------------------------------------------
    SPEED_DIAL = 0x50        # OSC
    STORE_NUMBER = 0x51      # OSC
    RECALL_NUMBER = 0x52     # OSC
    PHONE_DIRECTORY = 0x53   # OOC

    # -- messaging (§14.5) ----------------------------------------------------
    VOICE_MAIL = 0x70        # OOC
    SCREEN_CALLS = 0x71      # OOC
    DO_NOT_DISTURB = 0x72    # OOC
    MESSAGE = 0x73           # OSC
    ANSWER_ON_OFF = 0x74     # OOC

    # -- keypad (§14.2) -------------------------------------------------------
    KEY_0 = 0xB0
    KEY_1 = 0xB1
    KEY_2 = 0xB2
    KEY_3 = 0xB3
    KEY_4 = 0xB4
    KEY_5 = 0xB5
    KEY_6 = 0xB6
    KEY_7 = 0xB7
    KEY_8 = 0xB8
    KEY_9 = 0xB9
    KEY_STAR = 0xBA
    KEY_POUND = 0xBB
    KEY_A = 0xBC
    KEY_B = 0xBD
    KEY_C = 0xBE
    KEY_D = 0xBF


# -- LED bits (telephony OUTPUT report, LED Page 0x08 indicators) --------------
_LED_MESSAGE = 1 << 0


class Telephony:
    """Telephony control device (report ID 11) — call control, keypad, messaging.

    Usage::

        tel = Telephony(client, ReportTable.universal())

        # one-shot actions
        tel.tap(TelephonyUsage.REDIAL)
        tel.tap(TelephonyUsage.KEY_5)

        # stateful controls
        tel.press(TelephonyUsage.HOOK_SWITCH)   # off-hook
        tel.tap(TelephonyUsage.KEY_1)           # dial 1
        tel.release()                           # on-hook

        # LED feedback
        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                tel.handle_host_event(ev)
        print(tel.message_waiting)  # True if message indicator is lit
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._current: int = 0       # currently held usage, 0 = nothing
        self._led_byte: int = 0

    # -- state ---------------------------------------------------------------- #

    @property
    def current(self) -> int:
        """Currently held usage ID, or 0 if nothing is pressed."""
        return self._current

    @property
    def is_active(self) -> bool:
        """True if a telephony control is currently held."""
        return self._current != 0

    # -- LED feedback --------------------------------------------------------- #

    @property
    def led_byte(self) -> int:
        """Last LED state byte received from the host (0 if none)."""
        return self._led_byte

    @property
    def message_waiting(self) -> bool:
        """True if the host says a message is waiting (LED indicator)."""
        return bool(self._led_byte & _LED_MESSAGE)

    def handle_host_event(self, event: HostEventReceived) -> None:
        """Feed a :class:`HostEventReceived` from the connection event stream.

        When *event* is a telephony OUTPUT report, the message-waiting LED
        state is updated.
        """
        if (
            event.report_id == _REPORT_ID
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._led_byte = event.data[0]

    # -- press / release ------------------------------------------------------ #

    def press(self, usage: TelephonyUsage) -> None:
        """Press a telephony control (held until :meth:`release`).

        If another control is already held, it is replaced.
        """
        if self._current == usage:
            return
        self._current = int(usage)
        self._send()

    def release(self) -> None:
        """Release the currently held control."""
        if self._current == 0:
            return
        self._current = 0
        self._send()

    def tap(self, usage: TelephonyUsage) -> None:
        """Press and immediately release (convenience for one-shot usages)."""
        self.press(usage)
        self.release()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        v = self._current
        report = bytes([v & 0xFF, (v >> 8) & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
