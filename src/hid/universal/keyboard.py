"""Stateful boot-keyboard (6KRO) on top of an :class:`IHidClient`.

6KRO = up to 6 simultaneous non-modifier keycodes per HID boot protocol.
Modifier keys (Ctrl/Shift/Alt/GUI) are tracked in the modifier byte and
do NOT consume a keycode slot.

Conforms to:
* HID Usage Tables 1.7 §10 (Keyboard/Keypad Page 0x07)
* HID Device Class Definition, Appendix B (Boot Interface Descriptors)
"""

from __future__ import annotations

from core.events import HostEventReceived
from core.reports import KEYBOARD, ReportTable
from core.wire import HidReportType, MsgType

from .._client import IHidClient
from .._tables.keycode import Keycode

# -- LED bit mapping (Boot Keyboard OUTPUT report, HID Spec Appendix B) -------
_LED_NUM_LOCK = 1 << 0
_LED_CAPS_LOCK = 1 << 1
_LED_SCROLL_LOCK = 1 << 2
_LED_COMPOSE = 1 << 3
_LED_KANA = 1 << 4

# -- modifier key-to-bit mapping ----------------------------------------------
_MOD_MAP: dict[Keycode, int] = {k: 1 << (k - 0xE0) for k in Keycode if k.is_modifier}


class Keyboard:
    """Boot-keyboard state machine with 6KRO management and LED tracking.

    Usage::

        kb = Keyboard(client, ReportTable.universal())
        kb.press(Keycode.A)
        kb.press(Keycode.LEFT_SHIFT, Keycode.B)
        kb.release_all()

    *press* sends a report immediately.  *release* sends a report immediately.
    For bursts of changes use the context manager to batch::

        with kb.batch():
            kb.press(Keycode.A)
            kb.press(Keycode.B)
        # one report sent on exit

    **LED state** — feed :class:`HostEventReceived` events from the connection::

        for ev in client.drain_events():
            if isinstance(ev, HostEventReceived):
                kb.handle_host_event(ev)
        print(kb.caps_lock_on)  # True if host says Caps Lock is lit
    """

    # -- constructor ---------------------------------------------------------- #

    def __init__(
        self,
        client: IHidClient,
        table: ReportTable,
        *,
        rollover: bool = False,
    ) -> None:
        """*client*: anything satisfying :class:`IHidClient`.

        *table*: ``ReportTable.universal()`` or equivalent.

        *rollover*: if True, pressing a 7th key sends ErrorRollOver (0x01) in
        all 6 keycode slots instead of raising :class:`KeycodeError`.
        """
        self._client = client
        self._table = table
        self._rollover = rollover
        self._modifier: int = 0
        self._keys: list[int] = []  # max 6, sorted for deterministic ordering
        self._led_byte: int = 0
        self._batched: bool = False
        self._dirty: bool = False

    # -- state queries -------------------------------------------------------- #

    @property
    def modifier(self) -> int:
        """Current modifier byte bitmap."""
        return self._modifier

    @property
    def keys(self) -> tuple[int, ...]:
        """Currently pressed non-modifier keycodes (up to 6)."""
        return tuple(self._keys)

    def is_pressed(self, keycode: Keycode) -> bool:
        """True if *keycode* is currently held."""
        if keycode.is_modifier:
            return bool(self._modifier & _MOD_MAP[keycode])
        return keycode in self._keys

    # -- LED state (updated via handle_host_event) ---------------------------- #

    @property
    def led_byte(self) -> int:
        """Last LED state byte received from the host (0 if none)."""
        return self._led_byte

    @property
    def num_lock_on(self) -> bool:
        return bool(self._led_byte & _LED_NUM_LOCK)

    @property
    def caps_lock_on(self) -> bool:
        return bool(self._led_byte & _LED_CAPS_LOCK)

    @property
    def scroll_lock_on(self) -> bool:
        return bool(self._led_byte & _LED_SCROLL_LOCK)

    @property
    def compose_on(self) -> bool:
        return bool(self._led_byte & _LED_COMPOSE)

    @property
    def kana_on(self) -> bool:
        return bool(self._led_byte & _LED_KANA)

    def handle_host_event(self, event: HostEventReceived) -> None:
        """Feed a :class:`HostEventReceived` from the connection event stream.

        When *event* is a keyboard OUTPUT report (LED state), the internal
        LED state is updated.  Other report IDs are ignored.
        """
        if (
            event.report_id == KEYBOARD
            and event.report_type == HidReportType.OUTPUT
            and event.data
        ):
            self._led_byte = event.data[0]

    # -- press / release ------------------------------------------------------ #

    def press(self, *keycodes: Keycode) -> None:
        """Press one or more keys.  Modifiers go to modifier byte automatically."""
        for kc in keycodes:
            self._press_one(kc)
        self._maybe_flush()

    def release(self, *keycodes: Keycode) -> None:
        """Release one or more keys."""
        for kc in keycodes:
            self._release_one(kc)
        self._maybe_flush()

    def tap(self, *keycodes: Keycode) -> None:
        """Press and immediately release (convenience for single keystrokes)."""
        self.press(*keycodes)
        self.release(*keycodes)

    def release_all(self) -> None:
        """Release every held key and send an empty report."""
        self._modifier = 0
        self._keys.clear()
        self._flush()

    # -- batch context -------------------------------------------------------- #

    def batch(self) -> _BatchGuard:
        """Context manager: defer flush until exit.

        >>> with kb.batch():
        ...     kb.press(Keycode.A)
        ...     kb.press(Keycode.B)
        # sends one report
        """
        return _BatchGuard(self)

    # -- internals ------------------------------------------------------------ #

    def _press_one(self, kc: Keycode) -> None:
        if kc == Keycode.NONE:
            return
        if kc.is_modifier:
            self._modifier |= _MOD_MAP[kc]
            self._dirty = True
            return
        if kc in self._keys:
            return  # already held — no-op
        if len(self._keys) >= 6:
            if self._rollover:
                self._keys[:] = [Keycode.ERROR_ROLL_OVER] * 6
                self._dirty = True
                return
            raise KeycodeError(
                f"6KRO limit: cannot press {kc.name} — already holding "
                f"{[Keycode(k).name for k in self._keys]}"
            )
        self._keys.append(kc)
        self._keys.sort()
        self._dirty = True

    def _release_one(self, kc: Keycode) -> None:
        if kc.is_modifier:
            self._modifier &= ~_MOD_MAP[kc]
            self._dirty = True
            return
        if kc in self._keys:
            self._keys.remove(kc)
            self._dirty = True

    def _maybe_flush(self) -> None:
        if not self._batched:
            self._flush()

    def _flush(self) -> None:
        if not self._dirty:
            return
        kc = list(self._keys)
        kc += [0] * (6 - len(kc))
        report = bytes([self._modifier & 0xFF, 0, *(k & 0xFF for k in kc)])
        payload = bytes([KEYBOARD]) + self._table.pad_input(KEYBOARD, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
        self._dirty = False


class _BatchGuard:
    def __init__(self, kb: Keyboard) -> None:
        self._kb = kb

    def __enter__(self) -> Keyboard:
        self._kb._batched = True
        return self._kb

    def __exit__(self, *_: object) -> None:
        self._kb._batched = False
        self._kb._maybe_flush()


class KeycodeError(ValueError):
    """Raised on invalid keycode operations (e.g. 6KRO overflow)."""
