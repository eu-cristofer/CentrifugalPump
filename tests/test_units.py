"""Qt-free tests for the multi-unit spine: UNIT_OPTIONS, header parsing, codec."""

import pytest

from pump import Q_
from pumpflow import settings_codec as codec
from pumpflow import units

NEW_DIMS = (
    "pressure",
    "speed",
    "length",
    "npsh",
    "efficiency",
    "vibration_velocity",
)


@pytest.mark.parametrize(
    "dim,label,pint",
    [(d, lab, p) for d, opts in units.UNIT_OPTIONS.items() for lab, p in opts],
)
def test_every_unit_option_parses(dim, label, pint):
    assert Q_(1, pint) is not None
    assert units.label_for(dim, pint) is not None


@pytest.mark.parametrize("dim", NEW_DIMS)
def test_to_standard_and_convert_display_roundtrip(dim):
    canon = units.canonical_unit(dim)
    assert units.to_standard(12.5, dim, canon) == pytest.approx(12.5, rel=1e-12)
    for label, _p in units.UNIT_OPTIONS[dim]:
        std = units.to_standard(12.5, dim, label)
        assert std == pytest.approx(
            units.convert_display(12.5, dim, label, canon), rel=1e-12
        )
        there = units.convert_display(12.5, dim, canon, label)
        back = units.convert_display(there, dim, label, canon)
        assert back == pytest.approx(12.5, rel=1e-12)


def test_known_conversions():
    assert units.convert_display(1.0, "pressure", "bar", "kPa") == pytest.approx(100.0)
    assert units.convert_display(60.0, "speed", "rpm", "rev/s") == pytest.approx(1.0)
    assert units.convert_display(25.4, "length", "mm", "in") == pytest.approx(1.0)
    assert units.convert_display(61.0, "efficiency", "%", "fraction") == pytest.approx(
        0.61
    )
    assert units.atm_in("bar") == pytest.approx(1.01325)


def test_presets_cover_new_dimensions():
    for preset in ("SI", "US"):
        for dim in NEW_DIMS:
            assert units.PRESETS[preset][dim] in dict(units.options_for(dim))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Q [gpm]", ("q", "US GPM", None)),
        ("q [m³/h]", ("q", "m³/h", None)),
        ("P_dis [psi g]", ("p_dis", "psi", "g")),
        ("P_suc [bar a]", ("p_suc", "bar", "a")),
        ("T [°F]", ("temp_c", "°F", None)),
        ("T_water [degC]", ("temp_c", "°C", None)),
        ("N [rpm]", ("n", "rpm", None)),
        ("P [hp]", ("power", "hp", None)),
        ("Head [ft]", ("head", "ft", None)),
        ("η [%]", ("eff", "%", None)),
        ("eff [fraction]", ("eff", "fraction", None)),
        ("P_suc [kgf/cm2]", ("p_suc", "kgf/cm²", None)),
        ("P_dis [mH2O g]", ("p_dis", "mH₂O", "g")),
        ("Head", ("head", None, None)),
    ],
)
def test_parse_unit_header(text, expected):
    assert units.parse_unit_header(text) == expected


@pytest.mark.parametrize("text", ["Q [parsec]", "P_dis [furlong g]", "foo [m]", "300"])
def test_parse_unit_header_errors(text):
    with pytest.raises(ValueError):
        units.parse_unit_header(text)


def test_codec_roundtrip_new_rated_keys():
    rt = {
        "q": 833.0,
        "q_unit": "m³/h",
        "n": 29.0,
        "n_unit": "rev/s",
        "eff": 0.61,
        "eff_unit": "fraction",
        "head_shutoff": 300.0,
        "head_shutoff_unit": "ft",
        "npsha": 10.0,
        "npsha_unit": "ft",
    }
    v2 = codec.encode("rated_point", rt)
    assert v2["eff"] == {"value": 0.61, "unit": "dimensionless"}
    assert codec.decode("rated_point", v2) == rt
    assert codec.encode("rated_point", codec.decode("rated_point", v2)) == v2


def test_codec_roundtrip_correction_and_plot():
    rt = {"target_speed": 29.0, "target_speed_unit": "rev/s"}
    assert codec.decode("correction", codec.encode("correction", rt)) == rt
    plot = {
        "head_ylim": [0.0, 300.0],
        "head_ylim_unit": "ft",
        "power_ylim": None,
        "eff_ylim": [0.0, 1.0],
        "eff_ylim_unit": "fraction",
    }
    v2 = codec.encode("performance_plot", plot)
    assert v2["head_ylim"]["unit"] == "ft"
    assert codec.decode("performance_plot", v2) == plot


def test_codec_roundtrip_point_pressure_label_and_ref():
    rt = {
        "p_suc": 2.0,
        "p_dis": 10.0,
        "p_unit": "psi",
        "p_ref": "a",
        "eff": 61.0,
        "eff_unit": "%",
    }
    v2 = codec.encode("point", rt)
    assert v2["p_suc"]["ref"] == "a" and v2["p_dis"]["unit"] == "psi"
    assert codec.decode("point", v2) == rt
    assert codec.encode("point", codec.decode("point", v2)) == v2


def test_codec_v1_point_kgf_label():
    d = codec.upgrade_v1("point", {"p_suc": 1.0, "p_dis": 5.0, "p_unit": "kgf/cm**2"})
    assert d["p_unit"] == "kgf/cm²"
    rt = codec.decode("point", codec.encode("point", d))
    assert rt["p_unit"] == "kgf/cm²" and rt["p_ref"] == "g" and rt["p_suc"] == 1.0


def _tp_runtime(columns, ref="g", rows=None):
    return {
        "pump_tag": "A",
        "fluid_choice": "",
        "columns": columns,
        "pressure_ref": ref,
        "rows": rows
        or [
            {
                "q": 100.0,
                "p_suc": 1.5,
                "p_dis": 10.0,
                "temp_c": 30.0,
                "n": 1800.0,
                "power": 10.0,
                "head": None,
                "eff": None,
            }
        ],
    }


def test_codec_roundtrip_test_points_columns():
    cols = {
        "q": "US GPM",
        "p_suc": "psi",
        "p_dis": "psi",
        "temp_c": "°F",
        "n": "rpm",
        "power": "hp",
        "head": "ft",
        "eff": "fraction",
    }
    rt = _tp_runtime(cols, ref="a")
    v2 = codec.encode("test_points", rt)
    assert "unit" not in v2 and v2["pressure_ref"] == "a"
    assert v2["columns"]["q"] == "gal/min" and v2["columns"]["temp_c"] == "°F"
    assert v2["rows"] == rt["rows"]
    back = codec.decode("test_points", v2)
    assert back == rt  # rows stay in their column units, untouched
    assert codec.encode("test_points", back) == v2


def test_codec_upgrade_v1_test_points():
    v1 = {
        "pump_tag": "A",
        "unit": "kgf/cm**2",
        "fluid_choice": "",
        "rows": [
            {
                "q": 1.0,
                "p_suc": 1.0,
                "p_dis": 2.0,
                "temp_c": 25.0,
                "n": 1.0,
                "power": 1.0,
                "head": None,
                "eff": None,
            }
        ],
    }
    rt = codec.decode(
        "test_points", codec.encode("test_points", codec.upgrade_v1("test_points", v1))
    )
    assert rt["columns"] == {
        "q": "m³/h",
        "p_suc": "kgf/cm²",
        "p_dis": "kgf/cm²",
        "temp_c": "°C",
        "n": "rpm",
        "power": "kW",
        "head": "m",
        "eff": "%",
    }
    assert rt["pressure_ref"] == "g" and rt["rows"] == v1["rows"]


def test_codec_decode_unlabelled_columns_go_canonical():
    st = codec.encode(
        "test_points",
        _tp_runtime(
            {
                "q": "m³/h",
                "p_suc": "bar",
                "p_dis": "bar",
                "temp_c": "°C",
                "n": "rpm",
                "power": "kW",
                "head": "m",
                "eff": "%",
            }
        ),
    )
    st["columns"]["q"] = "m**3/s"
    st["columns"]["p_suc"] = st["columns"]["p_dis"] = "Pa"
    st["rows"][0].update(q=1.0, p_suc=100000.0, p_dis=200000.0)
    rt = codec.decode("test_points", st)
    assert rt["columns"]["q"] == "m³/h" and rt["columns"]["p_suc"] == "bar"
    assert rt["rows"][0]["q"] == pytest.approx(3600.0)
    assert rt["rows"][0]["p_suc"] == pytest.approx(1.0)
    assert rt["rows"][0]["p_dis"] == pytest.approx(2.0)


def test_test_points_us_columns_equal_si_columns():
    pytest.importorskip("PySide6", reason="test_points node imports PySide6")
    from pumpflow.nodes.test_points import _row_from_dict

    si_cols = {
        "q": "m³/h",
        "p_suc": "bar",
        "p_dis": "bar",
        "temp_c": "°C",
        "n": "rpm",
        "power": "kW",
        "head": "m",
        "eff": "%",
    }
    us_cols = {
        "q": "US GPM",
        "p_suc": "psi",
        "p_dis": "psi",
        "temp_c": "°F",
        "n": "rpm",
        "power": "hp",
        "head": "ft",
        "eff": "%",
    }
    si = {
        "q": 100.0,
        "p_suc": 1.5,
        "p_dis": 10.0,
        "temp_c": 30.0,
        "n": 1800.0,
        "power": 10.0,
        "head": 80.0,
        "eff": 55.0,
    }
    us = {
        "q": Q_(100.0, "m**3/h").to("gallon/min").magnitude,
        "p_suc": Q_(1.5, "bar").to("psi").magnitude,
        "p_dis": Q_(10.0, "bar").to("psi").magnitude,
        "temp_c": Q_(30.0, "degC").to("degF").magnitude,
        "n": 1800.0,
        "power": Q_(10.0, "kW").to("hp").magnitude,
        "head": Q_(80.0, "m").to("ft").magnitude,
        "eff": 55.0,
    }
    a = _row_from_dict(si, si_cols, "g")
    b = _row_from_dict(us, us_cols, "g")
    assert b.q.to("m**3/h").magnitude == pytest.approx(a.q.magnitude, rel=1e-12)
    assert b.p_suction.value.to("bar").magnitude == pytest.approx(1.5, rel=1e-12)
    assert b.p_discharge.value.to("bar").magnitude == pytest.approx(10.0, rel=1e-12)
    assert b.temperature.to("degC").magnitude == pytest.approx(30.0, rel=1e-12)
    assert b.power.to("kW").magnitude == pytest.approx(10.0, rel=1e-12)
    assert b.head.to("m").magnitude == pytest.approx(80.0, rel=1e-12)
    assert b.efficiency.to("percent").magnitude == pytest.approx(55.0, rel=1e-12)
