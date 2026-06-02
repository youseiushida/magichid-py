"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .arcade import ArcadeIO
from .barcode_scanner import BarcodeScanner
from .button_panel import ButtonPanel, PanelButton
from .camera_control import CameraControl
from .consumer_control import ConsumerControl, ConsumerUsage
from .digitizer import Digitizer
from .fido import FIDO
from .gamepad import Gamepad
from .keyboard import Keyboard, KeycodeError
from .monitor import Monitor
from .mouse import Mouse, MouseButton
from .msr import MSR
from .power_device import UPS
from .soc_control import SoCControl
from .telephony import Telephony
from .unicode_input import UnicodeInput
from .vesa_vc import VESAVC

__all__ = [
    "ArcadeIO",
    "BarcodeScanner",
    "ButtonPanel", "CameraControl",
    "ConsumerControl", "ConsumerUsage",
    "Digitizer",
    "FIDO",
    "Gamepad",
    "Keyboard", "KeycodeError", "Monitor", "Mouse", "MouseButton", "MSR", "PanelButton",
    "SoCControl",
    "Telephony",
    "UnicodeInput",
    "UPS",
    "VESAVC",
]
