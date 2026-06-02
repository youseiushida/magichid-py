"""HID Usage IDs for Keyboard/Keypad Page (0x07).

Source: HID Usage Tables 1.7 §10 “Keyboard/Keypad Page (0x07)”.
Every keycode is the wire value used in the boot-keyboard 6KRO array.
"""

from __future__ import annotations

from enum import IntEnum


class Keycode(IntEnum):
    """HID Keyboard/Keypad Usage ID (wire value = enum value)."""

    # -- reserved / error ------------------------------------------------
    NONE = 0x00
    ERROR_ROLL_OVER = 0x01
    POST_FAIL = 0x02
    ERROR_UNDEFINED = 0x03

    # -- letters ---------------------------------------------------------
    A = 0x04
    B = 0x05
    C = 0x06
    D = 0x07
    E = 0x08
    F = 0x09
    G = 0x0A
    H = 0x0B
    I = 0x0C
    J = 0x0D
    K = 0x0E
    L = 0x0F
    M = 0x10
    N = 0x11
    O = 0x12
    P = 0x13
    Q = 0x14
    R = 0x15
    S = 0x16
    T = 0x17
    U = 0x18
    V = 0x19
    W = 0x1A
    X = 0x1B
    Y = 0x1C
    Z = 0x1D

    # -- numbers ---------------------------------------------------------
    ONE = 0x1E
    TWO = 0x1F
    THREE = 0x20
    FOUR = 0x21
    FIVE = 0x22
    SIX = 0x23
    SEVEN = 0x24
    EIGHT = 0x25
    NINE = 0x26
    ZERO = 0x27

    # -- whitespace / punctuation ----------------------------------------
    RETURN = 0x28            # ENTER (main keyboard)
    ESCAPE = 0x29
    BACKSPACE = 0x2A         # DELETE (backspace)
    TAB = 0x2B
    SPACEBAR = 0x2C
    MINUS = 0x2D             # - and _
    EQUAL = 0x2E             # = and +
    LEFT_BRACKET = 0x2F      # [ and {
    RIGHT_BRACKET = 0x30     # ] and }
    BACKSLASH = 0x31         # \ and |
    NONUS_HASH = 0x32        # Non-US # and ~
    SEMICOLON = 0x33         # ; and :
    APOSTROPHE = 0x34        # ' and "
    GRAVE = 0x35             # ` and ~
    COMMA = 0x36             # , and <
    PERIOD = 0x37            # . and >
    SLASH = 0x38             # / and ?

    # -- lock keys -------------------------------------------------------
    CAPS_LOCK = 0x39

    # -- function keys ---------------------------------------------------
    F1 = 0x3A
    F2 = 0x3B
    F3 = 0x3C
    F4 = 0x3D
    F5 = 0x3E
    F6 = 0x3F
    F7 = 0x40
    F8 = 0x41
    F9 = 0x42
    F10 = 0x43
    F11 = 0x44
    F12 = 0x45

    # -- navigation / editing --------------------------------------------
    PRINT_SCREEN = 0x46
    SCROLL_LOCK = 0x47
    PAUSE = 0x48
    INSERT = 0x49
    HOME = 0x4A
    PAGE_UP = 0x4B
    DELETE = 0x4C             # Delete Forward
    END = 0x4D
    PAGE_DOWN = 0x4E
    RIGHT_ARROW = 0x4F
    LEFT_ARROW = 0x50
    DOWN_ARROW = 0x51
    UP_ARROW = 0x52

    # -- keypad ----------------------------------------------------------
    KP_NUM_LOCK = 0x53
    KP_SLASH = 0x54
    KP_ASTERISK = 0x55
    KP_MINUS = 0x56
    KP_PLUS = 0x57
    KP_ENTER = 0x58
    KP_1 = 0x59             # KP_1 and End
    KP_2 = 0x5A             # KP_2 and Down Arrow
    KP_3 = 0x5B             # KP_3 and PageDn
    KP_4 = 0x5C             # KP_4 and Left Arrow
    KP_5 = 0x5D
    KP_6 = 0x5E             # KP_6 and Right Arrow
    KP_7 = 0x5F             # KP_7 and Home
    KP_8 = 0x60             # KP_8 and Up Arrow
    KP_9 = 0x61             # KP_9 and PageUp
    KP_0 = 0x62             # KP_0 and Insert
    KP_PERIOD = 0x63        # KP_. and Delete

    # -- additional keys -------------------------------------------------
    NONUS_BACKSLASH = 0x64   # Non-US \ and |
    APPLICATION = 0x65       # Menu / Compose
    POWER = 0x66
    KP_EQUAL = 0x67

    F13 = 0x68
    F14 = 0x69
    F15 = 0x6A
    F16 = 0x6B
    F17 = 0x6C
    F18 = 0x6D
    F19 = 0x6E
    F20 = 0x6F
    F21 = 0x70
    F22 = 0x71
    F23 = 0x72
    F24 = 0x73

    EXECUTE = 0x74
    HELP = 0x75
    MENU = 0x76
    SELECT = 0x77
    STOP = 0x78
    AGAIN = 0x79
    UNDO = 0x7A
    CUT = 0x7B
    COPY = 0x7C
    PASTE = 0x7D
    FIND = 0x7E

    MUTE = 0x7F
    VOLUME_UP = 0x80
    VOLUME_DOWN = 0x81

    LOCKING_CAPS_LOCK = 0x82
    LOCKING_NUM_LOCK = 0x83
    LOCKING_SCROLL_LOCK = 0x84

    KP_COMMA = 0x85
    KP_EQUAL_SIGN = 0x86

    # -- international ---------------------------------------------------
    INTERNATIONAL_1 = 0x87
    INTERNATIONAL_2 = 0x88
    INTERNATIONAL_3 = 0x89
    INTERNATIONAL_4 = 0x8A
    INTERNATIONAL_5 = 0x8B
    INTERNATIONAL_6 = 0x8C
    INTERNATIONAL_7 = 0x8D
    INTERNATIONAL_8 = 0x8E
    INTERNATIONAL_9 = 0x8F

    # -- language keys ---------------------------------------------------
    LANG_1 = 0x90
    LANG_2 = 0x91
    LANG_3 = 0x92
    LANG_4 = 0x93
    LANG_5 = 0x94
    LANG_6 = 0x95
    LANG_7 = 0x96
    LANG_8 = 0x97
    LANG_9 = 0x98

    ALT_ERASE = 0x99
    SYSREQ = 0x9A
    CANCEL = 0x9B
    CLEAR = 0x9C
    PRIOR = 0x9D
    RETURN_2 = 0x9E         # alternate return
    SEPARATOR = 0x9F
    OUT = 0xA0
    OPER = 0xA1
    CLEAR_AGAIN = 0xA2
    CRSEL = 0xA3
    EXSEL = 0xA4

    # -- more keypad -----------------------------------------------------
    KP_00 = 0xB0
    KP_000 = 0xB1
    THOUSANDS_SEP = 0xB2
    DECIMAL_SEP = 0xB3
    CURRENCY_UNIT = 0xB4
    CURRENCY_SUBUNIT = 0xB5
    KP_LPAREN = 0xB6
    KP_RPAREN = 0xB7
    KP_LEFT_BRACE = 0xB8
    KP_RIGHT_BRACE = 0xB9
    KP_TAB = 0xBA
    KP_BACKSPACE = 0xBB
    KP_A = 0xBC
    KP_B = 0xBD
    KP_C = 0xBE
    KP_D = 0xBF
    KP_E = 0xC0
    KP_F = 0xC1
    KP_XOR = 0xC2
    KP_CARET = 0xC3
    KP_PERCENT = 0xC4
    KP_LT = 0xC5
    KP_GT = 0xC6
    KP_AMPERSAND = 0xC7
    KP_DOUBLE_AMPERSAND = 0xC8
    KP_PIPE = 0xC9
    KP_DOUBLE_PIPE = 0xCA
    KP_COLON = 0xCB
    KP_HASH = 0xCC
    KP_SPACE = 0xCD
    KP_AT = 0xCE
    KP_EXCLAMATION = 0xCF
    KP_MEMORY_STORE = 0xD0
    KP_MEMORY_RECALL = 0xD1
    KP_MEMORY_CLEAR = 0xD2
    KP_MEMORY_ADD = 0xD3
    KP_MEMORY_SUBTRACT = 0xD4
    KP_MEMORY_MULTIPLY = 0xD5
    KP_MEMORY_DIVIDE = 0xD6
    KP_PLUS_MINUS = 0xD7
    KP_CLEAR = 0xD8
    KP_CLEAR_ENTRY = 0xD9
    KP_BINARY = 0xDA
    KP_OCTAL = 0xDB
    KP_DECIMAL = 0xDC
    KP_HEXADECIMAL = 0xDD

    # -- modifiers (DV — Dynamic Flags, go in modifier byte) -------------
    LEFT_CONTROL = 0xE0
    LEFT_SHIFT = 0xE1
    LEFT_ALT = 0xE2
    LEFT_GUI = 0xE3
    RIGHT_CONTROL = 0xE4
    RIGHT_SHIFT = 0xE5
    RIGHT_ALT = 0xE6
    RIGHT_GUI = 0xE7

    @property
    def is_modifier(self) -> bool:
        """True if this keycode maps to the modifier byte (0xE0–0xE7)."""
        return 0xE0 <= self <= 0xE7

    def modifier_bit(self) -> int | None:
        """Return the modifier-byte bitmask, or *None* for non-modifiers."""
        if not self.is_modifier:
            return None
        return 1 << (self - 0xE0)
