"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .arcade import ArcadeIO
from .aux_display import AuxDisplay
from .barcode_scanner import BarcodeScanner
from .button_panel import ButtonPanel, PanelButton
from .camera_control import CameraControl
from .consumer_control import ConsumerControl, ConsumerUsage
from .digitizer import Digitizer
from .fido import FIDO
from .gamepad import Gamepad
from .haptics import Haptics
from .simulation import FlightSim
from .gaming_device import GamingDevice
from .sport import GolfClub
from .keyboard import Keyboard, KeycodeError
from .medical import MedicalUltrasound
from .monitor import Monitor
from .mouse import Mouse, MouseButton
from .msr import MSR
from .pid import PID
from .power_device import UPS
from .scale import Scale
from .sensor import Accelerometer
from .soc_control import SoCControl
from .telephony import Telephony
from .unicode_input import UnicodeInput
from .vesa_vc import VESAVC
from .vr_controls import VRHeadset

__all__ = [
    "Accelerometer",
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
    "Keyboard", "KeycodeError", "MedicalUltrasound", "Monitor", "Mouse", "MouseButton", "MSR", "PanelButton",
    "PID",
    "Scale",
    "SoCControl",
    "Telephony",
    "UnicodeInput",
    "UPS",
    "VESAVC",
    "VRHeadset",
]
