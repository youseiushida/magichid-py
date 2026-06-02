# MagicHID-py

Python client for the [MagicHID](https://github.com/youseiushida/magichid). 

## Install

```
pip install magichid
```

## Quickstart -- high-level API

```python
from core.io.blocking import BlockingClient
from core.reports import ReportTable
from hid import Keyboard, Keycode, Mouse, MouseButton, Digitizer

with BlockingClient("COM5") as c:
    c.handshake()

    # Keyboard
    kb = Keyboard(c, ReportTable.universal())
    kb.tap(Keycode.A)
    kb.type_text("Hello world")

    # Mouse
    mouse = Mouse(c, ReportTable.universal())
    mouse.move(x=10, y=-5)
    mouse.click(MouseButton.LEFT)

    # Touch digitizer
    dig = Digitizer(c, ReportTable.universal())
    dig.down(x=0.5, y=0.5)
    dig.move(x=0.6, y=0.5)
    dig.up()
```

35 device classes in `hid.universal`: keyboard, mouse, gamepad, flight sim, VR headset,
golf club, consumer control, digitizer, haptics, force feedback, unicode input, eye tracker,
accelerometer, medical ultrasound, braille display, lamp array, monitor, UPS, battery,
barcode scanner, scale, MSR, camera, arcade I/O, gaming device, FIDO authenticator, and more.

Horipad (Nintendo Switch, profile 1) in `hid.horipad`.

## Quickstart -- CLI

```
magichid --port COM5 keyboard type --text "Hello world"
magichid --port COM5 mouse move --x 10 --y -5 --json
magichid --port COM5 digitizer down --x 0.5 --y 0.5
magichid --port COM5 unicode type --text "Hello (U+1F389)"
magichid --port COM5 horipad press --button A --json
magichid --port COM5 soc firmware-chunk --firmware-id 1 --offset 0 --payload-file chunk.bin

# Agent introspection
magichid agent-context | jq .commands.mouse.actions
```

The CLI is non-interactive by default. `--json` emits structured stdout. Errors go to stderr
with enumerated valid values. `agent-context` provides a versioned machine-readable schema.
