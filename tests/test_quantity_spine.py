"""
Library quantity spine — sprint 1 of project 001_masterpiece.

Asserts the new single serialisation path (``pump.quantity_io``), the explicit
gauge/absolute ``Pressure`` type, standard gravity, the ``kinematic_viscosity``
standard unit, and the ``Water`` viscosity / vapour-pressure properties.

Run with::

    pytest tests/test_quantity_spine.py -v
"""

import json
import warnings

import pytest

from pump import G, P_ATM, Pressure, Q_, DesignPoint, TestPoint, Water, quantity_factory
from pump import quantity_io

# --------------------------------------------------------------------------- #
# quantity_io — JSON round-trips
# --------------------------------------------------------------------------- #
ROUND_TRIP = [
    (833.0, "m**3/h"),  # capacity
    (73.0, "m"),  # head
    (252.0, "kW"),  # power
    (50.0, "psi"),  # pressure
    (1.5, "bar"),
    (3.2, "kgf/cm**2"),
    (250.0, "kPa"),
    (20.0, "degC"),  # temperature
    (68.0, "degF"),
    (293.15, "K"),
    (1750.0, "rpm"),  # speed
    (1.004, "cSt"),  # viscosity
    (1.002, "cP"),
    (12.0, "mm"),  # length
    (4.0, "inch"),
    (10.0, "ft"),
    (36.8, "percent"),
    (998.2, "kg/m**3"),
    (5.0, "delta_degC"),
    (800.0, "gallon/minute"),
    (100.0, "hp"),
]


@pytest.mark.parametrize("value, unit", ROUND_TRIP)
def test_quantity_json_round_trip(value, unit):
    q = Q_(value, unit)
    d = quantity_io.to_json(q)
    assert set(d) == {"value", "unit"}
    assert isinstance(d["value"], float)
    assert isinstance(d["unit"], str)

    back = quantity_io.from_json(json.loads(json.dumps(d)))
    assert back.units == q.units
    assert back.magnitude == pytest.approx(value)
    assert back.to(unit).magnitude == pytest.approx(value)


def test_from_json_bare_number_uses_default_unit():
    q = quantity_io.from_json(12.5, default_unit="mm")
    assert q.to("mm").magnitude == pytest.approx(12.5)


def test_from_json_bare_number_without_default_unit_raises():
    with pytest.raises(ValueError):
        quantity_io.from_json(12.5)


def test_from_json_malformed_input_raises():
    with pytest.raises(ValueError):
        quantity_io.from_json({"unit": "mm"})
    with pytest.raises(ValueError):
        quantity_io.from_json("12 mm")


def test_to_json_rejects_non_quantity():
    with pytest.raises(ValueError):
        quantity_io.to_json(12.0)


# --------------------------------------------------------------------------- #
# Pressure — gauge / absolute semantics
# --------------------------------------------------------------------------- #
def test_pressure_difference_is_reference_free():
    diff = Pressure(Q_(50, "psi"), "g") - Pressure(Q_(10, "psi"), "g")
    assert diff.to("psi").magnitude == pytest.approx(40.0)


def test_pressure_gauge_to_absolute():
    absolute = Pressure(Q_(1, "bar"), "g").absolute()
    assert absolute.to("bar").magnitude == pytest.approx(2.01325)


def test_pressure_absolute_to_gauge():
    gauge = Pressure(Q_(2.01325, "bar"), "a").gauge()
    assert gauge.to("bar").magnitude == pytest.approx(1.0)


def test_pressure_mixed_references_raise():
    with pytest.raises(ValueError, match="mixed gauge/absolute"):
        Pressure(Q_(1, "bar"), "g") - Pressure(Q_(1, "bar"), "a")


def test_pressure_validates_inputs():
    with pytest.raises(ValueError):
        Pressure(Q_(1, "m"), "g")
    with pytest.raises(ValueError):
        Pressure(Q_(1, "bar"), "x")
    with pytest.raises(ValueError):
        Pressure(Q_(1, "bar"), "g", atmosphere=Q_(1, "kg"))


def test_pressure_json_round_trip():
    p = Pressure(Q_(3.5, "kgf/cm**2"), "a", Q_(1.0, "bar"))
    d = json.loads(json.dumps(p.to_json()))
    assert d["ref"] == "a"
    assert set(d["atm"]) == {"value", "unit"}
    assert Pressure.from_json(d) == p


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
def test_standard_gravity_and_atmosphere():
    assert G.to("m/s**2").magnitude == pytest.approx(9.80665)
    assert P_ATM.to("Pa").magnitude == pytest.approx(101325.0)


def test_points_use_shared_gravity_constant():
    assert DesignPoint.g is G
    assert TestPoint.g is G


# --------------------------------------------------------------------------- #
# Water — viscosity and vapour pressure
# --------------------------------------------------------------------------- #
def test_water_20c_kinematic_viscosity():
    nu = Water(Q_(20, "degC")).kinematic_viscosity
    assert nu.to("cSt").magnitude == pytest.approx(1.004, rel=0.01)


def test_water_20c_vapour_pressure():
    pv = Water(Q_(20, "degC")).vapour_pressure
    assert pv.to("kPa").magnitude == pytest.approx(2.339, rel=0.01)


def test_water_100c_vapour_pressure():
    pv = Water(Q_(100, "degC")).vapour_pressure
    assert pv.to("kPa").magnitude == pytest.approx(101.4, rel=0.01)


def test_water_vapour_pressure_out_of_range_raises():
    with pytest.raises(ValueError):
        Water(Q_(-10, "degC")).vapour_pressure
    with pytest.raises(ValueError):
        Water(Q_(400, "degC")).vapour_pressure


def test_water_equality_and_dict_unaffected_by_new_properties():
    assert Water(Q_(20, "degC")) == Water(Q_(20, "degC"))
    assert set(vars(Water(Q_(20, "degC")))) == {"name", "density", "temperature"}


# --------------------------------------------------------------------------- #
# kinematic_viscosity is a standard unit
# --------------------------------------------------------------------------- #
def test_cst_quantity_factory_emits_no_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        q = quantity_factory(Q_(1, "cSt"))
    assert q.magnitude == pytest.approx(1.0)
    assert q.units == Q_(1, "cSt").units


def test_stokes_converts_to_cst():
    q = quantity_factory(Q_(1, "St"))
    assert q.to("cSt").magnitude == pytest.approx(100.0)
    assert q.units == Q_(1, "cSt").units
