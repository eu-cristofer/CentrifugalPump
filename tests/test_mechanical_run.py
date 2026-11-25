"""
Mechanical running test (UC-11) — Qt-free.

Synthetic logs for pass / fail / info paths, unit independence, midnight wrap,
and the P-9001A Vendor A record (17 readings over 4 h).
"""

from dataclasses import replace

import pytest

from pump import (
    AcceptanceCriteria,
    Channel,
    MechanicalRunChecker,
    MechanicalRunCriteria,
    MechanicalRunLog,
    Q_,
    RunReading,
    plot_mechanical_run,
)


def _log(cols, rows):
    """cols: [(name, role, unit)]; rows: [(time, v1, v2, ...)] (None = missing)."""
    channels = tuple(Channel(n, r) for n, r, _u in cols)
    readings = tuple(
        RunReading(
            row[0],
            {
                name: Q_(v, unit)
                for (name, _r, unit), v in zip(cols, row[1:])
                if v is not None
            },
        )
        for row in rows
    )
    return MechanicalRunLog(channels, readings)


def _crit(**kw):
    base = dict(
        min_duration=Q_(4, "h"),
        role_max={
            "vibration_filtered": Q_(2.0, "mm/s"),
            "vibration_unfiltered": Q_(3.0, "mm/s"),
        },
    )
    base.update(kw)
    return MechanicalRunCriteria(**base)


_VIB_COLS = [
    ("Vib f", "vibration_filtered", "mm/s"),
    ("Vib u", "vibration_unfiltered", "mm/s"),
]
_HOURLY = ["00:00", "01:00", "02:00", "03:00", "04:00"]


def _vib_log(filtered=1.0, unfiltered=2.0, times=_HOURLY):
    return _log(_VIB_COLS, [(t, filtered, unfiltered) for t in times])


# --------------------------------------------------------------------------- #
# Verdicts
# --------------------------------------------------------------------------- #
def test_pass():
    res = MechanicalRunChecker(_vib_log(), _crit()).check()
    assert res.passed and res.fully_assessed
    assert res.duration_status == "pass"
    assert [c.status for c in res.channels] == ["pass", "pass"]
    assert res.verdict == "PASSED"


def test_vibration_over_limit_fails():
    res = MechanicalRunChecker(_vib_log(filtered=2.5), _crit()).check()
    assert not res.passed
    assert res.channels[0].status == "fail"
    assert res.channels[1].status == "pass"
    assert res.verdict == "FAILED"


def test_too_short_fails():
    res = MechanicalRunChecker(_vib_log(times=_HOURLY[:3]), _crit()).check()
    assert res.duration_status == "fail"
    assert not res.passed


def test_no_min_duration_is_info_and_not_fully_assessed():
    res = MechanicalRunChecker(_vib_log(), _crit(min_duration=None)).check()
    assert res.duration_status == "info"
    assert res.passed and not res.fully_assessed
    assert res.verdict == "PASSED (not fully assessed)"


def test_info_only_result_passes():
    log = _log([("Sump", "oil_temperature", "degF")], [(t, 120.0) for t in _HOURLY])
    res = MechanicalRunChecker(log, MechanicalRunCriteria()).check()
    assert res.passed and not res.fully_assessed
    assert res.channels[0].status == "info"


# --------------------------------------------------------------------------- #
# Stabilisation
# --------------------------------------------------------------------------- #
_TEMP_COLS = [("Sump", "oil_temperature", "degF")]
_TEMP_ROWS = [
    ("00:00", 100.0),
    ("00:30", 110.0),
    ("01:00", 120.0),
    ("01:30", 121.0),
    ("02:00", 122.0),
]


def test_stabilisation_unconfigured_is_info():
    res = MechanicalRunChecker(
        _log(_TEMP_COLS, _TEMP_ROWS), _crit(min_duration=None)
    ).check()
    ch = res.channels[0]
    assert ch.status == "info" and ch.stabilisation is None


def test_stabilisation_pass_and_fail():
    log = _log(_TEMP_COLS, _TEMP_ROWS)  # last 60 min: 120..122 degF = 2 delta_degF
    ok = _crit(stabilisation={"oil_temperature": (Q_(2, "delta_degF"), Q_(60, "min"))})
    res = MechanicalRunChecker(log, ok).check()
    ch = res.channels[0]
    assert ch.status == "pass" and ch.stabilisation["ok"] is True
    assert ch.stabilisation["change"].to("delta_degF").magnitude == pytest.approx(2.0)

    tight = _crit(
        stabilisation={"oil_temperature": (Q_(1, "delta_degF"), Q_(60, "min"))}
    )
    res = MechanicalRunChecker(log, tight).check()
    assert res.channels[0].status == "fail" and not res.passed


def test_stabilisation_delta_degc_on_fahrenheit_channel():
    log = _log(_TEMP_COLS, _TEMP_ROWS)
    crit = _crit(stabilisation={"oil_temperature": (Q_(1.2, "delta_degC"), Q_(1, "h"))})
    # 2 delta_degF = 1.11 delta_degC <= 1.2
    assert MechanicalRunChecker(log, crit).check().channels[0].status == "pass"


# --------------------------------------------------------------------------- #
# Units
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "mm_s, in_s, expected",
    [(1.27, 0.05, "pass"), (4.064, 0.16, "fail")],
)
def test_in_per_s_and_mm_per_s_agree(mm_s, in_s, expected):
    crit = _crit(role_max={"vibration_filtered": Q_(3.0, "mm/s")})
    results = []
    for value, unit in ((mm_s, "mm/s"), (in_s, "in/s")):
        log = _log([("V", "vibration_filtered", unit)], [(t, value) for t in _HOURLY])
        results.append(MechanicalRunChecker(log, crit).check())
    assert results[0].channels[0].status == results[1].channels[0].status == expected
    assert results[0].passed == results[1].passed


# --------------------------------------------------------------------------- #
# Log: elapsed time, midnight wrap, series
# --------------------------------------------------------------------------- #
def test_midnight_wrap():
    log = _log(
        [("V", "vibration_filtered", "mm/s")],
        [("23:30", 1.0), ("23:45", 1.0), ("00:00", 1.0), ("00:30", 1.0)],
    )
    assert [e.to("min").magnitude for e in log.elapsed()] == pytest.approx(
        [0, 15, 30, 60]
    )
    assert log.duration.to("min").magnitude == pytest.approx(60)


def test_series_skips_missing_values():
    log = _log(
        [("A", "other", "kW"), ("B", "other", "kW")],
        [("00:00", 1.0, 5.0), ("00:10", None, 6.0), ("00:20", 3.0, 7.0)],
    )
    x, y = log.series("A")
    assert list(x.to("min").magnitude) == pytest.approx([0, 20])
    assert list(y.to("kW").magnitude) == pytest.approx([1.0, 3.0])


def test_duplicate_channel_names_rejected():
    with pytest.raises(ValueError):
        MechanicalRunLog((Channel("A", "other"), Channel("A", "flow")), ())


def test_criteria_from_table():
    crit = MechanicalRunCriteria.from_table(
        {
            "min_duration": "4 h",
            "source": "s",
            "verified": False,
            "roles": [{"role": "vibration_filtered", "max": "2.0 mm/s"}],
        }
    )
    assert crit.min_duration.to("h").magnitude == pytest.approx(4)
    assert crit.role_max["vibration_filtered"].to("mm/s").magnitude == pytest.approx(
        2.0
    )
    assert crit.stabilisation == {} and crit.verified is False


def test_plot_returns_png():
    buf = plot_mechanical_run(_vib_log(), _crit())
    assert buf.read(4) == b"\x89PNG"


# --------------------------------------------------------------------------- #
# Seeds in the standard tables
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", [k for k, _ in AcceptanceCriteria.available()])
def test_every_edition_has_an_open_mechanical_run(key):
    crit = AcceptanceCriteria.load(key)
    mr = crit.mechanical_run
    assert mr.min_duration.to("h").magnitude == pytest.approx(4)
    assert mr.role_max["vibration_filtered"].to("mm/s").magnitude == pytest.approx(2.0)
    assert mr.role_max["vibration_unfiltered"].to("mm/s").magnitude == pytest.approx(
        3.0
    )
    if key == "api610:12":
        # 12th 8.3.4.2.1: rise above ambient <= 1 degC over 10 min, "if
        # specified": defined, but for information only.
        st = mr.stabilisation["oil_temperature"]
        assert st.relative_to_ambient and not st.required
        assert st.delta.to("delta_degC").magnitude == pytest.approx(1.0)
        assert st.window.to("min").magnitude == pytest.approx(10.0)
    else:
        assert mr.stabilisation == {}  # no numeric stabilisation in the text
    # Still open: the 8th edition defines no mechanical run test (duration comes
    # from the purchaser), and the 11th/12th high-speed allowance is not applied.
    assert mr.verified is False
    assert "Table" in mr.source or "Amarinth" in mr.source
    assert "mechanical running test limits" in crit.unverified


def test_n553_adds_temperature_stabilisation():
    crit = AcceptanceCriteria.load("api610:8", client="n553")
    st = crit.mechanical_run.stabilisation["oil_temperature"]
    assert st.delta.to("delta_degC").magnitude == pytest.approx(2.0)
    assert st.window.to("min").magnitude == pytest.approx(30.0)
    assert st.required and not st.relative_to_ambient
    assert st.warmup.to("min").magnitude == pytest.approx(60.0)  # 9.20 NOTE 1
    assert "bearing_temperature" in crit.mechanical_run.stabilisation
    assert "oil_outlet_temperature" in crit.mechanical_run.stabilisation


# --------------------------------------------------------------------------- #
# P-9001A Vendor A record (12/13/2011, 10300 rpm)
# --------------------------------------------------------------------------- #
_P9001A = """
06:00 43.53 487.32 29.72 0.04 0.15 44 116 69.34
06:15 43.51 486.45 29.42 0.04 0.15 44 120 66.77
06:30 43.51 484.71 29.08 0.04 0.15 42 121 65.89
06:45 43.49 485.58 28.78 0.04 0.15 42 121 65.82
07:00 43.49 485.58 28.71 0.04 0.16 42 122 66.11
07:15 43.51 484.71 28.61 0.05 0.15 42 122 65.15
07:30 43.47 485.58 28.76 0.05 0.15 42 122 65.38
07:45 43.51 484.71 28.83 0.05 0.15 42 121 64.94
08:00 43.49 485.58 28.86 0.05 0.14 42 120 65.16
08:15 43.51 485.58 29.15 0.05 0.15 42 121 66.09
08:30 43.49 486.59 29.11 0.05 0.15 42 121 65.45
08:45 43.51 486.45 29.08 0.05 0.15 42 121 65.67
09:00 43.51 486.45 29.03 0.05 0.16 42 122 65.89
09:15 43.49 486.45 28.98 0.05 0.15 42 123 66.11
09:30 43.49 487.32 29.03 0.05 0.15 42 122 65.67
09:45 43.51 487.32 29.08 0.05 0.14 42 123 65.53
10:00 43.49 487.32 29.11 0.05 0.14 42 124 65.65
"""

_B_COLS = [
    ("Flow", "flow", "gal/min"),
    ("dP", "differential_pressure", "psi"),
    ("Power", "power", "kW"),
    ("Vib filtered", "vibration_filtered", "in/s"),
    ("Vib unfiltered", "vibration_unfiltered", "in/s"),
    ("Lube oil", "oil_pressure", "psi"),
    ("Sump", "oil_temperature", "degF"),
    ("Seal cavity", "seal_pressure", "psi"),
]


@pytest.fixture
def p9001a():
    rows = []
    for line in _P9001A.strip().splitlines():
        parts = line.split()
        rows.append((parts[0], *[float(p) for p in parts[1:]]))
    return _log(_B_COLS, rows)


def test_p9001a_log(p9001a):
    assert len(p9001a.readings) == 17
    assert p9001a.duration.to("h").magnitude == pytest.approx(4.0)


def test_p9001a_against_unverified_seed(p9001a):
    crit = AcceptanceCriteria.default().mechanical_run
    res = MechanicalRunChecker(p9001a, crit).check()
    by_name = {c.name: c for c in res.channels}
    assert res.duration_status == "pass"

    filt = by_name["Vib filtered"]
    assert filt.max.to("in/s").magnitude == pytest.approx(0.05)
    assert filt.max.to("mm/s").magnitude == pytest.approx(1.27)
    assert filt.status == "pass"

    unf = by_name["Vib unfiltered"]
    assert unf.max.to("in/s").magnitude == pytest.approx(0.16)
    assert unf.max.to("mm/s").magnitude == pytest.approx(4.064)
    assert (
        unf.status == "fail"
    )  # expected: seed limits are notebook values for another pump class

    assert not res.passed
    assert res.verdict == "FAILED"
    assert by_name["Sump"].status == "info"  # no stabilisation seeded


def test_p9001a_sump_stabilisation_last_hour(p9001a):
    crit = replace(
        AcceptanceCriteria.default().mechanical_run,
        stabilisation={"oil_temperature": (Q_(2, "delta_degF"), Q_(60, "min"))},
    )
    res = MechanicalRunChecker(p9001a, crit).check()
    sump = {c.name: c for c in res.channels}["Sump"]
    assert sump.min.magnitude == pytest.approx(
        116
    ) and sump.max.magnitude == pytest.approx(124)
    assert sump.stabilisation["ok"] is True
    assert sump.stabilisation["change"].to("delta_degF").magnitude == pytest.approx(2.0)
    assert sump.status == "pass"


# --------------------------------------------------------------------------- #
# Bearing temperature rules by lubrication system (8th 2.9.2.3, 11th 6.10.2.4,
# 12th 6.10.2.7, N-553 rev E 7.35 c / 9.20)
# --------------------------------------------------------------------------- #
_QUARTER = [f"{h:02d}:{m:02d}" for h in range(4) for m in (0, 15, 30, 45)] + ["04:00"]


def _temp_log(cols, values, lubrication, times=_QUARTER):
    """cols: [(name, role, location)]; values: {name: constant degC or list}."""
    channels = tuple(Channel(n, r, loc) for n, r, loc in cols) + tuple(
        Channel(n, r) for n, r, _u in _VIB_COLS
    )
    readings = []
    for i, t in enumerate(times):
        vals = {n: Q_(1.0, "mm/s") for n, _r, _u in _VIB_COLS}
        for name, v in values.items():
            x = v[i] if isinstance(v, list) else v
            if x is not None:
                vals[name] = Q_(x, "degC")
        readings.append(RunReading(t, vals))
    return MechanicalRunLog(channels, tuple(readings), lubrication=lubrication)


def _check(log, key, client=None):
    crit = AcceptanceCriteria.load(key, client=client).mechanical_run
    crit = replace(
        crit,
        role_max={
            "vibration_filtered": Q_(2, "mm/s"),
            "vibration_unfiltered": Q_(3, "mm/s"),
        },
    )
    return MechanicalRunChecker(log, crit).check()


def _rule(res, key):
    return next(r for r in res.rules if r.key == key)


_PRESS = [
    ("Oil inlet", "oil_inlet_temperature", ""),
    ("Oil out DE", "oil_outlet_temperature", "DE"),
    ("Oil out NDE", "oil_outlet_temperature", "NDE"),
]


def test_pressurized_oil_rise_is_outlet_minus_inlet():
    log = _temp_log(
        _PRESS,
        {"Oil inlet": 40.0, "Oil out DE": 62.0, "Oil out NDE": 66.0},
        "pressurized",
    )
    res = _check(log, "api610:11")
    rise = _rule(res, "oil_rise_max")
    assert rise.status == "pass"
    assert rise.value.to("delta_degC").magnitude == pytest.approx(26.0)  # worst bearing
    assert rise.limit.to("delta_degC").magnitude == pytest.approx(28.0)
    # no bearing sensors: the metal limit applies "if supplied" -> information
    assert _rule(res, "bearing_metal_max").status == "info"
    # 70 degC outlet design limit at 43 degC ambient: reported, not judged
    assert _rule(res, "oil_outlet_design_max").status == "info"
    assert res.passed and res.fully_assessed


def test_pressurized_rise_over_28_K_fails():
    log = _temp_log(
        _PRESS,
        {"Oil inlet": 40.0, "Oil out DE": 62.0, "Oil out NDE": 69.0},
        "pressurized",
    )
    res = _check(log, "api610:12")
    assert _rule(res, "oil_rise_max").status == "fail" and not res.passed


def test_outlet_paired_with_the_inlet_of_its_bearing():
    cols = [
        ("In DE", "oil_inlet_temperature", "DE"),
        ("In NDE", "oil_inlet_temperature", "NDE"),
        ("Out DE", "oil_outlet_temperature", "DE"),
        ("Out NDE", "oil_outlet_temperature", "NDE"),
    ]
    log = _temp_log(
        cols,
        {"In DE": 30.0, "In NDE": 45.0, "Out DE": 55.0, "Out NDE": 70.0},
        "pressurized",
    )
    rise = _rule(_check(log, "api610:11"), "oil_rise_max")
    assert rise.value.to("delta_degC").magnitude == pytest.approx(25.0)


def test_missing_inlet_is_not_evaluated():
    log = _temp_log(
        _PRESS[1:], {"Oil out DE": 62.0, "Oil out NDE": 66.0}, "pressurized"
    )
    res = _check(log, "api610:11")
    rule = _rule(res, "oil_rise_max")
    assert rule.status == "not evaluated" and "inlet" in rule.note
    assert res.passed and not res.fully_assessed
    assert res.verdict == "PASSED (not fully assessed)"


@pytest.mark.parametrize(
    "key, limit, ok", [("api610:11", 40, True), ("api610:12", 39, False)]
)
def test_ring_oil_sump_rise_above_ambient(key, limit, ok):
    cols = [("Sump", "oil_temperature", ""), ("Ambient", "ambient_temperature", "")]
    log = _temp_log(cols, {"Sump": 65.0, "Ambient": 25.0}, "ring_oil")
    rule = _rule(_check(log, key), "sump_rise_max")
    assert rule.value.to("delta_degC").magnitude == pytest.approx(40.0)
    assert rule.limit.to("delta_degC").magnitude == pytest.approx(limit)
    assert rule.status == ("pass" if ok else "fail")


def test_sump_rise_is_judged_at_each_reading():
    # 11th 6.10.2.4 b): "above the ambient ... at the time of each reading"
    cols = [("Sump", "oil_temperature", ""), ("Ambient", "ambient_temperature", "")]
    n = len(_QUARTER)
    sump = [60.0] * n
    ambient = [25.0] * n
    ambient[5] = 18.0  # a cold reading: 42 K rise at that moment
    log = _temp_log(cols, {"Sump": sump, "Ambient": ambient}, "ring_oil")
    rule = _rule(_check(log, "api610:11"), "sump_rise_max")
    assert rule.value.to("delta_degC").magnitude == pytest.approx(42.0)
    assert rule.status == "fail"


def test_ring_oil_without_ambient_is_not_evaluated():
    log = _temp_log([("Sump", "oil_temperature", "")], {"Sump": 65.0}, "ring_oil")
    res = _check(log, "api610:11")
    assert _rule(res, "sump_rise_max").status == "not evaluated"
    assert not res.fully_assessed


def test_bearing_metal_limit_when_sensors_are_supplied():
    cols = _PRESS + [("Brg DE", "bearing_temperature", "DE")]
    log = _temp_log(
        cols,
        {"Oil inlet": 40.0, "Oil out DE": 60.0, "Oil out NDE": 60.0, "Brg DE": 95.0},
        "pressurized",
    )
    assert _rule(_check(log, "api610:11"), "bearing_metal_max").status == "fail"


def test_oil_mist_12th_with_n553_keeps_the_stricter_limits():
    cols = [
        ("Housing DE", "housing_temperature", "DE"),
        ("Ambient", "ambient_temperature", ""),
        ("Brg DE", "bearing_temperature", "DE"),
    ]
    log = _temp_log(
        cols, {"Housing DE": 70.5, "Ambient": 40.0, "Brg DE": 90.0}, "oil_mist"
    )
    res = _check(log, "api610:12", client="n553")
    assert _rule(res, "housing_max").limit.to("degC").magnitude == pytest.approx(70.0)
    assert _rule(res, "housing_max").status == "fail"  # N-553 7.35 c: below 70 degC
    assert _rule(res, "bearing_metal_max").limit.to("degC").magnitude == pytest.approx(
        88.0
    )
    assert _rule(res, "bearing_metal_max").status == "fail"  # 12th 6.10.2.7 c: 88 degC
    assert _rule(res, "housing_rise_max").status == "pass"  # 30.5 K <= 35 K


def test_no_lubrication_stated_is_not_evaluated():
    log = _temp_log(
        _PRESS, {"Oil inlet": 40.0, "Oil out DE": 60.0, "Oil out NDE": 60.0}, None
    )
    res = _check(log, "api610:11")
    assert [(r.key, r.status) for r in res.rules] == [("lubrication", "not evaluated")]
    assert not res.fully_assessed


def test_lubrication_without_rules_in_the_edition_is_information():
    log = _temp_log([], {}, "oil_mist")
    res = _check(log, "api610:11")  # 11th: no oil-mist rule (N-553 adds one)
    assert [(r.key, r.status) for r in res.rules] == [("lubrication", "info")]


def test_unknown_lubrication_is_rejected():
    with pytest.raises(ValueError, match="lubrication"):
        MechanicalRunLog((), (), lubrication="water")


def test_criteria_without_temperature_rules_add_none():
    log = _temp_log(_PRESS, {"Oil inlet": 40.0}, "pressurized")
    assert MechanicalRunChecker(log, _crit()).check().rules == ()


def test_12th_stabilisation_relative_to_ambient_is_information_only():
    cols = [("Sump", "oil_temperature", ""), ("Ambient", "ambient_temperature", "")]
    n = len(_QUARTER)
    sump = [50.0 + i for i in range(n)]  # still rising 1 K per 15 min...
    ambient = [20.0 + i for i in range(n)]  # ...but so is the cell: rise constant
    log = _temp_log(cols, {"Sump": sump, "Ambient": ambient}, "ring_oil")
    res = _check(log, "api610:12")
    sump_ch = next(c for c in res.channels if c.name == "Sump")
    st = sump_ch.stabilisation
    assert st["relative_to_ambient"] and not st["required"]
    assert st["ok"] is True and st["change"].to(
        "delta_degC"
    ).magnitude == pytest.approx(0)
    assert sump_ch.status == "info"  # "if specified": never pass/fail on its own


def test_n553_stabilisation_needs_the_warm_up():
    cols = _PRESS
    short = ["00:00", "00:15", "00:30", "00:45", "01:00"]
    log = _temp_log(
        cols,
        {"Oil inlet": 40.0, "Oil out DE": 60.0, "Oil out NDE": 60.0},
        "pressurized",
        times=short,
    )
    res = _check(log, "api610:11", client="n553")
    out = next(c for c in res.channels if c.name == "Oil out DE")
    # 1 h warm-up + 30 min window > 1 h run: cannot be judged yet
    assert out.status == "not evaluated" and not res.fully_assessed
    long = _temp_log(
        cols,
        {"Oil inlet": 40.0, "Oil out DE": 60.0, "Oil out NDE": 60.0},
        "pressurized",
    )
    out = next(
        c
        for c in _check(long, "api610:11", client="n553").channels
        if c.name == "Oil out DE"
    )
    assert out.status == "pass"
