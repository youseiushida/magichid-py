"""DIP boundary: high-level HID classes depend on this, not on a concrete client."""

from __future__ import annotations

from typing import Protocol


class IHidClient(Protocol):
    """Abstract send capability — anything that can push a HID report frame.

    Matches ``core.io.blocking.BlockingClient.request()`` so BlockingClient
    satisfies this protocol without an adapter.  AsyncClient and test fakes
    can do the same.
    """

    def request(self, type_: int, payload: bytes, *, reliable: bool = True) -> None:
        """Send a request frame with the given msg-type and payload.

        *reliable* enables ACK/retransmit (required for RELATIVE reports).
        """
        ...
