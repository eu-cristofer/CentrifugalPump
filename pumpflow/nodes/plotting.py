"""
nodes.plotting
==============

Shared matplotlib figure builder for the on-canvas charts (UI_SPEC §5.4 preview
and §5.5 Performance Plot): three stacked, shared-x charts Q×H (tallest), Q×P,
Q×η — corrected data points, the degree-3 polynomial, the natural cubic spline
(dashed), and a crosshair at the rated capacity with value labels.  With an
NPSH result a fourth chart Q×NPSHr is added: the NPSH3 test points, their fit
over the tested range, NPSHa as a horizontal line and the quoted NPSHr at rated
flow.

The returned figure carries ``fig.pump_axes`` (``{"head": ax, "power": ax,
"efficiency": ax, "npsh": ax}``, only those drawn) and ``fig.pump_readout(q)``,
the fitted values at a flow, for the interactive dialog.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from matplotlib.figure import Figure

from pump import Q_ as _Q
from pump.design import color as token_color

HEAD_C = token_color("chart-head")
POWER_C = token_color("chart-power")
EFF_C = token_color("chart-efficiency")
NPSH_C = token_color("chart-npsh")
NPSHA_C = token_color("chart-npsha")
GRID_C = token_color("chart-grid")
MARK_C = token_color("chart-ink")
TICK_C = token_color("chart-tick")
FRAME_C = token_color("chart-frame")
TITLE_C = token_color("chart-title")


def build_figure(
    fitted,
    rated=None,
    show_poly: bool = True,
    show_spline: bool = True,
    show_points: bool = True,
    ylims: Optional[dict] = None,
    resolution: int = 160,
    compact: bool = False,
    npsh=None,
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

    npsh_curve = getattr(npsh, "curve", None)
    npsh_res = getattr(npsh, "result", None)
    has_npsh = npsh_curve is not None
    n_axes = 1 + int(has_power) + int(has_eff) + int(has_npsh)
    ratios = (
        [5]
        + ([3] if has_power else [])
        + ([4] if has_eff else [])
        + ([3] if has_npsh else [])
    )

    height = 7.2 + (1.8 if has_npsh else 0.0)
    fig = Figure(figsize=(5.4, 5.6) if compact else (6.6, height), dpi=100)
    fig.patch.set_facecolor("white")
    axes = fig.subplots(n_axes, 1, sharex=True, gridspec_kw={"height_ratios": ratios})
    if n_axes == 1:
        axes = [axes]

    xs = np.linspace(float(caps.min()), float(caps.max()), resolution) if caps.size else np.array([])
    rated_q = float(rated.q.to("m**3/h").magnitude) if rated is not None else None

    def draw(ax, ydata, coeffs, spline, color, label, unit):
        if show_points and ydata.size:
            ax.scatter(caps, ydata, s=26, color=color, zorder=5, label="data")
        if show_poly and xs.size and len(coeffs):
            ax.plot(xs, np.polyval(coeffs, xs), "-", color=color, lw=1.8, label="poly-3")
        if show_spline and spline is not None and xs.size:
            sx, sy = spline.sample(resolution)
            ax.plot(sx, sy, "--", color=color, lw=1.4, alpha=0.85, label="spline")
        ax.set_ylabel(f"{label} ({unit})", fontsize=8, color=MARK_C)
        ax.grid(True, color=GRID_C, lw=0.8)
        ax.tick_params(labelsize=7, colors=TICK_C)
        for spine in ax.spines.values():
            spine.set_color(FRAME_C)
        if rated_q is not None and len(coeffs):
            yv = float(np.polyval(coeffs, rated_q))
            ax.axvline(rated_q, color=MARK_C, ls=":", lw=1.0, alpha=0.7)
            ax.axhline(yv, color=MARK_C, ls=":", lw=1.0, alpha=0.7)
            ax.plot([rated_q], [yv], "x", color=MARK_C, ms=8, mew=1.6, zorder=6)
            ax.annotate(f"{yv:.1f}", (ax.get_xlim()[0], yv), fontsize=7,
                        va="center", ha="left",
                        bbox=dict(fc="white", ec=FRAME_C, boxstyle="round,pad=0.2"))
        if not compact:
            ax.legend(fontsize=6.5, loc="best", framealpha=0.9)

    named = {}
    i = 0
    named["head"] = axes[i]
    draw(axes[i], heads, fitted.head_coeffs, fitted.head_spline, HEAD_C, "Head", "m")
    if "head" in ylims and ylims["head"]:
        axes[i].set_ylim(ylims["head"])
    if has_power:
        i += 1
        named["power"] = axes[i]
        draw(axes[i], powers, fitted.power_coeffs, fitted.power_spline, POWER_C, "Power", "kW")
        axes[i].yaxis.set_label_position("right")
        axes[i].yaxis.tick_right()
        if "power" in ylims and ylims["power"]:
            axes[i].set_ylim(ylims["power"])
    if has_eff:
        i += 1
        named["efficiency"] = axes[i]
        draw(axes[i], effs, fitted.efficiency_coeffs, fitted.efficiency_spline, EFF_C, "Efficiency", "%")
        if "efficiency" in ylims and ylims["efficiency"]:
            axes[i].set_ylim(ylims["efficiency"])

    npsh_fit = None
    if has_npsh:
        i += 1
        ax = named["npsh"] = axes[i]
        nq = np.asarray([float(q.to("m**3/h").magnitude) for q in npsh_curve.q])
        nv = np.asarray([float(v.to("m").magnitude) for v in npsh_curve.npshr])
        lo_q, hi_q = float(nq.min()), float(nq.max())

        def npsh_fit(q):  # fitted NPSHr (m), tested range only
            if q < lo_q or q > hi_q:
                return None
            return float(npsh_curve(_Q(q, "m**3/h")).to("m").magnitude)

        if show_points:
            ax.scatter(nq, nv, s=26, color=NPSH_C, zorder=5, label="NPSH3 data")
        grid = np.linspace(lo_q, hi_q, resolution)
        ax.plot(grid, [npsh_fit(x) for x in grid], "-", color=NPSH_C, lw=1.8,
                label="NPSHr fit")
        if npsh_res is not None and getattr(npsh_res, "npsha", None) is not None:
            a = float(npsh_res.npsha.to("m").magnitude)
            ax.axhline(a, color=NPSHA_C, lw=1.4, ls="-.", label=f"NPSHa {a:.2f} m")
        quoted = getattr(npsh_res, "npshr_quoted", None)
        if quoted is not None and rated_q is not None:
            ax.plot([rated_q], [float(quoted.to("m").magnitude)], "D", ms=6,
                    mfc="white", mec=NPSH_C, mew=1.4, zorder=6, label="quoted NPSHr")
        if rated_q is not None:
            ax.axvline(rated_q, color=MARK_C, ls=":", lw=1.0, alpha=0.7)
            yv = npsh_fit(rated_q)
            if yv is not None:
                ax.plot([rated_q], [yv], "x", color=MARK_C, ms=8, mew=1.6, zorder=6)
        ax.set_ylabel("NPSHr (m)", fontsize=8, color=MARK_C)
        ax.grid(True, color=GRID_C, lw=0.8)
        ax.tick_params(labelsize=7, colors=TICK_C)
        for spine in ax.spines.values():
            spine.set_color(FRAME_C)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        if not compact:
            ax.legend(fontsize=6.5, loc="best", framealpha=0.9)
        if ylims.get("npsh"):
            ax.set_ylim(ylims["npsh"])

    axes[-1].set_xlabel("Capacity  Q (m³/h)", fontsize=8, color=MARK_C)
    service_prefix = f"{rated.service} — " if rated is not None and rated.service else ""
    title = f"{service_prefix}{fitted.pump_tag} — performance curve"
    axes[0].set_title(title, fontsize=9.5, color=TITLE_C, pad=8)
    fig.tight_layout(pad=1.1)

    q_lo = float(caps.min()) if caps.size else 0.0
    q_hi = float(caps.max()) if caps.size else 0.0

    def readout(q: float) -> dict:
        """Fitted values at flow ``q`` (m³/h), canonical units; tested range only."""
        out = {}
        if caps.size and q_lo <= q <= q_hi:
            out["head"] = float(np.polyval(fitted.head_coeffs, q))
            if has_power:
                out["power"] = float(np.polyval(fitted.power_coeffs, q))
            if has_eff:
                out["efficiency"] = float(np.polyval(fitted.efficiency_coeffs, q))
        if npsh_fit is not None:
            v = npsh_fit(q)
            if v is not None:
                out["npsh"] = v
        return out

    fig.pump_axes = named  # type: ignore[attr-defined]
    fig.pump_readout = readout  # type: ignore[attr-defined]
    return fig
