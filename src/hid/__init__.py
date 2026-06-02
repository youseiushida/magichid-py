"""High-level HID device builders on top of the ``core`` protocol layer.

- :class:`IHidClient` — DIP boundary (Protocol)
- :class:`Keycode` — HUT 0x07 usage table as :class:`IntEnum`
- :class:`MouseButton` — HID Button Page (0x09)

Profile-specific devices live in sub-packages:

* ``hid.universal`` — 35-in-1 profile (PC: keyboard, mouse, gamepad, …)
* ``hid.horipad`` — Nintendo Switch controller profile (single report)
"""

from __future__ import annotations

from ._client import IHidClient
from ._tables.keycode import Keycode
from .universal import (
    ArcadeIO,
    AuxDisplay,
    BarcodeScanner,
    ButtonPanel, CameraControl,
    ConsumerControl, ConsumerUsage,
    Digitizer,
    FIDO,
    FlightSim,
    Gamepad,
    GamingDevice,
    GolfClub,
    Haptics,
    Keyboard, KeycodeError, Monitor, Mouse, MouseButton, MSR, PanelButton,
    PID,
    SoCControl,
    Telephony,
    UnicodeInput,
    UPS,
    VESAVC,
    VRHeadset,
)

__all__ = [
    "ArcadeIO",
    "AuxDisplay",
    "BarcodeScanner",
    "ButtonPanel", "CameraControl",
    "ConsumerControl", "ConsumerUsage",
    "Digitizer",
    "FIDO",
    "FlightSim",
    "Gamepad",
    "GamingDevice",
    "GolfClub",
    "Haptics",
    "IHidClient",
    "Keycode",
    "Keyboard", "KeycodeError",
    "Monitor",
    "Mouse", "MouseButton",
    "MSR",
    "PanelButton",
    "PID",
    "SoCControl",
    "Telephony",
    "UnicodeInput",
    "UPS",
    "VESAVC",
    "VRHeadset",
]
