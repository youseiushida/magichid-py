"""Universal profile (35-in-1) devices — all usable simultaneously without re-enumeration.

These are the "well-known" HID reports from the MagicHID universal USB descriptor.
"""

from .keyboard import Keyboard, KeycodeError
from .mouse import Mouse, MouseButton

__all__ = ["Keyboard", "KeycodeError", "Mouse", "MouseButton"]
