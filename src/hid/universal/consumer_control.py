"""Consumer Control device (report ID 12, 2-byte) on top of an :class:`IHidClient`.

Conforms to:
* HID Usage Tables 1.7 §15 (Consumer Page 0x0C)

The report is a single 16-bit Consumer Page usage ID (little-endian).
Press sends the usage ID; release sends 0x0000.  Only one action at a time.
"""

from __future__ import annotations

from enum import IntEnum

from core.reports import ReportTable
from core.wire import MsgType

from .._client import IHidClient

_REPORT_ID = 12  # REPORT_ID_CONSUMER


class ConsumerUsage(IntEnum):
    """HID Consumer Page (0x0C) usage IDs — common media, audio, and browser keys."""

    # -- system / power (§15.3) -----------------------------------------------
    POWER = 0x0030
    SLEEP = 0x0032

    # -- menu (§15.4) ---------------------------------------------------------
    MENU = 0x0040

    # -- media transport (§15.7) ----------------------------------------------
    PLAY = 0x00B0
    PAUSE = 0x00B1
    RECORD = 0x00B2
    FAST_FORWARD = 0x00B3
    REWIND = 0x00B4
    SCAN_NEXT_TRACK = 0x00B5
    SCAN_PREV_TRACK = 0x00B6
    STOP = 0x00B7
    EJECT = 0x00B8
    RANDOM_PLAY = 0x00B9
    REPEAT = 0x00BC
    PLAY_PAUSE = 0x00CD

    # -- audio (§15.9) --------------------------------------------------------
    MUTE = 0x00E2
    VOLUME_INCREMENT = 0x00E9
    VOLUME_DECREMENT = 0x00EA
    BASS_INCREMENT = 0x0152
    BASS_DECREMENT = 0x0153
    TREBLE_INCREMENT = 0x0154
    TREBLE_DECREMENT = 0x0155

    # -- application launch (§15.15) ------------------------------------------
    AL_CALCULATOR = 0x0192
    AL_EMAIL = 0x018A
    AL_LOCAL_BROWSER = 0x0194        # My Computer / File Explorer
    AL_INTERNET_BROWSER = 0x0196
    AL_SEARCH_BROWSER = 0x01C6
    AL_CONTACTS = 0x018D
    AL_CALENDAR = 0x018E
    AL_NEXT_TASK = 0x01A3            # Alt+Tab
    AL_PREV_TASK = 0x01A4            # Alt+Shift+Tab

    # -- application control (§15.16) -----------------------------------------
    AC_SEARCH = 0x0221
    AC_HOME = 0x0223
    AC_BACK = 0x0224
    AC_FORWARD = 0x0225
    AC_STOP = 0x0226
    AC_REFRESH = 0x0227
    AC_BOOKMARKS = 0x022A
    AC_ZOOM_IN = 0x022D
    AC_ZOOM_OUT = 0x022E
    AC_FULL_SCREEN = 0x0230
    AC_NEW_WINDOW = 0x0239


class ConsumerControl:
    """Consumer-page control device (report ID 12) — media keys, browser keys, etc.

    Usage::

        cc = ConsumerControl(client, ReportTable.universal())

        cc.tap(ConsumerUsage.PLAY_PAUSE)
        cc.tap(ConsumerUsage.VOLUME_INCREMENT)
        cc.tap(ConsumerUsage.AC_BACK)

    For keys that need a hold (e.g. volume auto-repeat)::

        cc.press(ConsumerUsage.VOLUME_INCREMENT)
        # ... wait ...
        cc.release()
    """

    def __init__(self, client: IHidClient, table: ReportTable) -> None:
        self._client = client
        self._table = table
        self._current: int = 0  # currently held usage ID, 0 = nothing

    # -- state ---------------------------------------------------------------- #

    @property
    def current(self) -> int:
        """Currently held usage ID, or 0 if nothing is pressed."""
        return self._current

    @property
    def is_active(self) -> bool:
        """True if a consumer key is currently held."""
        return self._current != 0

    # -- press / release ------------------------------------------------------ #

    def press(self, usage: ConsumerUsage) -> None:
        """Press a consumer key (held until :meth:`release`).

        If another key is already held, it is released first.
        """
        if self._current == usage:
            return  # already holding this
        self._current = int(usage)
        self._send()

    def release(self) -> None:
        """Release the currently held consumer key."""
        if self._current == 0:
            return
        self._current = 0
        self._send()

    def tap(self, usage: ConsumerUsage) -> None:
        """Press and immediately release (convenience for most consumer keys)."""
        self.press(usage)
        self.release()

    # -- internals ------------------------------------------------------------ #

    def _send(self) -> None:
        v = self._current
        report = bytes([v & 0xFF, (v >> 8) & 0xFF])
        payload = bytes([_REPORT_ID]) + self._table.pad_input(_REPORT_ID, report)
        self._client.request(MsgType.SEND_REPORT, payload, reliable=False)
