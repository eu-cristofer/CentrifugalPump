"""
nodes.plotting
==============

Shared matplotlib figure builder for the on-canvas charts (UI_SPEC §5.4 preview
and §5.5 Performance Plot): three stacked, shared-x charts Q×H (tallest), Q×P,
Q×η — corrected data points, the degree-3 polynomial, the natural cubic spline
(dashed), and a crosshair at the rated capacity with value labels.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from matplotlib.figure import Figure

HEAD_C = "#2f6fb0"
POWER_C = "#b4413c"
EFF_C = "#2e7d5b"
GRID_C = "#d9e0e8"
MARK_C = "#33414f"


def build_figure(
    fitted,
    rated=None,
    show_poly: bool = True,
    show_spline: bool = True,
    show_points: bool = True,
    ylims: Optional[dict] = None,
    resolution: int = 160,
    compact: bool = False,
) -> Figure:
    ylims = ylims or {}
    fitter = fitted.curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    heads = np.asarray(fitter.heads, dtype=float)
    try:
        powers = np.asarray(fitter.powers, dtype=float)
    except Exception:
        powers = np.array([])
    try:
        effs = np.asarray(fitter.efficiencies, dtype=float)
    except Exception:
        effs = np.array([])

    has_power = powers.size == caps.size and caps.size > 0
    has_eff = effs.size == caps.size and caps.size > 0

    n_axes = 1 + int(has_power) + int(has_eff)
    ratios = [5] + ([3] if has_power else []) + ([4] if has_eff else [])

    fig = Figure(figsize=(5.4, 5.6) if compact else (6.6, 7.2), dpi=100)
    fig.patch.set_facecolor("white")
    axes = fig.subplots(n_axes, 1, sharex=True, gridspec_kw={"height_ratios": ratios})
    if n_axes == 1:
        axes = [axes]

    xs = np.linspace(float(caps.min()), float(caps.max()), resolution) if caps.size else np.array([])
    rated_q = float(rated.q_m3h) if rated is not None else None

    def draw(ax, ydata, coeffs, spline, color, label, unit):
        if show_points and ydata.size:
            ax.scatter(caps, ydata, s=26, color=color, zorder=5, label="data")
        if show_poly and xs.size and len(coeffs):
            ax.plot(xs, np.polyval(coeffs, xs), "-", color=color, lw=1.8, label="poly-3")
        if show_spline and spline is not None and xs.size:
            sx, sy = spline.sample(resolution)
            ax.plot(sx, sy, "--", color=color, lw=1.4, alpha=0.85, label="spline")
        ax.set_ylabel(f"{label} ({unit})", fontsize=8, color="#33414f")
        ax.grid(True, color=GRID_C, lw=0.8)
        ax.tick_params(labelsize=7, colors="#5a6573")
        for spine in ax.spines.values():
            spine.set_color("#c3ccd6")
        if rated_q is not None and len(coeffs):
            yv = float(np.polyval(coeffs, rated_q))
            ax.axvline(rated_q, color=MARK_C, ls=":", lw=1.0, alpha=0.7)
            ax.axhline(yv, color=MARK_C, ls=":", lw=1.0, alpha=0.7)
            ax.plot([rated_q], [yv], "x", color=MARK_C, ms=8, mew=1.6, zorder=6)
            ax.annotate(f"{yv:.1f}", (ax.get_xlim()[0], yv), fontsize=7,
                        va="center", ha="left",
                        bbox=dict(fc="white", ec="#c3ccd6", boxstyle="round,pad=0.2"))
        if not compact:
            ax.legend(fontsize=6.5, loc="best", framealpha=0.9)

    i = 0
    draw(axes[i], heads, fitted.head_coeffs, fitted.head_spline, HEAD_C, "Head", "m")
    if "head" in ylims and ylims["head"]:
        axes[i].set_ylim(ylims["head"])
    if has_power:
        i += 1
        draw(axes[i], powers, fitted.power_coeffs, fitted.power_spline, POWER_C, "Power", "kW")
        axes[i].yaxis.set_label_position("right")
        axes[i].yaxis.tick_right()
        if "power" in ylims and ylims["power"]:
            axes[i].set_ylim(ylims["power"])
    if has_eff:
        i += 1
        draw(axes[i], effs, fitted.efficiency_coeffs, fitted.efficiency_spline, EFF_C, "Efficiency", "%")
        if "efficiency" in ylims and ylims["efficiency"]:
            axes[i].set_ylim(ylims["efficiency"])

    axes[-1].set_xlabel("Capacity  Q (m³/h)", fontsize=8, color="#33414f")
    title = f"{fitted.pump_tag} — performance curve"
    axes[0].set_title(title, fontsize=9.5, color="#28323d", pad=8)
    fig.tight_layout(pad=1.1)
    return fig
