"""
compare
=======

Side-by-side comparison of several fitted :class:`~pump.PerformanceCurve`
objects (e.g. twin pumps A and B tested for the same service).

The **first** curve is the reference: every other curve is reported with a
relative delta ``(x - ref) / ref`` for head, power and efficiency.

Classes / functions
-------------------
- ComparisonRow: predictions (and deltas vs the reference) at one capacity.
- ComparisonTable: all rows for the compared curves, with ``as_text()``.
- compare_curves: build a :class:`ComparisonTable` from named curves.
- plot_comparison: overlay of H, P and efficiency vs capacity (PNG stream).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

from .design import color as _token_color
from .performance_curve import PerformanceCurve
from .utilities.unit_conversion import Q_

__all__ = ["ComparisonRow", "ComparisonTable", "compare_curves", "plot_comparison"]

_METRICS = ("head", "power", "efficiency")
_COLORS = [
    _token_color(n)
    for n in (
        "chart-head",
        "chart-power",
        "chart-efficiency",
        "chart-series-4",
        "chart-series-5",
        "chart-series-6",
    )
]


@dataclass(frozen=True)
class ComparisonRow:
    """Predictions of every curve at one capacity.

    Attributes
    ----------
    q : Q_
        The capacity the curves were evaluated at.
    values : Mapping[str, Mapping[str, Q_]]
        ``tag -> {"head": m, "power": kW, "efficiency": percent}``.
    deltas : Mapping[str, Mapping[str, float]]
        ``tag -> {"head", "power", "efficiency"}`` relative deltas
        ``(x - ref) / ref`` against the first curve (which is omitted).
    """

    q: Q_
    values: Mapping[str, Mapping[str, Q_]]
    deltas: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ComparisonTable:
    """Rows of a comparison; ``tags[0]`` is the reference curve."""

    tags: tuple
    rows: tuple

    def as_text(self) -> str:
        """A ``tabulate`` grid: one line per (capacity, tag)."""
        headers = [
            "Q [m³/h]",
            "Tag",
            "H [m]",
            "P [kW]",
            "η [%]",
            "ΔH [%]",
            "ΔP [%]",
            "Δη [%]",
        ]

        def pct(value) -> str:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return "-"
            return f"{value * 100.0:+0.2f}"

        lines = []
        for row in self.rows:
            q = float(row.q.to("m**3/h").magnitude)
            for tag in self.tags:
                vals = row.values[tag]
                d = row.deltas.get(tag)
                lines.append(
                    [
                        f"{q:0.1f}",
                        tag,
                        f"{vals['head'].magnitude:0.2f}",
                        f"{vals['power'].magnitude:0.2f}",
                        f"{vals['efficiency'].magnitude:0.2f}",
                        pct(d["head"]) if d else "-",
                        pct(d["power"]) if d else "-",
                        pct(d["efficiency"]) if d else "-",
                    ]
                )
        return tabulate(lines, headers=headers, tablefmt="grid")


def _rel(value: Q_, ref: Q_) -> float:
    """Relative delta ``(value - ref) / ref`` (NaN when the reference is zero)."""
    r = float(ref.magnitude)
    if r == 0.0:
        return float("nan")
    return (float(value.magnitude) - r) / r


def compare_curves(
    curves: Mapping[str, PerformanceCurve], at: Sequence[Q_]
) -> ComparisonTable:
    """
    Compare fitted curves at the given capacities.

    Parameters
    ----------
    curves : Mapping[str, PerformanceCurve]
        ``tag -> curve``; the first entry is the reference. At least two are
        required.
    at : Sequence[Q_]
        Capacities to evaluate (Pint quantities).

    Returns
    -------
    ComparisonTable
        Head (m), power (kW) and efficiency (percent) predictions per tag, plus
        the relative deltas against the first curve.

    Raises
    ------
    ValueError
        With fewer than two curves.
    """
    if len(curves) < 2:
        raise ValueError("compare_curves needs at least two curves.")
    tags = tuple(curves)
    ref = tags[0]
    rows = []
    for q in at:
        values = {}
        for tag, curve in curves.items():
            values[tag] = {
                "head": curve.predict_head(q).to("m"),
                "power": curve.predict_breaking_power(q).to("kW"),
                "efficiency": curve.predict_efficiency(q).to("percent"),
            }
        deltas = {
            tag: {m: _rel(values[tag][m], values[ref][m]) for m in _METRICS}
            for tag in tags[1:]
        }
        rows.append(ComparisonRow(q=q, values=values, deltas=deltas))
    return ComparisonTable(tags=tags, rows=tuple(rows))


def plot_comparison(
    curves: Mapping[str, PerformanceCurve],
    rated_q: Optional[Q_] = None,
    return_io: bool = True,
):
    """
    Overlay head, power and efficiency of several curves (three stacked panels).

    Each tag gets one colour: measured points as markers plus the fitted curve
    sampled across that curve's capacity range. ``rated_q`` adds a dashed
    vertical line on every panel.

    Returns a ``BytesIO`` PNG when ``return_io`` is true, otherwise shows the
    figure.
    """
    fig, axes = plt.subplots(
        3, 1, sharex=True, figsize=(8, 8), gridspec_kw={"height_ratios": [5, 3, 4]}
    )
    ax_h, ax_p, ax_e = axes

    for i, (tag, curve) in enumerate(curves.items()):
        color = _COLORS[i % len(_COLORS)]
        fitter = curve.fitter
        caps = np.array([p.capacity.to("m**3/h").magnitude for p in curve.points])
        heads = np.array([p.head.to("m").magnitude for p in curve.points])
        powers = np.array([p.breaking_power.to("kW").magnitude for p in curve.points])
        effs = np.array([p.efficiency.to("percent").magnitude for p in curve.points])
        smooth = np.linspace(float(caps.min()), float(caps.max()), 100)

        ax_h.scatter(caps, heads, color=color, marker="o")
        ax_h.plot(
            smooth, np.polyval(fitter.head_coeffs, smooth), color=color, label=tag
        )
        ax_p.scatter(caps, powers, color=color, marker="o")
        ax_p.plot(
            smooth, np.polyval(fitter.power_coeffs, smooth), color=color, label=tag
        )
        ax_e.scatter(caps, effs, color=color, marker="o")
        ax_e.plot(
            smooth, np.polyval(fitter.efficiency_coeffs, smooth), color=color, label=tag
        )

    ax_h.set_ylabel("Head (m)")
    ax_h.set_title("Pump comparison")
    ax_p.set_ylabel("Power (kW)")
    ax_p.yaxis.set_label_position("right")
    ax_p.yaxis.tick_right()
    ax_e.set_ylabel("Efficiency (%)")
    ax_e.set_xlabel("Capacity (m³/h)")
    for ax in axes:
        ax.grid()
        if rated_q is not None:
            ax.axvline(
                float(rated_q.to("m**3/h").magnitude), color="gray", linestyle="dashed"
            )
    ax_h.legend()

    plt.tight_layout()

    if return_io:
        image_stream = io.BytesIO()
        from pump.utilities.numbers import localize_axes

        localize_axes(fig)
        fig.savefig(image_stream, format="png")
        plt.close(fig)
        image_stream.seek(0)
        return image_stream
    plt.show()
