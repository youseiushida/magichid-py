"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .button_panel import ButtonPanel, PanelButton
from .camera_control import CameraAction, CameraControl
from .consumer_control import ConsumerControl, ConsumerUsage
from .digitizer import Digitizer
from .fido import FIDO
from .gamepad import Gamepad, GamepadButton, GamepadDPad
from .keyboard import Keyboard, KeycodeError
from .mouse import Mouse, MouseButton
from .soc_control import SoCControl
from .telephony import Telephony, TelephonyUsage
from .unicode_input import UnicodeInput

__all__ = [
    "ButtonPanel", "CameraAction", "CameraControl",
    "ConsumerControl", "ConsumerUsage",
    "Digitizer",
    "FIDO",
    "Gamepad", "GamepadButton", "GamepadDPad",
    "Keyboard", "KeycodeError", "Mouse", "MouseButton", "PanelButton",
    "SoCControl",
    "Telephony", "TelephonyUsage",
    "UnicodeInput",
]
