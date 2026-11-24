"""
quantity_io
===========

One serialisation path for Pint quantities: a ``{"value", "unit"}`` pair that
round-trips through JSON.

The unit string is the compact (``~C``) Pint format, e.g. ``"m**3/h"``,
``"kgf/cm**2"``, ``"degC"``, so the stored files stay human readable.

Functions
---------
- to_json: Quantity -> ``{"value": float, "unit": str}``.
- from_json: ``{"value", "unit"}`` (or a bare number plus ``default_unit``) -> Quantity.

Examples
--------
>>> from pump import Q_
>>> from pump.quantity_io import to_json, from_json
>>> d = to_json(Q_(50, "psi"))
>>> d["value"]
50.0
>>> from_json(d).to("psi").magnitude
50.0
"""

from typing import Any, Dict, Optional, Union

from pump.utilities.unit_conversion import Q_

__all__ = ["to_json", "from_json"]


def to_json(q: Q_) -> Dict[str, Any]:
    """
    Serialise a quantity to a JSON-ready ``{"value", "unit"}`` dict.

    Parameters
    ----------
    q : Q_
        The quantity to serialise.

    Returns
    -------
    dict
        ``{"value": float, "unit": str}`` where ``unit`` is the compact Pint
        string of ``q.units``.

    Raises
    ------
    ValueError
        If ``q`` is not a Pint quantity.

    Examples
    --------
    >>> from pump import Q_
    >>> d = to_json(Q_(250, "kW"))
    >>> d["value"], d["unit"]
    (250.0, 'kW')
    """
    if not isinstance(q, Q_):
        raise ValueError("A valid pint.Quantity is required.")
    return {"value": float(q.magnitude), "unit": format(q.units, "~C")}


def from_json(
    d: Union[Dict[str, Any], int, float], default_unit: Optional[str] = None
) -> Q_:
    """
    Rebuild a quantity from :func:`to_json` output.

    Parameters
    ----------
    d : dict or float
        Either ``{"value": ..., "unit": ...}`` or a bare number. A bare number
        (legacy v1 files) needs ``default_unit``. In a dict, a missing
        ``"unit"`` also falls back to ``default_unit``.
    default_unit : str, optional
        Unit applied when ``d`` carries none.

    Returns
    -------
    Q_
        The reconstructed quantity.

    Raises
    ------
    ValueError
        If the input is malformed or no unit can be determined.

    Examples
    --------
    >>> from pump import Q_
    >>> from_json({"value": 12.5, "unit": "mm"}).to("mm").magnitude
    12.5
    >>> from_json(12.5, default_unit="mm").to("mm").magnitude
    12.5
    >>> from_json(12.5)
    Traceback (most recent call last):
        ...
    ValueError: A bare number needs a default_unit.
    """
    if isinstance(d, dict):
        if "value" not in d:
            raise ValueError("Quantity JSON needs a 'value' key.")
        value = d["value"]
        unit = d.get("unit", default_unit)
        if unit is None:
            raise ValueError("Quantity JSON needs a 'unit' (or a default_unit).")
    elif isinstance(d, (int, float)) and not isinstance(d, bool):
        if default_unit is None:
            raise ValueError("A bare number needs a default_unit.")
        value, unit = d, default_unit
    else:
        raise ValueError(f"Cannot build a quantity from {d!r}.")
    return Q_(float(value), unit)
