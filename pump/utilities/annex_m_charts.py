"""
pump.utilities.annex_m_charts
=============================

Test charts drawn in the style of API 610 Annex M:

- :func:`plot_annex_m_curve`: the **test curve format** (11th/12th ed.
  Figures M.2/M.3).  One dotted grid, one flow axis, and each quantity on its
  own scale in its own height band: head (Y1, upper left), efficiency (Y2,
  lower left), power (Y3, right, middle) and NPSH3 (Y4, right, bottom).  It
  has numbered curve callouts, the preferred (a) and allowable (b) operating
  region arrows, a header block (pump, liquid, rated point), the impeller
  diameter box and the date box.
- :func:`plot_test_points_vibration`: the **test points on a typical
  performance curve** (Figure M.4).  It shows the head curve with every
  tested point, the region limits hatched, and vibration against flow under
  the basic limit (preferred region) and the raised limit (outside it).

Both draw only what they are given.  The curves span the tested flow range and
are never extrapolated.  The allowable region is drawn only when it is passed;
otherwise the chart says so.  Both return PNG bytes.

Examples
--------
>>> _nice_range([2.1, 3.8])
(2.0, 4.0, [2.0, 2.5, 3.0, 3.5, 4.0])
>>> _nice_range([0.0, 87.0])[:2]
(0.0, 100.0)
"""

from __future__ import annotations

import io
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from ..design import color
from .unit_conversion import Q_

__all__ = ["plot_annex_m_curve", "plot_test_points_vibration"]

Translate = Callable[[str], str]

_INK = color("print-ink")
_GRID_MAJOR = color("print-grid-major")
_GRID_MINOR = color("print-grid-minor")
_ACCENT = color("print-measured")  # the measured vibration (Figure M.4 "6")
_LIMIT = color("print-limit")  # vibration limits


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _nice_range(values: Sequence[float], nbins: int = 5) -> tuple:
    """``(low, high, ticks)``: round tick limits that enclose ``values``."""
    from matplotlib.ticker import MaxNLocator

    lo, hi = float(min(values)), float(max(values))
    if hi - lo < 1e-12:
        hi = lo + (abs(lo) * 0.1 or 1.0)
    ticks = MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10]).tick_values(lo, hi)
    ticks = [float(round(t, 10)) for t in ticks if t >= lo - 1e-9 * (hi - lo) - 1e-12]
    ticks = ticks or [lo]
    while ticks[0] > lo + 1e-12:  # the locator may start above lo
        step = (ticks[1] - ticks[0]) if len(ticks) > 1 else 1.0
        ticks.insert(0, ticks[0] - step)
    while ticks[-1] < hi - 1e-12:
        step = (ticks[-1] - ticks[-2]) if len(ticks) > 1 else 1.0
        ticks.append(ticks[-1] + step)
    return ticks[0], ticks[-1], ticks


def _band_axis(host, side: str, band: tuple, ticks: list, tag: str, unit_label: str):
    """A twin y-axis whose scale fills only ``band`` (fractions of the height).

    The spine is drawn only over the band and offset outward, as on the
    printed form; ``tag`` (Y1, Y2...) is written beside the band.
    """
    b0, b1 = band
    t0, t1 = ticks[0], ticks[-1]
    span = (t1 - t0) / (b1 - b0)
    ax = host.twinx()
    ax.set_ylim(t0 - b0 * span, t0 + (1.0 - b0) * span)
    ax.set_yticks(ticks)
    from matplotlib.ticker import NullLocator

    ax.yaxis.set_minor_locator(NullLocator())
    for spine in ax.spines.values():
        spine.set_visible(False)
    sp = ax.spines[side]
    sp.set_visible(True)
    sp.set_bounds(t0, t1)
    sp.set_position(("outward", 8))
    sp.set_linewidth(1.1)
    sp.set_color(_INK)
    if side == "left":
        ax.yaxis.tick_left()
        ax.yaxis.set_label_position("left")
    else:
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
    ax.tick_params(axis="y", labelsize=7, direction="out", length=3, colors=_INK)
    # The tag (Y1, Y2...) beside the band; units are in the key.
    ha = "right" if side == "left" else "left"
    host.text(
        -0.085 if side == "left" else 1.085,
        (b0 + b1) / 2,
        tag,
        transform=host.transAxes,
        ha=ha,
        va="center",
        fontsize=10,
        fontweight="bold",
        color=_INK,
    )
    return ax


def _host(fig, rect, q_max: float):
    """The framed, dotted-grid plotting area; its own y axis is a hidden 0..1."""
    from matplotlib.ticker import AutoMinorLocator, MultipleLocator

    host = fig.add_axes(rect)
    host.set_xlim(0.0, q_max)
    host.set_ylim(0.0, 1.0)
    host.yaxis.set_major_locator(MultipleLocator(0.1))
    host.yaxis.set_minor_locator(MultipleLocator(0.02))
    host.xaxis.set_minor_locator(AutoMinorLocator(5))
    host.tick_params(
        axis="y", which="both", left=False, right=False, labelleft=False, length=0
    )
    host.tick_params(axis="x", labelsize=7, direction="out", colors=_INK)
    host.grid(which="major", ls=":", lw=0.7, color=_GRID_MAJOR)
    host.grid(which="minor", ls=":", lw=0.4, color=_GRID_MINOR)
    for spine in host.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color(_INK)
    return host


def _callout(ax, x: float, y: float, number: str, dx: float = 18, dy: float = 16):
    """A numbered leader to a curve (the figure's 1, 2, 3, 4)."""
    ax.annotate(
        number,
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9,
        fontweight="bold",
        color=_INK,
        ha="center",
        va="center",
        arrowprops=dict(arrowstyle="-|>", lw=0.9, color=_INK, shrinkA=4, shrinkB=1),
    )


def _dimension(host, lo: float, hi: float, y: float, text: str):
    """A double-headed dimension arrow between two flows at height ``y``."""
    host.annotate(
        "",
        xy=(lo, y),
        xytext=(hi, y),
        xycoords="data",
        arrowprops=dict(arrowstyle="<|-|>", lw=0.9, color=_INK, shrinkA=0, shrinkB=0),
    )
    for x in (lo, hi):
        host.plot([x, x], [y - 0.025, y + 0.025], color=_INK, lw=0.9)
    host.text(
        (lo + hi) / 2,
        y + 0.012,
        text,
        ha="center",
        va="bottom",
        fontsize=8,
        style="italic",
        color=_INK,
    )


def _arrow_x(host):
    """The arrowhead at the end of the flow axis."""
    host.annotate(
        "",
        xy=(1.035, 0.0),
        xytext=(1.0, 0.0),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", lw=0.9, color=_INK, shrinkA=0, shrinkB=0),
        annotation_clip=False,
    )


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    return buf.getvalue()


def _m3h(q) -> float:
    return float(q.to("m**3/h").magnitude)


def _fmt(value, digits: int = 1) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    return f"{float(value):,.{digits}f}"


# --------------------------------------------------------------------------- #
# Figure M.3: the test curve format
# --------------------------------------------------------------------------- #
def plot_annex_m_curve(
    curve,
    rated: Mapping,
    por: Optional[tuple] = None,
    aor: Optional[tuple] = None,
    npsh_curve=None,
    header: Optional[Mapping] = None,
    impeller: Optional[Mapping] = None,
    date: str = "",
    head_band: Optional[tuple] = None,
    translate: Translate = lambda t: t,
) -> bytes:
    """
    The test curve in the format of API 610 Figure M.3, as PNG bytes.

    Parameters
    ----------
    curve : PerformanceCurve
        The corrected, fitted curve (flow in m³/h).
    rated : mapping
        ``{"q", "head", "power", "npsh3", "efficiency"}`` as ``Q_`` or
        ``None``.  The rated point is marked on each curve and listed in the
        header.
    por, aor : (Q_, Q_), optional
        Preferred and allowable operating regions.  Each is drawn only when
        given.
    npsh_curve : pump.npsh.NPSHrCurve, optional
        NPSH3 test points and their fit.  Without it there is no Y4 band.
    header : mapping, optional
        Left and middle header fields: ``serial``, ``size_type``, ``stages``,
        ``speed``, ``impeller_no``, ``liquid``, ``density``, ``temperature``,
        ``viscosity``, ``eye_area`` and ``curve_no``.  Missing fields stay as
        blank lines.
    impeller : mapping, optional
        ``{"max", "rated", "min"}`` impeller diameters (``Q_``).
    date : str
        Test date for the date box.
    head_band : (float, float), optional
        Rated-head tolerance ``(minus, plus)`` as fractions.  When given, it
        is drawn as a bar at the rated point.
    """
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle

    _ = translate
    hdr = dict(header or {})
    fitter = curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    heads = np.asarray(fitter.heads, dtype=float)
    q_rated = _m3h(rated["q"])
    q_hi = max(float(caps.max()), q_rated)
    if aor is not None:
        q_hi = max(q_hi, _m3h(aor[1]))
    q_max = _nice_range([0.0, q_hi * 1.04], nbins=6)[1]
    qs = np.linspace(float(caps.min()), float(caps.max()), 240)

    fig = Figure(figsize=(7.4, 10.0))
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    renderer = FigureCanvasAgg(fig).get_renderer()  # to measure label widths

    def width_in(ax, text_artist) -> float:
        """Width of a text artist as a fraction of ``ax``'s width."""
        return text_artist.get_window_extent(renderer).width / ax.bbox.width

    host = _host(fig, (0.15, 0.19, 0.70, 0.61), q_max)

    # -- Y1 head (upper left) ---------------------------------------------- #
    h_fit = np.polyval(fitter.head_coeffs, qs)
    h_vals = list(h_fit) + list(heads) + [float(rated["head"].to("m").magnitude)]
    if head_band:
        h_r = float(rated["head"].to("m").magnitude)
        h_vals += [h_r * (1 + head_band[0]), h_r * (1 + head_band[1])]
    ax_h = _band_axis(
        host, "left", (0.64, 0.97), _nice_range(h_vals)[2], "Y1", _("Head") + " (m)"
    )
    ax_h.plot(qs, h_fit, color=_INK, lw=2.2, solid_capstyle="round")
    ax_h.plot(caps, heads, "x", color=_INK, ms=4, mew=0.9)

    # -- Y2 efficiency (lower left) ---------------------------------------- #
    ax_e = None
    try:
        effs = np.asarray(fitter.efficiencies, dtype=float)
        scale = 100.0 if np.nanmax(effs) <= 1.5 else 1.0
        e_fit = np.clip(np.polyval(fitter.efficiency_coeffs, qs) * scale, 0, None)
        ax_e = _band_axis(
            host,
            "left",
            (0.0, 0.56),
            _nice_range([0.0, float(np.nanmax(e_fit)), float(np.nanmax(effs * scale))])[
                2
            ],
            "Y2",
            _("Efficiency") + " (%)",
        )
        ax_e.plot(qs, e_fit, color=_INK, lw=2.2, solid_capstyle="round")
        ax_e.plot(caps, effs * scale, "x", color=_INK, ms=4, mew=0.9)
    except Exception:  # no efficiency data: no Y2 band
        effs = None

    # -- Y3 power (right, middle) ------------------------------------------ #
    ax_p = None
    try:
        p_fit = np.polyval(fitter.power_coeffs, qs)
        powers = np.asarray(fitter.powers, dtype=float)
        p_vals = list(p_fit) + list(powers)
        if rated.get("power") is not None:
            p_vals.append(float(rated["power"].to("kW").magnitude))
        ax_p = _band_axis(
            host, "right", (0.40, 0.60), _nice_range(p_vals, 4)[2], "Y3", "kW"
        )
        ax_p.plot(qs, p_fit, color=_INK, lw=2.2, solid_capstyle="round")
        ax_p.plot(caps, powers, "x", color=_INK, ms=4, mew=0.9)
    except Exception:
        pass

    # -- Y4 NPSH3 (right, bottom) ------------------------------------------ #
    ax_n = None
    if npsh_curve is not None:
        nq = np.asarray([_m3h(q) for q in npsh_curve.q])
        nv = np.asarray([float(n.to("m").magnitude) for n in npsh_curve.npshr])
        grid = np.linspace(float(nq.min()), float(nq.max()), 120)
        n_fit = np.asarray(
            [float(npsh_curve(Q_(x, "m**3/h")).to("m").magnitude) for x in grid]
        )
        n_vals = [0.0] + list(n_fit) + list(nv)
        if rated.get("npsh3") is not None:
            n_vals.append(float(rated["npsh3"].to("m").magnitude))
        ax_n = _band_axis(
            host, "right", (0.0, 0.24), _nice_range(n_vals, 4)[2], "Y4", "m"
        )
        ax_n.plot(grid, n_fit, color=_INK, lw=2.2, solid_capstyle="round")
        ax_n.plot(nq, nv, "x", color=_INK, ms=4, mew=0.9)

    # -- rated point markers (the form's tolerance symbol) ------------------ #
    def rated_mark(ax, value, unit, band=None):
        if ax is None or value is None:
            return
        y = float(value.to(unit).magnitude)
        if band:
            ax.plot(
                [q_rated, q_rated],
                [y * (1 + band[0]), y * (1 + band[1])],
                color=_INK,
                lw=1.4,
            )
            for f in band:
                ax.plot(
                    [q_rated - q_max * 0.008, q_rated + q_max * 0.008],
                    [y * (1 + f)] * 2,
                    color=_INK,
                    lw=1.1,
                )
        ax.plot(
            [q_rated],
            [y],
            marker="<",
            ms=7,
            mfc="white",
            mec=_INK,
            mew=1.2,
            zorder=5,
        )

    rated_mark(ax_h, rated.get("head"), "m", head_band)
    rated_mark(ax_p, rated.get("power"), "kW")
    if ax_e is not None and rated.get("efficiency") is not None:
        rated_mark(ax_e, rated["efficiency"], "percent")
    rated_mark(ax_n, rated.get("npsh3"), "m")
    host.axvline(q_rated, color=_INK, lw=0.6, ls=(0, (6, 3)))

    # -- numbered callouts -------------------------------------------------- #
    def callout(ax, x_frac, fn, number, dx, dy):
        if ax is None:
            return
        x = float(caps.min() + x_frac * (caps.max() - caps.min()))
        _callout(ax, x, float(fn(x)), number, dx, dy)

    callout(ax_h, 0.38, lambda x: np.polyval(fitter.head_coeffs, x), "1", 16, 18)
    if ax_p is not None:
        callout(ax_p, 0.25, lambda x: np.polyval(fitter.power_coeffs, x), "2", -14, 18)
    if ax_e is not None and effs is not None:
        scale = 100.0 if np.nanmax(effs) <= 1.5 else 1.0
        callout(
            ax_e,
            0.45,
            lambda x: max(np.polyval(fitter.efficiency_coeffs, x) * scale, 0),
            "3",
            18,
            -20,
        )
    if ax_n is not None:
        mid = float(np.median(nq))
        _callout(
            ax_n,
            mid,
            float(npsh_curve(Q_(mid, "m**3/h")).to("m").magnitude),
            "4",
            14,
            18,
        )

    # -- operating regions a / b (between the head and power bands) -------- #
    if por is not None:
        lo, hi = (_m3h(p) for p in por)
        _dimension(host, lo, hi, 0.615, "a")
        for x in (lo, hi):
            host.plot([x, x], [0.615, 0.66], color=_INK, lw=0.6, ls=":")
    if aor is not None:
        lo, hi = (_m3h(p) for p in aor)
        _dimension(host, lo, hi, 0.585, "b")

    # -- impeller diameter box (inside, upper right) ------------------------ #
    imp = dict(impeller or {})
    rows = [
        (_("Max."), imp.get("max")),
        (_("As rated"), imp.get("rated")),
        (_("Min."), imp.get("min")),
    ]
    bx, by, bw, bh = 0.02, 0.655, 0.25, 0.18  # lower left of the head band
    title_txt = host.text(
        bx + 0.015,
        by + bh - 0.03,
        _("Impeller diameter"),
        transform=host.transAxes,
        fontsize=7.5,
        fontweight="bold",
        va="center",
        zorder=7,
    )
    bw = max(bw, width_in(host, title_txt) + 0.03)
    host.add_patch(
        Rectangle(
            (bx, by),
            bw,
            bh,
            transform=host.transAxes,
            fc="white",
            ec=_INK,
            lw=0.9,
            zorder=6,
        )
    )
    for k, (label, value) in enumerate(rows):
        y = by + bh - 0.075 - k * 0.04
        text = "" if value is None else f"{float(value.to('mm').magnitude):.1f} mm"
        host.text(
            bx + 0.015,
            y,
            label,
            transform=host.transAxes,
            fontsize=7,
            va="center",
            zorder=7,
        )
        host.plot(
            [bx + 0.11, bx + bw - 0.015],
            [y - 0.012] * 2,
            transform=host.transAxes,
            color=_INK,
            lw=0.6,
            zorder=7,
        )
        host.text(
            bx + bw - 0.02,
            y,
            text,
            transform=host.transAxes,
            fontsize=7,
            va="center",
            ha="right",
            zorder=7,
        )

    # -- x axis, arrows, date box ------------------------------------------- #
    host.set_xlabel("")
    host.text(
        1.04,
        -0.035,
        "X",
        transform=host.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="top",
    )
    _arrow_x(host)
    date_ax = fig.add_axes((0.69, 0.142, 0.16, 0.024))
    date_ax.set_xticks([])
    date_ax.set_yticks([])
    for s in date_ax.spines.values():
        s.set_linewidth(0.8)
    date_ax.text(0.04, 0.5, _("Date") + f"  {date}", fontsize=7, va="center")

    # -- header block -------------------------------------------------------- #
    head_ax = fig.add_axes((0.06, 0.825, 0.88, 0.155))
    head_ax.set_xlim(0, 1)
    head_ax.set_ylim(0, 1)
    head_ax.axis("off")
    head_ax.add_patch(Rectangle((0.66, 0.0), 0.34, 1.0, fill=False, ec=_INK, lw=0.9))

    def field(x, y, label, value, width=0.30, line_from=0.13):
        t = head_ax.text(x, y, label, fontsize=7, va="bottom")
        line_from = max(line_from, width_in(head_ax, t) + 0.01)
        head_ax.plot([x + line_from, x + width], [y - 0.01] * 2, color=_INK, lw=0.6)
        if value not in (None, ""):
            text = str(value)
            room = max(int((width - line_from) * 140), 4)  # characters that fit
            if len(text) > room:
                text = text[: max(room - 1, 1)] + "…"
            head_ax.text(
                x + line_from + 0.005,
                y + 0.005,
                text,
                fontsize=6.6,
                va="bottom",
                color=color("print-text"),
            )

    left = [
        (_("Pump serial no."), hdr.get("serial")),
        (_("Size and type"), hdr.get("size_type")),
        (_("No. of stages"), hdr.get("stages")),
        (_("Speed, r/min"), hdr.get("speed")),
        (_("Impeller no."), hdr.get("impeller_no")),
    ]
    middle = [
        (_("Pumped liquid"), hdr.get("liquid")),
        (_("Relative density"), hdr.get("density")),
        (_("Temperature") + ", °C", hdr.get("temperature")),
        (_("Kinematic viscosity") + ", mm²/s", hdr.get("viscosity")),
        (_("Impeller eye area") + ", mm²", hdr.get("eye_area")),
    ]
    for k, (label, value) in enumerate(left):
        field(0.0, 0.80 - k * 0.19, label, value, width=0.30)
    for k, (label, value) in enumerate(middle):
        field(0.33, 0.80 - k * 0.19, label, value, width=0.64 - 0.33, line_from=0.205)

    head_ax.text(
        0.675,
        0.87,
        _("Curve No.") + f"  {hdr.get('curve_no') or ''}",
        fontsize=7.5,
        fontweight="bold",
        va="center",
    )
    head_ax.text(0.985, 0.72, _("Rated point"), fontsize=7.5, ha="right", va="center")
    eff = rated.get("efficiency")
    rated_rows = [
        (_("Flowrate"), "m³/h =", rated.get("q"), "m**3/h", 1),
        (_("Head"), "m =", rated.get("head"), "m", 1),
        ("NPSH3", "m =", rated.get("npsh3"), "m", 2),
        (_("Power"), "kW =", rated.get("power"), "kW", 1),
        (_("Calculated efficiency") + " %:", "", eff, "percent", 1),
    ]
    for k, (label, unit, value, to, digits) in enumerate(rated_rows):
        y = 0.60 - k * 0.125
        head_ax.text(0.675, y, label, fontsize=7, va="center")
        head_ax.text(0.885, y, unit, fontsize=7, va="center", ha="right")
        head_ax.text(
            0.985,
            y,
            "" if value is None else _fmt(value.to(to).magnitude, digits),
            fontsize=7,
            va="center",
            ha="right",
        )

    # -- key ----------------------------------------------------------------- #
    key_left = [
        "X   " + _("flowrate, expressed in cubic metres per hour"),
        "Y1  " + _("head, expressed in metres"),
        "Y2  " + _("efficiency, expressed in percentage"),
        "Y3  " + _("power, expressed in kilowatts"),
    ]
    if ax_n is not None:
        key_left.append("Y4  " + "NPSH3, " + _("expressed in metres"))
    key_right = ["1  " + _("head"), "2  " + _("power"), "3  " + _("efficiency")]
    if ax_n is not None:
        key_right.append("4  NPSH3")
    if por is not None:
        key_right.append("a  " + _("Preferred operating region"))
    if aor is not None:
        key_right.append("b  " + _("Allowable operating region"))
    else:
        key_right.append(_("Allowable operating region: not in the project"))
    fig.text(0.06, 0.112, _("Key"), fontsize=8, fontweight="bold", va="top")
    for k, line in enumerate(key_left):
        fig.text(0.06, 0.092 - k * 0.0125, line, fontsize=6.6, va="top")
    for k, line in enumerate(key_right):
        fig.text(0.56, 0.092 - k * 0.0125, line, fontsize=6.6, va="top")
    fig.text(
        0.94,
        0.128,
        "×  " + _("test point") + "    ◁  " + _("rated point"),
        fontsize=6.6,
        ha="right",
        va="top",
    )
    return _png(fig)


# --------------------------------------------------------------------------- #
# Figure M.4: test points and vibration against flow
# --------------------------------------------------------------------------- #
def _hatch_limit(host, x: float, y0: float, y1: float, side: int, q_span: float):
    """A region limit drawn as on the form: a line with short diagonal hatching
    on the outside (``side`` = -1 left, +1 right)."""
    host.plot([x, x], [y0, y1], color=_INK, lw=1.0)
    step = (y1 - y0) / 9
    dx = side * q_span * 0.012
    for k in range(9):
        y = y0 + k * step
        host.plot([x, x + dx], [y, y + step * 0.9], color=_INK, lw=0.7)


def plot_test_points_vibration(
    curve,
    rated_q: Q_,
    rated_head: Q_,
    point_vibration: Sequence,
    limits: Mapping,
    por: Optional[tuple] = None,
    aor: Optional[tuple] = None,
    aor_factor: float = 1.30,
    measure: str = "overall",
    shutoff_fraction: float = 0.05,
    translate: Translate = lambda t: t,
    title: str = "",
) -> bytes:
    """
    Test points and vibration against flow, in the format of API 610
    Figure M.4, as PNG bytes.

    Parameters
    ----------
    curve : PerformanceCurve
        The fitted curve; its test points are drawn as stars on the head curve.
    point_vibration : sequence of (Q_, dict)
        ``(flow at rated speed, {vibration key: Q_})`` per test point (see
        :func:`pump.utilities.test_summary.vibration_by_region`).
    limits : mapping
        ``{"overall": Q_, "filtered": Q_}`` preferred-region limits.
    por, aor : (Q_, Q_), optional
        Operating regions.  Without ``aor``, the raised limit is drawn over
        the tested flow range (shut-off excluded), and the key says so.
    aor_factor : float
        Raise outside the preferred region (API 610: +30 %).
    measure : "overall" or "filtered"
        Which reading and limit to draw.
    """
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.figure import Figure

    from .test_summary import VIBRATION_KEYS

    _ = translate
    fitter = curve.fitter
    caps = np.asarray(fitter.capacities, dtype=float)
    heads = np.asarray(fitter.heads, dtype=float)
    rq = _m3h(rated_q)
    filtered = measure == "filtered"

    series: dict = {}
    for q, values in point_vibration or ():
        qv = _m3h(q)
        if qv < shutoff_fraction * rq:
            continue
        for key, v in (values or {}).items():
            if key.endswith("_f") != filtered or key not in VIBRATION_KEYS:
                continue
            series.setdefault(key, []).append((qv, float(v.to("mm/s").magnitude)))
    tested = [q for pts in series.values() for q, _v in pts]

    q_hi = max(float(caps.max()), rq)
    if aor is not None:
        q_hi = max(q_hi, _m3h(aor[1]))
    _lo, q_max, _t = _nice_range([0.0, q_hi * 1.06], nbins=6)

    fig = Figure(figsize=(9.8, 6.2))
    host = _host(fig, (0.09, 0.12, 0.55, 0.78), q_max)
    host.grid(False, which="both")
    host.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())

    # Y1: head with the test points ---------------------------------------- #
    qs = np.linspace(float(caps.min()), float(caps.max()), 240)
    h_fit = np.polyval(fitter.head_coeffs, qs)
    h_ticks = _nice_range(
        list(h_fit) + list(heads) + [float(rated_head.to("m").magnitude)]
    )[2]
    ax_h = _band_axis(host, "left", (0.56, 0.90), h_ticks, "Y1", _("Head") + " (m)")
    ax_h.plot(qs, h_fit, color=_INK, lw=2.0)
    ax_h.plot(
        caps,
        heads,
        marker="*",
        ls="none",
        ms=11,
        mfc=color("print-test-point"),
        mec=_INK,
        mew=0.6,
        zorder=5,
    )
    hr = float(rated_head.to("m").magnitude)
    ax_h.plot([rq], [hr], marker="o", ms=5, mfc="white", mec=_INK, mew=1.2, zorder=6)

    # Region limits, hatched, and the dimension arrows 1 (AOR) and 2 (POR) --- #
    def head_at(x):
        return float(np.polyval(fitter.head_coeffs, x))

    def frac(ax, y):  # data y of a band axis -> host fraction
        lo, hi = ax.get_ylim()
        return (y - lo) / (hi - lo)

    aor_q = None
    if aor is not None:
        aor_q = tuple(_m3h(p) for p in aor)
    elif tested:
        aor_q = (min(tested), max(tested))
    por_q = tuple(_m3h(p) for p in por) if por is not None else None
    span = q_max
    if aor_q is not None:
        for x, side in ((aor_q[0], -1), (aor_q[1], 1)):
            y = frac(ax_h, head_at(min(max(x, caps.min()), caps.max())))
            _hatch_limit(host, x, max(y - 0.07, 0.5), min(y + 0.07, 0.99), side, span)
            host.plot([x, x], [0.0, max(y - 0.07, 0.5)], color=_INK, lw=0.5)
        _dimension(host, aor_q[0], aor_q[1], 0.955, "1")
    if por_q is not None:
        for x, side in ((por_q[0], -1), (por_q[1], 1)):
            y = frac(ax_h, head_at(min(max(x, caps.min()), caps.max())))
            _hatch_limit(host, x, max(y - 0.07, 0.5), min(y + 0.07, 0.99), side, span)
            host.plot([x, x], [0.0, max(y - 0.07, 0.5)], color=_INK, lw=0.5)
        _dimension(host, por_q[0], por_q[1], 0.915, "2")
    # rated flow (5) and the rated operating point (8)
    host.plot([rq, rq], [0.0, frac(ax_h, hr)], color=_INK, lw=0.6)
    host.text(
        rq,
        -0.06,
        "5",
        transform=host.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
    )
    _callout(ax_h, rq, hr, "8", -16, -22)
    _callout(
        ax_h,
        float(caps.min() + 0.15 * (caps.max() - caps.min())),
        head_at(float(caps.min() + 0.15 * (caps.max() - caps.min()))),
        "7",
        -10,
        16,
    )

    # Y2: vibration against flow -------------------------------------------- #
    limit = limits.get("filtered" if filtered else "overall")
    basic = None if limit is None else float(limit.to("mm/s").magnitude)
    raised = None if basic is None else basic * aor_factor
    v_vals = [0.0] + [v for pts in series.values() for _q, v in pts]
    if raised is not None:
        v_vals.append(raised * 1.12)
    v_ticks = _nice_range(v_vals, 5)[2]
    unit = _("Vibration") + (
        " (" + _("filtered") + ", mm/s RMS)" if filtered else ", mm/s RMS"
    )
    ax_v = _band_axis(host, "left", (0.0, 0.44), v_ticks, "Y2", unit)
    styles = ["-", "--", "-.", ":"]
    for k, (key, pts) in enumerate(sorted(series.items())):
        pts.sort()
        xs, ys = zip(*pts)
        ax_v.plot(
            xs,
            ys,
            ls=styles[k % 4],
            marker="o",
            ms=3.5,
            lw=1.6,
            color=_ACCENT,
            label=_(VIBRATION_KEYS[key][0]),
        )
    if basic is not None:
        lo_b = por_q[0] if por_q else (aor_q[0] if aor_q else 0.0)
        hi_b = por_q[1] if por_q else (aor_q[1] if aor_q else q_max)
        ax_v.plot([lo_b, hi_b], [basic, basic], color=_LIMIT, lw=1.3)
        ax_v.text(hi_b, basic, f"  {basic:.1f}", color=_LIMIT, fontsize=7, va="center")
        if aor_q is not None and por_q is not None:
            drawn = []
            for a, b, edge in (
                (aor_q[0], por_q[0], por_q[0]),
                (por_q[1], aor_q[1], por_q[1]),
            ):
                if b > a:
                    ax_v.plot([a, b], [raised, raised], color=_LIMIT, lw=1.3)
                    ax_v.plot(
                        [edge, edge], [basic, raised], color=_LIMIT, lw=0.8, ls=":"
                    )
                    drawn.append((a, b))
            if drawn and raised is not None:
                a, b = drawn[-1]
                ax_v.text(
                    b, raised, f"  {raised:.1f}", color=_LIMIT, fontsize=7, va="center"
                )
                _callout(ax_v, (a + b) / 2, raised, "3", 14, 16)
        _callout(ax_v, (lo_b + hi_b) / 2, basic, "4", 10, -18)
    if series:
        first = sorted(series.items())[0][1]
        mid = first[len(first) // 2]
        _callout(ax_v, mid[0], mid[1], "6", -16, 18)
        ax_v.legend(
            loc="upper left",
            fontsize=6.5,
            frameon=False,
            bbox_to_anchor=(0.0, 0.44 / (1.0)),
            bbox_transform=host.transAxes,
        )
    else:
        host.text(
            0.5,
            0.2,
            _("No vibration recorded in the Test Points table."),
            transform=host.transAxes,
            ha="center",
            fontsize=8,
            style="italic",
        )

    host.text(
        1.04,
        -0.035,
        "X",
        transform=host.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="top",
    )
    _arrow_x(host)

    # Key (to the right, as on the form) ------------------------------------ #
    key = [
        ("X", _("flowrate") + " (m³/h)"),
        ("Y1", _("head") + " (m)"),
        ("Y2", _("vibration") + " (mm/s RMS)"),
        (
            "1",
            (
                _("allowable operating region of flow")
                if aor is not None
                else _("tested flow range (no allowable region in the project)")
            ),
        ),
        ("2", _("preferred operating region of flow")),
        (
            "3",
            _("limit outside the preferred region")
            + f" +{(aor_factor - 1) * 100:.0f} %",
        ),
        ("4", _("basic vibration limit")),
        ("5", _("rated flow")),
        ("6", _("vibration vs. flow curve")),
        ("7", _("head vs. flow curve")),
        ("8", _("rated operating point")),
        ("★", _("test point")),
    ]
    fig.text(0.71, 0.88, _("Key"), fontsize=9, fontweight="bold", va="top")
    for k, (tag, text) in enumerate(key):
        y = 0.84 - k * 0.042
        fig.text(0.71, y, tag, fontsize=7.5, va="top", fontweight="bold")
        fig.text(0.745, y, text, fontsize=7.2, va="top", wrap=True)
    if title:
        fig.text(0.10, 0.965, title, fontsize=9, va="top")
    return _png(fig)
