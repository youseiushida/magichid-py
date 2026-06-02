"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .button_panel import ButtonPanel, PanelButton
from .camera_control import CameraControl
from .consumer_control import ConsumerControl, ConsumerUsage
from .digitizer import Digitizer
from .fido import FIDO
from .gamepad import Gamepad
from .keyboard import Keyboard, KeycodeError
from .monitor import Monitor
from .mouse import Mouse, MouseButton
from .power_device import UPS
from .soc_control import SoCControl
from .telephony import Telephony
from .unicode_input import UnicodeInput

__all__ = [
    "ButtonPanel", "CameraControl",
    "ConsumerControl", "ConsumerUsage",
    "Digitizer",
    "FIDO",
    "Gamepad",
    "Keyboard", "KeycodeError", "Monitor", "Mouse", "MouseButton", "PanelButton",
    "SoCControl",
    "Telephony",
    "UnicodeInput",
    "UPS",
]
