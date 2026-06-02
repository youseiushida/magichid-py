"""HORIPAD (Nintendo Switch) profile — single controller report.

Switching to this profile requires ``SET_IDENTITY``, which triggers a
physical USB re-enumeration.
"""

from .controller import Horipad, HoripadButton, HoripadDpad

__all__ = ["Horipad", "HoripadButton", "HoripadDpad"]
