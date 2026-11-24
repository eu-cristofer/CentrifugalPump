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
    assert mr.stabilisation == {}  # API editions: no stabilisation rule encoded
    # Still open: the 8th edition defines no mechanical run test (duration comes
    # from the purchaser), and the 11th/12th high-speed allowance is not applied.
    assert mr.verified is False
    assert "Table" in mr.source or "Amarinth" in mr.source
    assert "mechanical running test limits" in crit.unverified


def test_n553_adds_temperature_stabilisation():
    crit = AcceptanceCriteria.load("api610:8", client="n553")
    delta, window = crit.mechanical_run.stabilisation["oil_temperature"]
    assert delta.to("delta_degC").magnitude == pytest.approx(2.0)
    assert window.to("min").magnitude == pytest.approx(30.0)
    assert "bearing_temperature" in crit.mechanical_run.stabilisation


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
