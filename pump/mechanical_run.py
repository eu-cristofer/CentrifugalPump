"""
mechanical_run
==============

Mechanical running test (UC-11): a time log of measured channels (vibration,
temperatures, pressures, process values), checked against acceptance criteria
and plotted for the report.

Elapsed time is measured from the first reading and is monotone: the clock
labels ("HH:MM") may wrap past midnight.  Readings are kept in the order given.

Checks per channel
------------------
* an upper limit per *role* (for example vibration velocity), compared with the
  channel maximum;
* an optional *stabilisation* rule per role: over the last ``window`` of
  elapsed time the change (max - min) must not exceed an allowed change.

A check that has no configured criterion is reported as ``"info"`` (never as
pass or fail).  The overall result passes when no check fails;
:attr:`MechanicalRunResult.fully_assessed` is False while an expected check
(duration, or any vibration / bearing-temperature / oil-temperature channel) is
only ``"info"``.

Temperature differences are computed on absolute temperatures converted to
kelvin and expressed as delta quantities (``delta_degC`` / ``delta_degF``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Mapping, Optional

import numpy as np
from pint.errors import DimensionalityError

from .utilities.unit_conversion import Q_

__all__ = [
    "ROLES",
    "Channel",
    "RunReading",
    "MechanicalRunLog",
    "MechanicalRunCriteria",
    "ChannelResult",
    "MechanicalRunResult",
    "MechanicalRunChecker",
    "plot_mechanical_run",
]

ROLES = (
    "vibration_filtered",
    "vibration_unfiltered",
    "bearing_temperature",
    "oil_temperature",
    "oil_pressure",
    "seal_pressure",
    "flow",
    "differential_pressure",
    "power",
    "other",
)

# Roles whose check is expected for a complete assessment.
_ASSESSED_ROLES = (
    "vibration_filtered",
    "vibration_unfiltered",
    "bearing_temperature",
    "oil_temperature",
)

_RTOL = 1e-9


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
def _parse_time(text) -> float:
    """``"HH:MM"`` / ``"HH:MM:SS"`` -> minutes since midnight."""
    parts = str(text).strip().split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid time {text!r}; expected HH:MM")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid time {text!r}; expected HH:MM") from None
    seconds = nums[2] if len(nums) == 3 else 0.0
    return nums[0] * 60.0 + nums[1] + seconds / 60.0


@dataclass(frozen=True)
class Channel:
    """A measured channel: display ``name`` and its ``role`` (see ``ROLES``)."""

    name: str
    role: str


@dataclass(frozen=True)
class RunReading:
    """One log line: clock ``time`` ("HH:MM") and ``{channel name: Q_}`` values.

    A channel may be missing from ``values``.
    """

    time: str
    values: Mapping[str, Q_]


@dataclass(frozen=True)
class MechanicalRunLog:
    """Channels plus time-ordered readings of a mechanical running test."""

    channels: tuple
    readings: tuple

    def __post_init__(self):
        object.__setattr__(self, "channels", tuple(self.channels))
        object.__setattr__(self, "readings", tuple(self.readings))
        names = [c.name for c in self.channels]
        if len(set(names)) != len(names):
            raise ValueError(f"Duplicate channel names: {names}")
        elapsed = []
        acc = 0.0
        prev = None
        for reading in self.readings:
            t = _parse_time(reading.time)
            if prev is not None:
                acc += (t - prev) % 1440.0  # midnight wrap
            elapsed.append(acc)
            prev = t
        object.__setattr__(self, "_elapsed_min", tuple(elapsed))

    def elapsed(self) -> tuple:
        """Elapsed time of each reading, in minutes, from the first reading."""
        return tuple(Q_(e, "min") for e in self._elapsed_min)

    @property
    def duration(self) -> Q_:
        """Elapsed time between the first and the last reading."""
        return Q_(self._elapsed_min[-1] if self._elapsed_min else 0.0, "min")

    def series(self, name: str) -> tuple:
        """``(elapsed Q_ array [min], values Q_ array)`` of the readings that
        have a value for channel ``name``; values use the first value's unit."""
        pairs = [
            (e, r.values[name])
            for e, r in zip(self._elapsed_min, self.readings)
            if r.values.get(name) is not None
        ]
        if not pairs:
            return Q_(np.array([]), "min"), Q_(np.array([]), "dimensionless")
        unit = pairs[0][1].units
        x = np.array([p[0] for p in pairs], dtype=float)
        y = np.array([p[1].to(unit).magnitude for p in pairs], dtype=float)
        return Q_(x, "min"), Q_(y, unit)


# --------------------------------------------------------------------------- #
# Criteria
# --------------------------------------------------------------------------- #
def _parse_quantity(text) -> Q_:
    number, unit = str(text).split(None, 1)
    return Q_(float(number), unit.strip())


@dataclass(frozen=True)
class MechanicalRunCriteria:
    """
    Acceptance criteria of a mechanical running test.

    Attributes
    ----------
    min_duration : Q_ or None
        Minimum run duration; ``None`` means not configured.
    role_max : mapping role -> Q_
        Upper limit of the channel maximum, per role.
    stabilisation : mapping role -> (max change, window)
        e.g. ``(Q_(2, "delta_degF"), Q_(60, "min"))``; empty by default.
    source, verified : provenance of the numbers.
    """

    min_duration: Optional[Q_] = None
    role_max: Mapping[str, Q_] = field(default_factory=dict)
    stabilisation: Mapping[str, tuple] = field(default_factory=dict)
    source: str = ""
    verified: bool = False

    @classmethod
    def from_table(cls, table: Mapping) -> "MechanicalRunCriteria":
        """Build from a TOML ``mechanical_run`` table."""
        table = table or {}
        min_duration = table.get("min_duration")
        role_max = {}
        for entry in table.get("roles", ()):
            if "max" in entry:
                role_max[entry["role"]] = _parse_quantity(entry["max"])
        stabilisation = {}
        for entry in table.get("stabilisation", ()):
            stabilisation[entry["role"]] = (
                _parse_quantity(entry["delta"]),
                _parse_quantity(entry["window"]),
            )
        return cls(
            min_duration=_parse_quantity(min_duration) if min_duration else None,
            role_max=role_max,
            stabilisation=stabilisation,
            source=str(table.get("source", "")),
            verified=bool(table.get("verified", False)),
        )


# --------------------------------------------------------------------------- #
# Checker
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ChannelResult:
    """Statistics and verdict of one channel (values in the channel's unit).

    ``stabilisation`` is ``None`` when not configured for the role, else a dict
    ``{"change", "allowed", "window", "ok"}`` (``ok`` is None if it could not
    be evaluated).  ``status`` is ``"pass"``, ``"fail"`` or ``"info"``.
    """

    name: str
    role: str
    unit: str
    min: Optional[Q_]
    max: Optional[Q_]
    last: Optional[Q_]
    limit: Optional[Q_]
    stabilisation: Optional[dict]
    status: str


@dataclass(frozen=True)
class MechanicalRunResult:
    """Overall result of the mechanical running test."""

    duration: Q_
    min_duration: Optional[Q_]
    duration_status: str
    channels: tuple
    passed: bool
    fully_assessed: bool
    source: str = ""
    verified: bool = False

    @property
    def verdict(self) -> str:
        """``PASSED`` / ``FAILED`` / ``PASSED (not fully assessed)``."""
        if not self.passed:
            return "FAILED"
        return "PASSED" if self.fully_assessed else "PASSED (not fully assessed)"


class MechanicalRunChecker:
    """Check a :class:`MechanicalRunLog` against :class:`MechanicalRunCriteria`."""

    def __init__(
        self, log: MechanicalRunLog, criteria: Optional[MechanicalRunCriteria] = None
    ):
        self.log = log
        self.criteria = criteria if criteria is not None else MechanicalRunCriteria()

    @property
    def result(self) -> MechanicalRunResult:
        return self.check()

    def check(self) -> MechanicalRunResult:
        crit = self.criteria
        duration = self.log.duration
        if crit.min_duration is None:
            duration_status = "info"
        else:
            need = crit.min_duration.to("min").magnitude
            ok = duration.to("min").magnitude >= need - _RTOL * abs(need)
            duration_status = "pass" if ok else "fail"

        channels = tuple(self._check_channel(c) for c in self.log.channels)
        passed = duration_status != "fail" and all(c.status != "fail" for c in channels)
        fully = duration_status != "info" and all(
            c.status != "info" for c in channels if c.role in _ASSESSED_ROLES
        )
        return MechanicalRunResult(
            duration=duration,
            min_duration=crit.min_duration,
            duration_status=duration_status,
            channels=channels,
            passed=passed,
            fully_assessed=fully,
            source=crit.source,
            verified=crit.verified,
        )

    # ------------------------------------------------------------------
    def _check_channel(self, channel: Channel) -> ChannelResult:
        crit = self.criteria
        x, y = self.log.series(channel.name)
        if len(y) == 0:
            return ChannelResult(
                channel.name,
                channel.role,
                "",
                None,
                None,
                None,
                crit.role_max.get(channel.role),
                None,
                "info",
            )
        unit = y.units
        unit_str = f"{unit:~P}"
        vmin = Q_(float(np.min(y.magnitude)), unit)
        vmax = Q_(float(np.max(y.magnitude)), unit)
        vlast = Q_(float(y.magnitude[-1]), unit)

        statuses = []
        limit = crit.role_max.get(channel.role)
        if limit is not None:
            try:
                limit = limit.to(unit)
            except DimensionalityError:
                limit = None
        if limit is not None:
            lim = limit.magnitude
            statuses.append(vmax.magnitude <= lim + _RTOL * abs(lim))

        stab = None
        if channel.role in crit.stabilisation:
            allowed, window = crit.stabilisation[channel.role]
            stab = {"change": None, "allowed": allowed, "window": window, "ok": None}
            try:
                change = self._window_change(x, y, unit, allowed, window)
            except Exception:
                change = None
            if change is not None:
                stab["change"] = change
                a = allowed.magnitude
                stab["ok"] = bool(change.magnitude <= a + _RTOL * abs(a))
                statuses.append(stab["ok"])

        if any(s is False for s in statuses):
            status = "fail"
        elif statuses:
            status = "pass"
        else:
            status = "info"
        return ChannelResult(
            channel.name, channel.role, unit_str, vmin, vmax, vlast, limit, stab, status
        )

    @staticmethod
    def _window_change(x, y, unit, allowed, window):
        """max - min of ``y`` over the last ``window`` of the *run* (None if < 2 points)."""
        end = x.to("min").magnitude[-1]
        start = end - window.to("min").magnitude - _RTOL
        mask = x.to("min").magnitude >= start
        vals = y.magnitude[mask]
        if len(vals) < 2:
            return None
        if Q_(1, unit).dimensionality == Q_(1, "K").dimensionality:
            kelvin = Q_(vals, unit).to("K").magnitude  # offset units -> K first
            return Q_(float(kelvin.max() - kelvin.min()), "K").to(allowed.units)
        return Q_(float(vals.max() - vals.min()), unit).to(allowed.units)


# --------------------------------------------------------------------------- #
# Plot
# --------------------------------------------------------------------------- #
_GROUPS = (
    ("Vibration", ("vibration_filtered", "vibration_unfiltered")),
    ("Temperature", ("bearing_temperature", "oil_temperature")),
    ("Pressure", ("oil_pressure", "seal_pressure", "differential_pressure")),
    ("Process", ("flow", "power", "other")),
)


def plot_mechanical_run(
    log: MechanicalRunLog, criteria: Optional[MechanicalRunCriteria] = None
) -> BytesIO:
    """Trend plot as a PNG ``BytesIO``: one subplot per role group present,
    role limits as dashed lines, x axis = elapsed minutes."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    groups = []
    for title, roles in _GROUPS:
        chans = [
            c for c in log.channels if c.role in roles and len(log.series(c.name)[0])
        ]
        if chans:
            groups.append((title, chans))
    n = max(1, len(groups))
    fig = Figure(figsize=(8, 2.6 * n + 0.6))
    FigureCanvasAgg(fig)
    axes = fig.subplots(n, 1, sharex=True, squeeze=False)[:, 0]

    if not groups:
        axes[0].text(
            0.5, 0.5, "No data", ha="center", va="center", transform=axes[0].transAxes
        )
    for ax, (title, chans) in zip(axes, groups):
        units = set()
        for ch in chans:
            x, y = log.series(ch.name)
            unit = f"{y.units:~P}"
            units.add(unit)
            (line,) = ax.plot(
                x.to("min").magnitude,
                y.magnitude,
                marker="o",
                ms=3,
                label=f"{ch.name} [{unit}]",
            )
            limit = criteria.role_max.get(ch.role) if criteria else None
            if limit is not None:
                try:
                    ax.axhline(
                        limit.to(y.units).magnitude,
                        ls="--",
                        lw=1,
                        color=line.get_color(),
                    )
                except DimensionalityError:
                    pass
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_ylabel(units.pop() if len(units) == 1 else "")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, loc="best")
    axes[-1].set_xlabel("Elapsed time [min]")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    return buf
