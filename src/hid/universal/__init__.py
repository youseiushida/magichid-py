"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .arcade import ArcadeIO
from .aux_display import AuxDisplay
from .barcode_scanner import BarcodeScanner
from .battery_system import BatterySystem
from .braille import BrailleDisplay
from .button_panel import ButtonPanel, PanelButton
from .camera_control import CameraControl
from .consumer_control import ConsumerControl, ConsumerUsage
from .digitizer import Digitizer
from .eye_tracker import EyeTracker
from .fido import FIDO
from .gamepad import Gamepad
from .generic_device import GenericDevice
from .haptics import Haptics
from .simulation import FlightSim
from .gaming_device import GamingDevice
from .sport import GolfClub
from .keyboard import Keyboard, KeycodeError
from .led import LED
from .lighting import LampArray
from .medical import MedicalUltrasound
from .monitor import Monitor
from .monitor_enum import MonitorEnum
from .mouse import Mouse, MouseButton
from .msr import MSR
from .ordinal import Ordinal
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
    "BatterySystem",
    "BrailleDisplay",
    "ButtonPanel", "CameraControl",
    "ConsumerControl", "ConsumerUsage",
    "Digitizer",
    "EyeTracker",
    "FIDO",
    "FlightSim",
    "Gamepad",
    "GamingDevice",
    "GenericDevice",
    "GolfClub",
    "Haptics",
    "Keyboard", "KeycodeError", "LampArray", "LED", "MedicalUltrasound", "Monitor", "MonitorEnum",
    "Mouse", "MouseButton", "MSR",
    "Ordinal",
    "PanelButton",
    "PID",
    "Scale",
    "SoCControl",
    "Telephony",
    "UnicodeInput",
    "UPS",
    "VESAVC",
    "VRHeadset",
]
