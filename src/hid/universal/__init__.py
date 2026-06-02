"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .button_panel import ButtonPanel, PanelButton
from .keyboard import Keyboard, KeycodeError
from .mouse import Mouse, MouseButton

__all__ = ["ButtonPanel", "Keyboard", "KeycodeError", "Mouse", "MouseButton", "PanelButton"]
