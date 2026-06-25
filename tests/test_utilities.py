"""
Units & ``Fluid`` spec — the executable version of ``tests/utilities_test.ipynb``.

The notebook *prints* expected values in comments; this module *asserts* them, so a
regression in unit canonicalization (which underpins every API 610 compliance
verdict — UC-02) fails loudly instead of silently. Each test below maps to one
printed line of the notebook, followed by the contract edge cases the notebook does
not show but the code promises.

Run with::

    pytest tests/test_utilities.py -v
"""

import pytest

from pump import Q_, Fluid, quantity_factory


# --------------------------------------------------------------------------- #
# quantity_factory — the printed notebook examples
# --------------------------------------------------------------------------- #
def test_mass_canonicalizes_to_kilogram():
    # notebook: quantity_factory(Q_(500, "gram"))  ->  0.5 kilogram
    q = quantity_factory(Q_(500, "gram"))
    assert str(q.units) == "kilogram"
    assert q.magnitude == pytest.approx(0.5)


def test_pressure_atm_context_to_pascal():
    # notebook: quantity_factory(Q_(1, "atm"), context="atm")  ->  101325.0 pascal
    q = quantity_factory(Q_(1, "atm"), context="atm")
    assert str(q.units) == "pascal"
    assert q.magnitude == pytest.approx(101325.0)


def test_pressure_delta_context_to_bar():
    # notebook: quantity_factory(Q_(1, "atm"), context="delta")  ->  1.01325 bar
    q = quantity_factory(Q_(1, "atm"), context="delta")
    assert str(q.units) == "bar"
    assert q.magnitude == pytest.approx(1.01325)


def test_temperature_delta_context_to_kelvin():
    # notebook: quantity_factory(Q_(1, "degC"), context="delta")  ->  1.0 kelvin
    # A 1 °C difference equals a 1 K difference (delta-temperature branch).
    q = quantity_factory(Q_(1, "degC"), context="delta")
    assert str(q.units) == "kelvin"
    assert q.magnitude == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# Fluid — the printed notebook example
# --------------------------------------------------------------------------- #
def test_fluid_density_canonicalizes_to_kg_per_m3():
    # notebook: Fluid("Water", density=Q_(1_000_000, "g/m**3")).density -> 1000 kg/m³
    water = Fluid(name="Water", density=Q_(1_000_000, "g/m**3"))
    assert str(water.density.units) == "kilogram / meter ** 3"
    assert water.density.magnitude == pytest.approx(1000.0)


def test_fluid_repr_is_stable():
    water = Fluid(name="Water", density=Q_(1_000_000, "g/m**3"))
    assert repr(water) == "Fluid(name=Water, density=1000.0 kilogram / meter ** 3)"


# --------------------------------------------------------------------------- #
# Contracts the notebook does not show but the code guarantees
# --------------------------------------------------------------------------- #
def test_invalid_context_raises_value_error():
    with pytest.raises(ValueError):
        quantity_factory(Q_(500, "gram"), context="not-a-context")


def test_non_quantity_input_raises_value_error():
    # quantity_factory requires a pint.Quantity (unit_conversion.py).
    with pytest.raises(ValueError):
        quantity_factory(42)


def test_unknown_dimensionality_warns_and_passes_through():
    # Electric current has no entry in STANDARD_UNITS, so the quantity is
    # returned unchanged with a UserWarning rather than raising.
    current = Q_(5, "ampere")
    with pytest.warns(UserWarning):
        result = quantity_factory(current)
    assert result == current


def test_conversion_error_surfaces_as_value_error_not_name_error(monkeypatch):
    # Regression: unit_conversion.py references ``pint.UndefinedUnitError`` /
    # ``pint.DimensionalityError`` in its ``except`` clauses, which requires a
    # module-level ``import pint`` (not just ``from pint import ...``). Without it,
    # any conversion failure raised a ``NameError`` that masked the real error in
    # the foundation layer. Force the ``.to()`` call to raise a pint error and
    # assert the handler surfaces a ``ValueError``, never a ``NameError``.
    import pint
    from pint import Quantity

    def boom(self, *args, **kwargs):
        raise pint.DimensionalityError("gram", "kilogram")

    monkeypatch.setattr(Quantity, "to", boom)
    with pytest.raises(ValueError):
        quantity_factory(Q_(500, "gram"))
