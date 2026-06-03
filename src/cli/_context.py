"""Agent-context -- structured introspection for agents (Principle 7)."""

from __future__ import annotations

import argparse
import json
import sys

# Schema version -- bump on breaking shape changes
SCHEMA_VERSION = 1


COMMANDS = {
    "mouse": {
        "description": "Boot-mouse (5-byte relative report)",
        "actions": {
            "move": {
                "flags": {
                    "--x": {"type": "int", "range": [-127, 127], "default": 0},
                    "--y": {"type": "int", "range": [-127, 127], "default": 0},
                },
                "description": "Send relative X/Y movement deltas",
            },
            "scroll": {
                "flags": {
                    "--wheel": {"type": "int", "range": [-127, 127], "default": 0},
                    "--pan": {"type": "int", "range": [-127, 127], "default": 0},
                },
                "description": "Send vertical/horizontal scroll deltas",
            },
            "click": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["left", "right", "middle", "back", "forward"],
                        "required": True,
                    },
                },
                "description": "Press and release a button",
            },
            "press": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["left", "right", "middle", "back", "forward"],
                        "required": True,
                    },
                },
                "description": "Press (hold) a button until release/release-all",
            },
            "release": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["left", "right", "middle", "back", "forward"],
                        "required": True,
                    },
                },
                "description": "Release a held button",
            },
            "release-all": {
                "flags": {},
                "description": "Release all held buttons",
            },
        },
    },
    "keyboard": {
        "description": "Boot-keyboard with 6KRO keycode management",
        "actions": {
            "press": {
                "flags": {
                    "--key": {"type": "keycode", "repeatable": True, "required": True},
                },
                "description": "Press (hold) one or more keys. Modifiers go to modifier byte.",
            },
            "release": {
                "flags": {
                    "--key": {"type": "keycode", "repeatable": True, "required": True},
                },
                "description": "Release one or more keys",
            },
            "tap": {
                "flags": {
                    "--key": {"type": "keycode", "repeatable": True, "required": True},
                },
                "description": "Press and immediately release a key",
            },
            "type": {
                "flags": {
                    "--text": {"type": "string", "required": True},
                },
                "description": "Type an ASCII text string via sequential keystrokes",
            },
            "release-all": {
                "flags": {},
                "description": "Release all held keys",
            },
        },
    },
    "digitizer": {
        "description": "Absolute-position touch screen digitizer",
        "actions": {
            "down": {
                "flags": {
                    "--x": {"type": "float", "range": [0.0, 1.0], "required": True},
                    "--y": {"type": "float", "range": [0.0, 1.0], "required": True},
                    "--pressure": {"type": "float", "range": [0.0, 1.0], "default": 0.5},
                    "--contact-id": {"type": "int", "range": [0, 255], "default": 0},
                },
                "description": "Touch down at a fractional position",
            },
            "move": {
                "flags": {
                    "--x": {"type": "float", "range": [0.0, 1.0], "required": True},
                    "--y": {"type": "float", "range": [0.0, 1.0], "required": True},
                    "--pressure": {"type": "float", "range": [0.0, 1.0], "default": None},
                },
                "description": "Move contact while touching",
            },
            "up": {
                "flags": {},
                "description": "Lift contact (touch up)",
            },
        },
    },
    "unicode": {
        "description": "Direct Unicode text input (UTF-16LE, 6 code units per report)",
        "actions": {
            "type": {
                "flags": {
                    "--text": {"type": "string", "required": True},
                },
                "description": "Send text as Unicode input reports. Surrogate pairs handled automatically.",
            },
        },
    },
    "soc": {
        "description": "ESP32-S3 firmware update via FEATURE report",
        "actions": {
            "firmware-chunk": {
                "flags": {
                    "--firmware-id": {"type": "int", "range": [0, 65535], "required": True},
                    "--offset": {"type": "int", "range": [0, 2147483647], "required": True},
                    "--payload-file": {"type": "path", "required": True,
                                       "description": "Path to a file (max 32 bytes)"},
                    "--is-last": {"type": "bool", "default": False},
                },
                "description": "Send one 32-byte firmware chunk. Repeat with incremental --offset.",
            },
        },
    },
    "horipad": {
        "description": "HORIPAD Nintendo Switch wired controller (profile 1)",
        "note": "Requires SET_IDENTITY(profile=1) + serial reconnect before use",
        "actions": {
            "press": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["y", "b", "a", "x", "l", "r", "zl", "zr",
                                   "minus", "plus", "l_stick", "r_stick", "home", "capture"],
                        "repeatable": True, "required": True,
                    },
                },
                "description": "Press (hold) one or more buttons",
            },
            "hold": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["y", "b", "a", "x", "l", "r", "zl", "zr",
                                   "minus", "plus", "l_stick", "r_stick", "home", "capture"],
                        "repeatable": True, "required": True,
                    },
                    "--duration-ms": {"type": "float", "range": [0, None], "default": 1000.0},
                    "--interval-ms": {"type": "float", "range": [0, None], "default": 100.0},
                },
                "description": "Hold one or more buttons for a duration, refreshing before the watchdog",
            },
            "release": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["y", "b", "a", "x", "l", "r", "zl", "zr",
                                   "minus", "plus", "l_stick", "r_stick", "home", "capture"],
                        "repeatable": True, "required": True,
                    },
                },
                "description": "Release one or more buttons",
            },
            "tap": {
                "flags": {
                    "--button": {
                        "type": "enum",
                        "values": ["y", "b", "a", "x", "l", "r", "zl", "zr",
                                   "minus", "plus", "l_stick", "r_stick", "home", "capture"],
                        "repeatable": True, "required": True,
                    },
                },
                "description": "Press and immediately release a button",
            },
            "dpad": {
                "flags": {
                    "--direction": {
                        "type": "enum",
                        "values": ["up", "up_right", "right", "down_right",
                                   "down", "down_left", "left", "up_left", "center"],
                        "required": True,
                    },
                },
                "description": "Set D-pad direction. CENTER = neutral (0x0F).",
            },
            "stick-left": {
                "flags": {
                    "--x": {"type": "float", "range": [-1.0, 1.0], "default": 0.0},
                    "--y": {"type": "float", "range": [-1.0, 1.0], "default": 0.0},
                    "--raw": {"type": "bool", "default": False,
                              "description": "Treat x/y as raw 0x00-0xFF"},
                },
                "description": "Set left analog stick position. Centre is 0.0.",
            },
            "stick-right": {
                "flags": {
                    "--x": {"type": "float", "range": [-1.0, 1.0], "default": 0.0},
                    "--y": {"type": "float", "range": [-1.0, 1.0], "default": 0.0},
                    "--raw": {"type": "bool", "default": False,
                              "description": "Treat x/y as raw 0x00-0xFF"},
                },
                "description": "Set right analog stick position.",
            },
            "release-all": {
                "flags": {},
                "description": "Release all buttons, centre sticks and dpad",
            },
        },
    },
    "identity": {
        "description": "Persist USB identity/profile and reboot the device",
        "actions": {
            "set": {
                "flags": {
                    "--profile": {
                        "type": "enum",
                        "values": ["universal", "horipad"],
                        "required": True,
                    },
                    "--vid": {"type": "u16", "default": 0},
                    "--pid": {"type": "u16", "default": 0},
                    "--bcd": {"type": "u16", "default": 0},
                },
                "description": "Send SET_IDENTITY. 0 VID/PID/bcd keeps the profile default.",
            },
        },
    },
}


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("agent-context",
                        help="Emit structured CLI schema for agents (Principle 7)")
    p.add_argument("--scope", choices=list(COMMANDS) + ["all"], dest="scope",
                   default="all", help="Scope to one device or all (default: all)")


def run(args: argparse.Namespace) -> None:
    if args.scope == "all":
        data = {
            "schema_version": SCHEMA_VERSION,
            "description": "MagicHID CLI -- USB-HID bridge agent-native controller",
            "global_flags": {
                "--port": {"type": "string", "required": True,
                           "description": "Serial port (e.g. COM3, /dev/ttyUSB0)"},
                "--baudrate": {"type": "int", "default": 1000000},
                "--handshake-timeout": {"type": "float", "default": 5.0},
                "--json": {"type": "bool", "default": False,
                           "description": "Emit JSON to stdout"},
            },
            "commands": COMMANDS,
        }
    else:
        data = {
            "schema_version": SCHEMA_VERSION,
            "command": args.scope,
            "spec": COMMANDS[args.scope],
        }
    print(json.dumps(data, indent=2))
