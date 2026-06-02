"""I/O edges that drive the sans-I/O core over real transports.

* :class:`BlockingClient` — single-threaded, caller-driven, no background threads.
* An asyncio edge (~40 lines) can be added later against the same :class:`Connection`.
"""

from __future__ import annotations

from .blocking import BlockingClient, BlockingError, CommandTimeout, ProtocolVersionError

__all__ = ["BlockingClient", "BlockingError", "CommandTimeout", "ProtocolVersionError"]
