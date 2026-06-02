"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .button_panel import ButtonPanel, PanelButton
from .consumer_control import ConsumerControl, ConsumerUsage
from .gamepad import Gamepad, GamepadButton, GamepadDPad
from .keyboard import Keyboard, KeycodeError
from .mouse import Mouse, MouseButton

__all__ = [
    "ButtonPanel", "ConsumerControl", "ConsumerUsage",
    "Gamepad", "GamepadButton", "GamepadDPad",
    "Keyboard", "KeycodeError", "Mouse", "MouseButton", "PanelButton",
]
