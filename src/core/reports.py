"""Report table: sizes + relative/absolute flags for every report in a profile.

Data comes from ``spec/reports.json`` (bundled, multi-profile) or a live
``CAPS`` reply. The table answers two questions the core cannot:

* How many bytes does this report's INPUT expect?  (``in_len``)
* Does the INPUT contain a relative field?           (``relative`` → MUST use reliable mode)

HID field *layout* (which byte is a modifier, which is a keycode, …) is NOT
encoded here — it follows the HID descriptor / HUT for each report.
Convenience builders for common reports live in ``examples/``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from .wire import ReportFlag

if TYPE_CHECKING:
    from .events import CapsReceived

# Well-known report ids in the universal profile.
MOUSE = 1      # in_len 5: [buttons][x][y][wheel][pan] — RELATIVE
KEYBOARD = 7   # in_len 8: [modifier][reserved][k1..k6]


@lru_cache(maxsize=1)
def _bundled_data() -> dict:
    """Load the bundled ``reports.json`` once and cache it."""
    return json.loads(
        files("core").joinpath("reports.json").read_text(encoding="utf-8")
    )


@dataclass(frozen=True)
class ReportSpec:
    """One row of a profile's report table."""

    id: int
    in_len: int
    out_len: int
    feat_len: int
    flags: int
    name: str = ""

    @property
    def relative(self) -> bool:
        return bool(self.flags & ReportFlag.RELATIVE)

    @property
    def sendable(self) -> bool:
        return self.in_len > 0


class ReportTable:
    """Lookup of :class:`ReportSpec` by report id + payload padding."""

    def __init__(self, specs: list[ReportSpec]) -> None:
        self._by_id: dict[int, ReportSpec] = {s.id: s for s in specs}

    # -- constructors ------------------------------------------------------- #

    @classmethod
    def from_json(cls, path: str | Path, profile: str = "universal") -> "ReportTable":
        """Load from a ``reports.json``-format file on disk."""
        return cls.from_profile_data(
            json.loads(Path(path).read_text(encoding="utf-8")), profile,
        )

    @classmethod
    def from_profile_data(cls, data: dict, profile: str = "universal") -> "ReportTable":
        """Load from an already-parsed ``reports.json`` dict."""
        return cls([ReportSpec(
            id=r["id"],
            in_len=r["input_bytes"],
            out_len=r["output_bytes"],
            feat_len=r["feature_bytes"],
            flags=(ReportFlag.RELATIVE if r.get("relative") else 0),
            name=r.get("name", ""),
        ) for r in data["profiles"][profile]["reports"]])

    @classmethod
    def universal(cls) -> "ReportTable":
        """The bundled ``universal`` profile table (35 reports)."""
        return cls.from_profile_data(_bundled_data(), "universal")

    @classmethod
    def horipad(cls) -> "ReportTable":
        """The ``horipad`` profile: single ``[id=0, in_len=8, flags=0]`` entry."""
        return cls.from_profile_data(_bundled_data(), "horipad")

    @classmethod
    def from_caps(cls, caps: "CapsReceived") -> "ReportTable":
        """Build from a live ``CAPS`` reply."""
        return cls([ReportSpec(
            id=e.id, in_len=e.in_len, out_len=e.out_len,
            feat_len=e.feat_len, flags=e.flags,
        ) for e in caps.entries])

    # -- lookup ------------------------------------------------------------- #

    def __getitem__(self, rid: int) -> ReportSpec:
        return self._by_id[rid]

    def __contains__(self, rid: int) -> bool:
        return rid in self._by_id

    def __iter__(self):
        return iter(sorted(self._by_id.values(), key=lambda s: s.id))

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, rid: int) -> ReportSpec | None:
        return self._by_id.get(rid)

    def in_len(self, rid: int) -> int:
        return self._by_id[rid].in_len

    def pad_input(self, rid: int, data: bytes) -> bytes:
        """Zero-pad *data* up to the report's ``in_len``.

        Raises :class:`ValueError` if *data* exceeds ``in_len`` or the report
        has no INPUT (output/feature-only).
        """
        s = self._by_id[rid]
        if not s.sendable:
            raise ValueError(f"report {rid} ({s.name}) has no INPUT")
        if len(data) > s.in_len:
            raise ValueError(f"report {rid} data {len(data)} > in_len {s.in_len}")
        return bytes(data) + b"\x00" * (s.in_len - len(data))

    def pad_feature(self, rid: int, data: bytes) -> bytes:
        """Zero-pad *data* up to the report's ``feat_len``.

        Raises :class:`ValueError` if *data* exceeds ``feat_len`` or the report
        has no FEATURE.
        """
        s = self._by_id[rid]
        if s.feat_len == 0:
            raise ValueError(f"report {rid} ({s.name}) has no FEATURE")
        if len(data) > s.feat_len:
            raise ValueError(f"report {rid} data {len(data)} > feat_len {s.feat_len}")
        return bytes(data) + b"\x00" * (s.feat_len - len(data))
