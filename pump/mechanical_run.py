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
  elapsed time the change (max - min) must not exceed an allowed change,
  optionally of the rise above the ambient temperature, and optionally only
  for information (an "if specified" definition, see :class:`Stabilisation`).

Temperature rules (API 610 8th 2.9.2.3, 11th 6.10.2.4, 12th 6.10.2.7 and
client overlays) depend on the bearing lubrication system of the log
(:data:`LUBRICATION`) and are evaluated across channels: the oil temperature
rise through the bearings (outlet - inlet), the sump or housing rise above the
ambient temperature, and the bearing metal / housing temperatures
(:class:`TemperatureRules`, :class:`RuleResult`).

A check that has no configured criterion is reported as ``"info"`` (never as
pass or fail).  A required check that cannot be computed (a missing channel)
is ``"not evaluated"``.  The overall result passes when no check fails;
:attr:`MechanicalRunResult.fully_assessed` is False while an expected check
(duration, any vibration channel, a temperature rule) is only ``"info"`` or
``"not evaluated"``.

Temperature differences are computed on absolute temperatures converted to
kelvin and expressed as delta quantities (``delta_degC`` / ``delta_degF``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Mapping, Optional

import numpy as np
from pint.errors import DimensionalityError

from .utilities.unit_conversion import Q_

__all__ = [
    "ROLES",
    "LUBRICATION",
    "LUBRICATION_LABELS",
    "Stabilisation",
    "TemperatureRules",
    "RuleResult",
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
    "oil_temperature",  # oil sump (ring-oil / splash systems)
    "oil_inlet_temperature",  # pressurized systems: oil supply to the bearings
    "oil_outlet_temperature",  # pressurized systems: oil drain of one bearing
    "housing_temperature",  # bearing-housing surface (oil mist, grease)
    "ambient_temperature",  # test-cell ambient, for the rise rules
    "oil_pressure",
    "seal_pressure",
    "flow",
    "differential_pressure",
    "power",
    "other",
)

# Roles whose channel check is expected for a complete assessment.  The
# temperatures are assessed by the temperature rules instead (when the criteria
# define rules for the log's lubrication system).
_ASSESSED_ROLES = (
    "vibration_filtered",
    "vibration_unfiltered",
)
# Legacy: without temperature rules, a bearing / sump channel with no limit
# still makes the assessment incomplete (as before the rules existed).
_LEGACY_TEMPERATURE_ROLES = ("bearing_temperature", "oil_temperature")

#: Bearing lubrication systems (API 610 12th 6.10.2.7 a-c; grease 9.1.2.7).
LUBRICATION = ("ring_oil", "pressurized", "oil_mist", "grease")
LUBRICATION_LABELS = {
    "ring_oil": "Ring-oil / splash",
    "pressurized": "Pressurized (forced-feed)",
    "oil_mist": "Pure oil mist",
    "grease": "Grease",
}

PASS, FAIL, INFO, NOT_EVALUATED = "pass", "fail", "info", "not evaluated"

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
    """A measured channel: display ``name``, its ``role`` (see ``ROLES``) and
    an optional bearing ``location`` ("DE", "NDE", ...) that pairs an oil
    outlet with the oil inlet of the same bearing."""

    name: str
    role: str
    location: str = ""


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
    lubrication: Optional[str] = None  # one of LUBRICATION, None = not stated
    # Elapsed minutes per reading, computed in __post_init__ (not an input).
    _elapsed_min: tuple = field(init=False, repr=False, compare=False, default=())

    def __post_init__(self):
        object.__setattr__(self, "channels", tuple(self.channels))
        object.__setattr__(self, "readings", tuple(self.readings))
        names = [c.name for c in self.channels]
        if len(set(names)) != len(names):
            raise ValueError(f"Duplicate channel names: {names}")
        if self.lubrication is not None and self.lubrication not in LUBRICATION:
            raise ValueError(
                f"Unknown lubrication {self.lubrication!r}; one of {LUBRICATION}"
            )
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


def _opt_quantity(table: Mapping, key: str) -> Optional[Q_]:
    v = table.get(key)
    return _parse_quantity(v) if v is not None else None


@dataclass(frozen=True)
class Stabilisation:
    """Temperature-stabilisation rule of one channel role.

    Over the last ``window`` of the run the change (max - min) must not exceed
    ``delta``.  ``relative_to_ambient`` judges the rise above the ambient
    channel instead of the temperature itself (API 610 12th 8.3.4.2.1).
    ``warmup`` is the time to wait before the window may start (N-553 rev E
    9.20 NOTE 1).  ``required`` False keeps the result for information: the
    edition defines stabilisation, but runs to it only "if specified".
    """

    delta: Q_
    window: Q_
    relative_to_ambient: bool = False
    required: bool = True
    warmup: Optional[Q_] = None

    @classmethod
    def coerce(cls, spec) -> "Stabilisation":
        """A :class:`Stabilisation` from itself, ``(delta, window)`` or a dict."""
        if isinstance(spec, cls):
            return spec
        if isinstance(spec, Mapping):
            return cls(
                delta=spec["delta"],
                window=spec["window"],
                relative_to_ambient=bool(spec.get("relative_to_ambient", False)),
                required=bool(spec.get("required", True)),
                warmup=spec.get("warmup"),
            )
        delta, window = spec[0], spec[1]
        return cls(delta=delta, window=window)


@dataclass(frozen=True)
class TemperatureRules:
    """Bearing temperature limits of one lubrication system (shop test).

    Rises are temperature *differences* (``delta_degC``); the other limits are
    temperatures.  ``*_design_max`` are design limits at 43 degC ambient
    (8th 2.9.2.3, 11th 6.10.2.4): reported for information, not judged in the
    shop test.  ``None`` means the edition sets no such limit.
    """

    oil_rise_max: Optional[Q_] = None  # oil outlet - oil inlet (pressurized)
    sump_rise_max: Optional[Q_] = None  # oil sump - ambient (ring-oil / splash)
    housing_rise_max: Optional[Q_] = None  # housing - ambient (oil mist, grease)
    bearing_metal_max: Optional[Q_] = None  # if sensors are supplied
    housing_max: Optional[Q_] = None  # housing surface (pure oil mist)
    oil_outlet_design_max: Optional[Q_] = None
    sump_design_max: Optional[Q_] = None
    housing_design_max: Optional[Q_] = None
    source: str = ""

    _KEYS = (
        "oil_rise_max",
        "sump_rise_max",
        "housing_rise_max",
        "bearing_metal_max",
        "housing_max",
        "oil_outlet_design_max",
        "sump_design_max",
        "housing_design_max",
    )

    @classmethod
    def from_table(cls, table: Mapping) -> "TemperatureRules":
        return cls(
            **{k: _opt_quantity(table, k) for k in cls._KEYS},
            source=str(table.get("source", "")),
        )


@dataclass(frozen=True)
class RuleResult:
    """One temperature rule: the worst ``value`` against ``limit``.

    ``status`` is ``"pass"``, ``"fail"``, ``"info"`` (reported, not judged) or
    ``"not evaluated"`` (required, but a channel is missing).
    """

    key: str
    name: str
    value: Optional[Q_]
    limit: Optional[Q_]
    status: str
    note: str = ""

    @property
    def unit(self) -> str:
        q = self.limit if self.limit is not None else self.value
        return "" if q is None else f"{q.units:~P}"


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
    stabilisation : mapping role -> Stabilisation
        A :class:`Stabilisation`, or ``(max change, window)`` such as
        ``(Q_(2, "delta_degF"), Q_(60, "min"))``; empty by default.
    temperature : mapping lubrication -> TemperatureRules
        Bearing temperature limits per lubrication system; empty by default.
    source : str
        Provenance of the numbers (clause references).
    verified : bool
        True only when the limits were checked against the standard text.
    """

    min_duration: Optional[Q_] = None
    role_max: Mapping[str, Q_] = field(default_factory=dict)
    stabilisation: Mapping[str, Any] = field(default_factory=dict)
    source: str = ""
    verified: bool = False
    temperature: Mapping[str, TemperatureRules] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(
            self,
            "stabilisation",
            {r: Stabilisation.coerce(v) for r, v in dict(self.stabilisation).items()},
        )

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
            stabilisation[entry["role"]] = Stabilisation(
                delta=_parse_quantity(entry["delta"]),
                window=_parse_quantity(entry["window"]),
                relative_to_ambient=bool(entry.get("relative_to_ambient", False)),
                required=bool(entry.get("required", True)),
                warmup=_opt_quantity(entry, "warmup"),
            )
        temperature = {
            lube: TemperatureRules.from_table(t)
            for lube, t in (table.get("temperature") or {}).items()
            if lube in LUBRICATION
        }
        return cls(
            min_duration=_parse_quantity(min_duration) if min_duration else None,
            role_max=role_max,
            stabilisation=stabilisation,
            source=str(table.get("source", "")),
            verified=bool(table.get("verified", False)),
            temperature=temperature,
        )


# --------------------------------------------------------------------------- #
# Checker
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ChannelResult:
    """Statistics and verdict of one channel (values in the channel's unit).

    ``stabilisation`` is ``None`` when not configured for the role, else a dict
    ``{"change", "allowed", "window", "ok", "required", "relative_to_ambient"}``
    (``ok`` is None if it could not be evaluated).  ``status`` is ``"pass"``,
    ``"fail"``, ``"info"`` or ``"not evaluated"`` (a required stabilisation that
    could not be computed).
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
    rules: tuple = ()  # RuleResult per temperature rule
    lubrication: Optional[str] = None

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
        rules = self._temperature_rules()
        passed = (
            duration_status != FAIL
            and all(c.status != FAIL for c in channels)
            and all(r.status != FAIL for r in rules)
        )
        assessed = _ASSESSED_ROLES + (
            () if crit.temperature else _LEGACY_TEMPERATURE_ROLES
        )
        fully = (
            duration_status != INFO
            and all(
                c.status not in (INFO, NOT_EVALUATED)
                for c in channels
                if c.role in assessed
            )
            and all(c.status != NOT_EVALUATED for c in channels)
            and all(r.status != NOT_EVALUATED for r in rules)
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
            rules=rules,
            lubrication=self.log.lubrication,
        )

    # ------------------------------------------------------------------
    def _role_channels(self, *roles) -> list:
        return [c for c in self.log.channels if c.role in roles]

    def _kelvin_by_reading(self, name: str) -> list:
        """Per reading: the channel value in kelvin, or None when missing."""
        out = []
        for r in self.log.readings:
            v = r.values.get(name)
            try:
                out.append(None if v is None else float(v.to("K").magnitude))
            except DimensionalityError:
                out.append(None)
        return out

    def _max_abs(self, chans) -> Optional[Q_]:
        """Highest reading of temperature channels ``chans`` (degC), None if none."""
        vals = [
            v for c in chans for v in self._kelvin_by_reading(c.name) if v is not None
        ]
        if not vals:
            return None
        return Q_(max(vals), "K").to("degC")

    def _max_rise(self, hot_chans, cold_for) -> Optional[Q_]:
        """Highest per-reading difference hot - cold (delta_degC), None if no pair."""
        rises = []
        for hot in hot_chans:
            cold = cold_for(hot)
            if cold is None:
                continue
            for h, c in zip(
                self._kelvin_by_reading(hot.name), self._kelvin_by_reading(cold.name)
            ):
                if h is not None and c is not None:
                    rises.append(h - c)
        if not rises:
            return None
        return Q_(max(rises), "delta_degC")

    @staticmethod
    def _judge(key, name, value, limit, missing_note) -> RuleResult:
        if value is None:
            return RuleResult(key, name, None, limit, NOT_EVALUATED, missing_note)
        lim = limit.to(value.units).magnitude
        ok = value.magnitude <= lim + _RTOL * abs(lim)
        return RuleResult(key, name, value, limit, PASS if ok else FAIL)

    def _temperature_rules(self) -> tuple:
        """The bearing temperature rules of the log's lubrication system."""
        temperature = self.criteria.temperature
        if not temperature:
            return ()
        lube = self.log.lubrication
        if lube is None:
            return (
                RuleResult(
                    "lubrication",
                    "Bearing temperature rules",
                    None,
                    None,
                    NOT_EVALUATED,
                    "lubrication system not stated in the MRT Log",
                ),
            )
        rules = temperature.get(lube)
        label = LUBRICATION_LABELS[lube]
        if rules is None:
            return (
                RuleResult(
                    "lubrication",
                    "Bearing temperature rules",
                    None,
                    None,
                    INFO,
                    f"the criteria set no limits for {label.lower()} lubrication",
                ),
            )
        ambient = (self._role_channels("ambient_temperature") or [None])[0]
        inlets = self._role_channels("oil_inlet_temperature")

        def inlet_for(outlet):
            same = [c for c in inlets if c.location and c.location == outlet.location]
            return (same or inlets or [None])[0]

        def to_ambient(_chan):
            return ambient

        out = []
        if rules.oil_rise_max is not None:
            outlets = self._role_channels("oil_outlet_temperature")
            out.append(
                self._judge(
                    "oil_rise_max",
                    "Oil temperature rise (outlet − inlet)",
                    self._max_rise(outlets, inlet_for),
                    rules.oil_rise_max,
                    "needs oil inlet and oil outlet temperature channels",
                )
            )
        if rules.sump_rise_max is not None:
            sumps = self._role_channels("oil_temperature")
            out.append(
                self._judge(
                    "sump_rise_max",
                    "Oil sump rise above ambient",
                    self._max_rise(sumps, to_ambient),
                    rules.sump_rise_max,
                    "needs oil sump and ambient temperature channels",
                )
            )
        housings = self._role_channels("housing_temperature")
        if rules.housing_rise_max is not None:
            out.append(
                self._judge(
                    "housing_rise_max",
                    "Bearing-housing rise above ambient",
                    self._max_rise(housings, to_ambient),
                    rules.housing_rise_max,
                    "needs bearing-housing and ambient temperature channels",
                )
            )
        if rules.housing_max is not None:
            out.append(
                self._judge(
                    "housing_max",
                    "Bearing-housing temperature",
                    self._max_abs(housings),
                    rules.housing_max,
                    "needs bearing-housing temperature channels",
                )
            )
        if rules.bearing_metal_max is not None:
            metal = self._max_abs(self._role_channels("bearing_temperature"))
            if metal is None:
                out.append(
                    RuleResult(
                        "bearing_metal_max",
                        "Bearing metal temperature",
                        None,
                        rules.bearing_metal_max,
                        INFO,
                        "no bearing temperature sensors in the log "
                        "(the limit applies if sensors are supplied)",
                    )
                )
            else:
                out.append(
                    self._judge(
                        "bearing_metal_max",
                        "Bearing metal temperature",
                        metal,
                        rules.bearing_metal_max,
                        "",
                    )
                )
        for key, name, roles in (
            (
                "oil_outlet_design_max",
                "Oil outlet temperature",
                ("oil_outlet_temperature",),
            ),
            ("sump_design_max", "Oil sump temperature", ("oil_temperature",)),
            (
                "housing_design_max",
                "Bearing-housing temperature",
                ("housing_temperature",),
            ),
        ):
            limit = getattr(rules, key)
            value = self._max_abs(self._role_channels(*roles))
            if limit is not None and value is not None:
                out.append(
                    RuleResult(
                        key,
                        name,
                        value,
                        limit,
                        INFO,
                        "design limit at 43 °C ambient, not judged in the shop test",
                    )
                )
        return tuple(out)

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
        unevaluated = False
        if channel.role in crit.stabilisation:
            spec = Stabilisation.coerce(crit.stabilisation[channel.role])
            allowed, window = spec.delta, spec.window
            stab = {
                "change": None,
                "allowed": allowed,
                "window": window,
                "ok": None,
                "required": spec.required,
                "relative_to_ambient": spec.relative_to_ambient,
            }
            try:
                xs, ys = x, y
                if spec.relative_to_ambient:
                    xs, ys = self._rise_over_ambient(channel.name)
                change = self._window_change(
                    xs, ys, ys.units, allowed, window, spec.warmup
                )
            except Exception:
                change = None
            if change is not None:
                stab["change"] = change
                a = allowed.magnitude
                stab["ok"] = bool(change.magnitude <= a + _RTOL * abs(a))
                if spec.required:
                    statuses.append(stab["ok"])
            elif spec.required:
                unevaluated = True

        if any(s is False for s in statuses):
            status = FAIL
        elif unevaluated:
            status = NOT_EVALUATED
        elif statuses:
            status = PASS
        else:
            status = INFO
        return ChannelResult(
            channel.name, channel.role, unit_str, vmin, vmax, vlast, limit, stab, status
        )

    def _rise_over_ambient(self, name: str):
        """``(elapsed [min], rise [delta_degC])`` of channel ``name`` above the
        first ambient channel, on the readings that have both."""
        ambient = (self._role_channels("ambient_temperature") or [None])[0]
        if ambient is None:
            raise ValueError("no ambient temperature channel")
        xs, ys = [], []
        for e, h, c in zip(
            self.log._elapsed_min,
            self._kelvin_by_reading(name),
            self._kelvin_by_reading(ambient.name),
        ):
            if h is not None and c is not None:
                xs.append(e)
                ys.append(h - c)
        return Q_(np.array(xs, dtype=float), "min"), Q_(
            np.array(ys, dtype=float), "delta_degC"
        )

    @staticmethod
    def _window_change(x, y, unit, allowed, window, warmup=None):
        """max - min of ``y`` over the last ``window`` of the *run* (at least two
        readings; None if there are fewer, or if the window would start before
        the ``warmup``)."""
        if len(x) == 0:
            return None
        end = x.to("min").magnitude[-1]
        start = end - window.to("min").magnitude - _RTOL
        if warmup is not None and start < warmup.to("min").magnitude - 1e-6:
            return None
        xm = x.to("min").magnitude
        mask = xm >= start
        if mask.sum() < 2:
            # Readings sparser than the window (e.g. every 15 min against a
            # 10 min window): reach back to the last reading before it, so the
            # change is taken over at least the window (conservative).
            before = np.nonzero(~mask)[0]
            if len(before):
                mask[before[-1]] = True
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
    (
        "Temperature",
        (
            "bearing_temperature",
            "oil_temperature",
            "oil_inlet_temperature",
            "oil_outlet_temperature",
            "housing_temperature",
            "ambient_temperature",
        ),
    ),
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
