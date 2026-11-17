"""
pumpflow.binding.summary

The API 610 test data summary (Annex M / 8th-edition Appendix T): fill a
:class:`pump.utilities.test_summary.TestDataSummary` per pump from the project
and export it (docx, tex, pdf, xlsx).  Values the project does not hold are left
blank, never invented.
"""

from __future__ import annotations

from typing import Callable, Optional

from pump import Q_
from pump.utilities.test_summary import (
    PerformanceLine,
    TestDataSummary,
    VibrationLine,
    plot_test_curve,
    vibration_by_region,
    write_docx,
    write_pdf,
    write_tex,
    write_xlsx,
)

from ..signals import RatedPoint
from .acceptance import criteria_for, criteria_label

#: Formats the summary can be written in.
SUMMARY_FORMATS = ("docx", "tex", "pdf", "xlsx")

#: Optional Report Export settings used only by the summary (stored when set).
SUMMARY_FIELDS = (
    "purchaser",
    "po_number",
    "item_number",
    "curve_number",
    "stages",
    "impeller_pattern",
    "vanes",
    "volute_pattern",
    "blade_tip_clearance",
)

Translate = Callable[[str], str]


def _ordinal(n: str) -> str:
    try:
        k = int(n)
    except ValueError:
        return n
    suffix = (
        "th" if 10 <= k % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    )
    return f"{k}{suffix}"


def form_title(criteria, translate: Translate) -> str:
    """'Test data summary (API 610 8th edition, Appendix T)' or '…, Annex M)'."""
    _ = translate
    standard, _sep, edition = criteria.key.partition(":")
    annex = _("Appendix T") if edition == "8" else _("Annex M")
    if standard == "api610":
        where = (
            _("API 610 {ordinal} edition").format(
                ordinal=_ordinal(edition), number=edition
            )
            + f", {annex}"
        )
    else:
        where = criteria.label
    return f"{_('Test data summary')} ({where})"


def _band(minus: float, plus: float) -> str:
    if abs(minus - plus) < 1e-12:
        return f"±{plus * 100:g} %"
    return f"−{minus * 100:g} / +{plus * 100:g} %"


def _mag(q, unit: str) -> Optional[float]:
    return None if q is None else float(q.to(unit).magnitude)


def _signatory(settings: dict, *roles: str) -> str:
    names = [
        str(r.get("name") or "").strip()
        for r in settings.get("signatories") or []
        if isinstance(r, dict) and r.get("role") in roles
    ]
    return ", ".join(n for n in names if n)


def _performance(rated: RatedPoint, branch, criteria, compliance) -> tuple:
    rows = {p.name: p for p in (compliance.parameters if compliance else ())}
    tol = dict(getattr(compliance, "tolerances", {}) or {})
    lines = [
        PerformanceLine(
            "Flow", "m³/h", _mag(rated.q, "m**3/h"), _mag(rated.q, "m**3/h"), None, ""
        )
    ]
    h = rows.get("Head")
    h_band = criteria.head_tolerance(rated.head)
    if tol.get("head") is not None and abs(tol["head"] - h_band[1]) > 1e-9:
        h_band = (tol["head"], tol["head"])
    lines.append(
        PerformanceLine(
            "Head",
            "m",
            _mag(rated.head, "m"),
            getattr(h, "predicted", None),
            getattr(h, "deviation", None),
            _band(*h_band),
        )
    )
    p = rows.get("Power")
    lines.append(
        PerformanceLine(
            "Power",
            "kW",
            _mag(rated.power, "kW"),
            getattr(p, "predicted", None),
            getattr(p, "deviation", None),
            f"+{(tol.get('power', criteria.power_tol_plus)) * 100:g} %",
        )
    )

    npsh = getattr(branch, "npsh", None)
    res = getattr(npsh, "result", None)
    if res is not None:
        quoted = getattr(res, "npshr_quoted", None)
        tested = _mag(res.npshr, "m")
        dev = None
        if quoted is not None and _mag(quoted, "m"):
            dev = (tested - _mag(quoted, "m")) / _mag(quoted, "m")
        tol_n = res.criteria.npshr_tol_plus
        lines.append(
            PerformanceLine(
                "NPSH3",
                "m",
                _mag(quoted, "m"),
                tested,
                dev,
                "" if tol_n is None else f"+{tol_n * 100:g} %",
            )
        )
    else:
        lines.append(PerformanceLine("NPSH3", "m"))

    so = rows.get("Shutoff Head")
    s_band = criteria.shutoff_tolerance(rated.head)
    if tol.get("shutoff") is not None and abs(tol["shutoff"] - s_band[1]) > 1e-9:
        s_band = (tol["shutoff"], tol["shutoff"])
    lines.append(
        PerformanceLine(
            "Shut-off head",
            "m",
            _mag(rated.head_shutoff, "m"),
            getattr(so, "predicted", None),
            getattr(so, "deviation", None),
            _band(*s_band) if rated.head_shutoff is not None else "",
            note="extrapolated" if getattr(so, "extrapolated", False) else "",
        )
    )
    sp = rows.get("Test speed")
    lines.append(
        PerformanceLine(
            "Speed",
            "rpm",
            _mag(rated.speed, "rpm"),
            getattr(sp, "predicted", None),
            getattr(sp, "deviation", None),
            f"±{criteria.test_speed_tol * 100:g} %" if criteria.test_speed_tol else "",
        )
    )
    return tuple(lines)


def _vibration(rated, branch, criteria, translate: Translate):
    _ = translate
    fitted = branch.fitted
    limits = {
        "overall": criteria.mechanical_run.role_max.get("vibration_unfiltered"),
        "filtered": criteria.mechanical_run.role_max.get("vibration_filtered"),
    }
    sel = criteria.selection
    try:
        q_bep = fitted.curve.bep()[0]
    except Exception:
        q_bep = None
    points = tuple(getattr(fitted, "point_vibration", ()) or ())
    notes = []
    if points:
        lines = vibration_by_region(
            points, rated.q, q_bep, limits, por=(sel.por_min, sel.por_max)
        )
        if q_bep is not None:
            notes.append(
                _(
                    "Preferred operating region: {lo:g}–{hi:g} % of the BEP flow "
                    "({qlo:.2f}–{qhi:.2f} m³/h)."
                ).format(
                    lo=sel.por_min * 100,
                    hi=sel.por_max * 100,
                    qlo=sel.por_min * q_bep.to("m**3/h").magnitude,
                    qhi=sel.por_max * q_bep.to("m**3/h").magnitude,
                )
            )
        notes.append(
            _(
                "Allowable region: every tested point except shut-off (the "
                "vendor's allowable-region limits are not in the project); "
                "specified = preferred-region limit + 30 %."
            )
        )
    else:
        lines = ()
        mech = getattr(getattr(branch, "mechanical", None), "result", None)
        if mech is not None:
            fallback = []
            for role, measure in (
                ("vibration_unfiltered", "Overall"),
                ("vibration_filtered", "Filtered"),
            ):
                maxima = [
                    c.max for c in mech.channels if c.role == role and c.max is not None
                ]
                if maxima:
                    peak = max(float(m.to("mm/s").magnitude) for m in maxima)
                    fallback.append(
                        VibrationLine(
                            "All probes (mechanical run)",
                            measure,
                            rated=(
                                round(peak, 2),
                                _mag(limits[measure.lower()], "mm/s"),
                            ),
                        )
                    )
            lines = tuple(fallback)
            if lines:
                notes.append(
                    _(
                        "No vibration in the Test Points table: the rated-flow "
                        "column is taken from the mechanical run."
                    )
                )
    notes.insert(
        0,
        _(
            "Bearing-housing velocity, mm/s RMS. True-peak values are not "
            "used for acceptance."
        ),
    )
    return lines, tuple(notes)


def _bearings(branch, settings: dict, translate: Translate) -> tuple:
    mech = getattr(getattr(branch, "mechanical", None), "result", None)
    oil = bearing = None
    if mech is not None:
        oils = [
            c.max
            for c in mech.channels
            if c.role == "oil_temperature" and c.max is not None
        ]
        brgs = [
            c.max
            for c in mech.channels
            if c.role == "bearing_temperature" and c.max is not None
        ]
        oil = max(oils, key=lambda q: q.to("K").magnitude) if oils else None
        bearing = max(brgs, key=lambda q: q.to("K").magnitude) if brgs else None
    ambient = None
    if settings.get("ambient_temp") is not None:
        unit = {"°C": "degC", "°F": "degF", "K": "K"}.get(
            settings.get("ambient_temp_unit") or "°C", "degC"
        )
        ambient = Q_(float(settings["ambient_temp"]), unit)

    def show(q):
        return "" if q is None else f"{q.magnitude:.1f} {q.units:~P}"

    rise = ""
    if oil is not None and ambient is not None:
        delta = oil.to("K").magnitude - ambient.to("K").magnitude
        rise = f"{delta:.1f} K"
    return (
        ("Ambient temperature", show(ambient)),
        ("Oil sump / outlet temperature", show(oil)),
        ("Oil temperature rise", rise),
        ("Maximum bearing temperature", show(bearing)),
    )


def test_data_summaries(
    rated: RatedPoint,
    branches,
    settings: Optional[dict] = None,
    translate: Translate = lambda t: t,
) -> list:
    """One :class:`TestDataSummary` per pump branch that has a fitted curve."""
    _ = translate
    s = settings or {}
    criteria = criteria_for(rated)
    equipment = s.get("equipment") or {}
    title = form_title(criteria, translate)
    out = []
    for b in branches:
        if b.fitted is None:
            continue
        eq = {**equipment, **(getattr(b, "equipment", None) or {})}
        size_type = " / ".join(v for v in (eq.get("Model"), eq.get("Type")) if v)
        header = (
            ("Customer", s.get("client", "")),
            ("Purchaser", s.get("purchaser") or s.get("client", "")),
            ("Purchase order no.", s.get("po_number", "")),
            ("Item no.", s.get("item_number") or rated.tag),
            ("Pump serial no.", eq.get("Serial No.", "")),
            ("Size and type", size_type),
            ("No. of stages", s.get("stages", "")),
            ("Curve no.", s.get("curve_number", "")),
            ("Test date", s.get("test_date", "")),
            ("Certified by (vendor representative)", _signatory(s, "Vendor")),
            (
                "Witnessed by (purchaser representative)",
                _signatory(s, "Client witness", "Inspector"),
            ),
        )
        d_imp = getattr(rated, "impeller_diameter", None)
        construction = (
            (
                "Impeller diameter (mm)",
                "" if d_imp is None else f"{_mag(d_imp, 'mm'):.1f}",
                "",
            ),
            ("Impeller pattern no.", s.get("impeller_pattern", ""), ""),
            ("No. of vanes", s.get("vanes", ""), ""),
            ("Volute/diffuser pattern no.", s.get("volute_pattern", ""), ""),
            ("Blade tip clearance (%)", s.get("blade_tip_clearance", ""), ""),
        )
        vib_lines, vib_notes = _vibration(rated, b, criteria, translate)
        sel = criteria.selection
        try:
            q_bep = b.fitted.curve.bep()[0]
            por = (sel.por_min * q_bep, sel.por_max * q_bep)
        except Exception:
            por = None
        try:
            png = plot_test_curve(
                b.fitted.curve,
                rated.q,
                rated.head,
                por=por,
                npsh_curve=getattr(getattr(b, "npsh", None), "curve", None),
                title=f"{b.pump_tag} · {_('rated speed')} {_mag(rated.speed, 'rpm'):g} rpm",
                labels={
                    "flow": _("Flow") + " (m³/h)",
                    "head": _("Head") + " (m)",
                    "eff": _("Efficiency") + " (%)",
                    "power": _("Power") + " (kW)",
                    "npsh": "NPSH3 (m)",
                    "por": _("Preferred operating region"),
                    "rated": _("Rated point"),
                },
            )
        except Exception:
            png = None
        notes = [
            _("Blank fields are not recorded in the project: complete them by hand.")
        ]
        open_parts = [p for p in criteria.unverified]
        if open_parts:
            notes.append(
                _(
                    "Criteria not yet verified against the standard text: {items}."
                ).format(items=", ".join(open_parts))
            )
        out.append(
            TestDataSummary(
                pump_tag=b.pump_tag,
                form_title=title,
                standard_label=criteria_label(criteria),
                header=header,
                performance=_performance(rated, b, criteria, b.compliance),
                construction=construction,
                vibration=vib_lines,
                vibration_notes=vib_notes,
                bearings=_bearings(b, s, translate),
                curve_png=png,
                notes=tuple(notes),
            )
        )
    return out


def export_test_summary(
    summaries,
    formats=SUMMARY_FORMATS,
    language: str = "en",
    out_dir: Optional[str] = None,
    stem: str = "Test_data_summary",
):
    """Write the summaries; ``(paths, errors)`` like :func:`export_reports`."""
    from pathlib import Path

    from pump.utilities.report import LocalizationHelper

    _ = LocalizationHelper(language)._
    folder = Path(out_dir or ".")
    writers = {
        "docx": lambda p: write_docx(summaries, p, _),
        "tex": lambda p: write_tex(summaries, p, _, language),
        "pdf": lambda p: write_pdf(summaries, p, _, language),
        "xlsx": lambda p: write_xlsx(summaries, p, _),
    }
    paths, errors = {}, {}
    for fmt in formats:
        if fmt not in writers:
            errors[fmt] = f"unknown summary format {fmt!r}"
            continue
        try:
            paths[fmt] = writers[fmt](folder / f"{stem}.{fmt}")
        except Exception as exc:  # collected, reported by the caller
            errors[fmt] = f"{type(exc).__name__}: {exc}"
    return paths, errors
