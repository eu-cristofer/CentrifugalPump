"""Sprint 4: complete head = pressure + velocity + elevation (Qt-free)."""

import math

import pytest

from pump import Q_, Pressure
from pump.constants import G
from pumpflow import settings_codec as codec
from pumpflow import units
from pumpflow.binding import format_geometry, row_head, row_head_components
from pumpflow.signals import BenchGeometry, TestRow

RHO = Q_(998.0, "kg/m**3")
G_MS2 = float(G.to("m/s**2").magnitude)


def _g(value, unit):
    return Pressure(Q_(value, unit), "g")


def _row(**kw):
    base = dict(
        q=Q_(100.0, "m**3/h"),
        p_suction=_g(1.0, "bar"),
        p_discharge=_g(6.0, "bar"),
        temperature=Q_(25.0, "degC"),
        speed=Q_(1800.0, "rpm"),
        power=Q_(20.0, "kW"),
    )
    base.update(kw)
    return TestRow(**base)


GEOM = BenchGeometry(
    suction_id=Q_(150.0, "mm"),
    discharge_id=Q_(100.0, "mm"),
    suction_elevation=Q_(0.3, "m"),
    discharge_elevation=Q_(0.8, "m"),
)


def _hand():
    """Hand calculation (SI floats): ΔP/(ρg), (v_d²−v_s²)/2g, z_d−z_s."""
    q = 100.0 / 3600.0  # m3/s
    v_s = q / (math.pi * 0.150**2 / 4.0)
    v_d = q / (math.pi * 0.100**2 / 4.0)
    pressure = 5.0e5 / (998.0 * G_MS2)
    velocity = (v_d**2 - v_s**2) / (2.0 * G_MS2)
    elevation = 0.8 - 0.3
    return pressure, velocity, elevation


def test_total_matches_hand_calculation():
    pressure, velocity, elevation = _hand()
    head = row_head(_row(), RHO, GEOM)
    assert head.units == Q_(1, "m").units
    assert head.magnitude == pytest.approx(pressure + velocity + elevation, rel=1e-9)


def test_components_match_hand_calculation():
    pressure, velocity, elevation = _hand()
    c = row_head_components(_row(), RHO, GEOM)
    assert c["pressure"].to("m").magnitude == pytest.approx(pressure, rel=1e-9)
    assert c["velocity"].to("m").magnitude == pytest.approx(velocity, rel=1e-9)
    assert c["elevation"].to("m").magnitude == pytest.approx(elevation, rel=1e-9)
    assert c["total"].to("m").magnitude == pytest.approx(
        pressure + velocity + elevation, rel=1e-9
    )
    assert velocity > 0 and elevation > 0  # the geometry really matters


def test_one_id_missing_gives_zero_velocity_term():
    pressure, _velocity, elevation = _hand()
    geom = BenchGeometry(
        suction_id=Q_(150.0, "mm"),
        suction_elevation=Q_(0.3, "m"),
        discharge_elevation=Q_(0.8, "m"),
    )
    assert geom.components_available() == (False, True)
    c = row_head_components(_row(), RHO, geom)
    assert c["velocity"].to("m").magnitude == 0.0
    assert row_head(_row(), RHO, geom).magnitude == pytest.approx(
        pressure + elevation, rel=1e-9
    )


def test_one_elevation_missing_gives_zero_elevation_term():
    pressure, velocity, _elevation = _hand()
    geom = BenchGeometry(
        suction_id=Q_(150.0, "mm"),
        discharge_id=Q_(100.0, "mm"),
        suction_elevation=Q_(0.3, "m"),
    )
    assert geom.components_available() == (True, False)
    c = row_head_components(_row(), RHO, geom)
    assert c["elevation"].to("m").magnitude == 0.0
    assert row_head(_row(), RHO, geom).magnitude == pytest.approx(
        pressure + velocity, rel=1e-9
    )


def test_units_entered_do_not_matter():
    mixed = BenchGeometry(
        suction_id=Q_(150.0, "mm").to("inch"),
        discharge_id=Q_(0.1, "m"),
        suction_elevation=Q_(300.0, "mm"),
        discharge_elevation=Q_(0.8, "m").to("ft"),
    )
    assert row_head(_row(), RHO, mixed).magnitude == pytest.approx(
        row_head(_row(), RHO, GEOM).magnitude, rel=1e-9
    )


def test_no_geometry_is_bit_identical_to_pressure_only_head():
    row = _row()
    old = ((row.p_discharge - row.p_suction) / (RHO * G)).to("m")
    for geometry in (None, BenchGeometry()):
        new = row_head(row, RHO, geometry)
        assert new == old
        assert repr(new) == repr(old)
        assert new.magnitude == old.magnitude
    # the 2-argument call (every pre-sprint caller) is unchanged too
    assert repr(row_head(row, RHO)) == repr(old)
    c = row_head_components(row, RHO, None)
    assert c["total"] == old and c["pressure"] == old
    assert c["velocity"].magnitude == 0.0 and c["elevation"].magnitude == 0.0


def test_explicit_row_head_still_wins():
    row = _row(head=Q_(80.0, "m"))
    assert row_head(row, RHO, GEOM).magnitude == pytest.approx(80.0, rel=1e-12)
    c = row_head_components(row, RHO, GEOM)
    assert c["total"].magnitude == pytest.approx(80.0, rel=1e-12)
    assert c["velocity"].magnitude == 0.0 and c["elevation"].magnitude == 0.0


def test_format_geometry_uses_entered_units():
    text = format_geometry(GEOM)
    assert text == "suction ID 150 mm · discharge ID 100 mm · z_s 0.3 m · z_d 0.8 m"
    partial = BenchGeometry(
        suction_id=Q_(6.0, "inch"), discharge_elevation=Q_(0.8, "m")
    )
    assert format_geometry(partial) == "suction ID 6 in · z_d 0.8 m"


# --------------------------------------------------------------------------- #
# codec: optional length quantities
# --------------------------------------------------------------------------- #
def _runtime(**geo):
    cols = {k: units.canonical_unit(d) for k, d in units.COLUMN_DIMENSIONS.items()}
    cols["p_suc"] = cols["p_dis"] = "bar"
    rows = [
        {
            "q": 100.0,
            "p_suc": 1.0,
            "p_dis": 6.0,
            "temp_c": 25.0,
            "n": 1800.0,
            "power": 20.0,
            "head": None,
            "eff": None,
        }
    ]
    rt = {
        "pump_tag": "B-1",
        "fluid_choice": "",
        "columns": cols,
        "pressure_ref": "g",
        "rows": rows,
    }
    rt.update(geo)
    return rt


def test_codec_roundtrip_with_geometry_set():
    rt = _runtime(
        suction_id=150.0,
        suction_id_unit="mm",
        discharge_id=4.0,
        discharge_id_unit="in",
        suction_z=0.3,
        suction_z_unit="m",
        discharge_z=0.8,
        discharge_z_unit="m",
    )
    v2 = codec.encode("test_points", rt)
    assert v2["suction_id"] == {"value": 150.0, "unit": "mm"}
    assert v2["discharge_id"] == {"value": 4.0, "unit": "in"}
    assert v2["suction_z"] == {"value": 0.3, "unit": "m"}
    assert "suction_id_unit" not in v2 and "discharge_z_unit" not in v2
    assert codec.decode("test_points", v2) == rt
    assert codec.encode("test_points", codec.decode("test_points", v2)) == v2


def test_codec_roundtrip_with_geometry_unset_has_no_stray_unit_keys():
    rt = _runtime(suction_id=None, discharge_id=None, suction_z=None, discharge_z=None)
    v2 = codec.encode("test_points", rt)
    # unset optional geometry is omitted on disk: a re-saved file equals one
    # written before the feature existed (and equals what migrate() produces)
    for k in ("suction_id", "discharge_id", "suction_z", "discharge_z"):
        assert k not in v2 and f"{k}_unit" not in v2
    assert codec.encode("test_points", codec.decode("test_points", v2)) == v2
    # runtime dicts that still carry unit labels encode to the same document
    with_units = dict(rt, suction_id_unit="mm", suction_z_unit="m")
    assert codec.encode("test_points", with_units) == v2


def test_codec_old_files_without_geometry_keys_stay_without():
    rt = _runtime()
    v2 = codec.encode("test_points", rt)
    assert not any(k.startswith(("suction_", "discharge_")) for k in v2)
    back = codec.decode("test_points", v2)
    assert not any(k.startswith(("suction_", "discharge_")) for k in back)
    assert codec.encode("test_points", back) == v2
