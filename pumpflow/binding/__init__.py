"""
binding
=======

The single place where the UI calls **into** the ``pump`` library (UI_SPEC §4).
Nothing here re-implements physics the library already provides; it only adapts
the signal payloads (:mod:`pumpflow.signals`, which carry Pint quantities) to the
library's constructors and reads results back out.

Binding table (UI_SPEC §4)
--------------------------
======================================  ====================================================
UI concept                              Library entry point
======================================  ====================================================
Rated fluid / test water                ``pump.Fluid(name, density=, viscosity=)``
Rated / design point                    ``pump.DesignPoint(fluid, capacity=, differential_head=, ...)``
Measured / corrected point              ``pump.TestPoint(fluid, capacity=, speed_of_rotation=, _head=, ...)``
Collection of points                    ``pump.PerformanceCurve(fluid, points, polynomial_degree=3)``
Affinity-law speed correction           ``PerformanceCurve.to_speed(Q_(N, "rpm"))``
Density correction                      ``PerformanceCurve.to_fluid(rated_fluid)``
Viscosity correction (HI 9.6.7)         ``PerformanceCurve.to_viscous(rated_fluid)``
Impeller trim (diameter affinity)       ``PerformanceCurve.to_diameter(d_new, d_ref)`` / ``pump.trim.diameter_for_duty``
Polynomial fit + predictions            ``PerformanceCurve.fitter.*_coeffs`` / ``predict_*``
Built-in matplotlib curve               ``PerformanceCurve.plot_performance_curve(...)``
Tolerances & verdict tables             ``pump.PerformanceChecker(design_point, curve, criteria=)``
Acceptance criteria (edition / client)  ``pump.acceptance.AcceptanceCriteria.load(key, client)``
Mechanical run verdict + trend plot     ``pump.mechanical_run.MechanicalRunChecker`` / ``plot_mechanical_run``
NPSHa / NPSHr curve / margin verdict    ``pump.npsh.npsh_available`` / ``NPSHrCurve`` / ``check_npsh`` / ``plot_npsh``
Units everywhere                        ``pump.Q_`` + ``quantity_factory`` (STANDARD_UNITS)
======================================  ====================================================

The adapter is a package; every public name is re-exported here, so
``from pumpflow.binding import X`` keeps working.
"""

from __future__ import annotations

from ._common import (
    BindingError,
    make_rated_fluid,
    water_density_kgm3,
    water_dynamic_viscosity_cP,
    water_kinematic_viscosity_cst,
    make_fluid,
    make_design_point,
    _has_eff,
    _mag,
)
from .curves import (
    row_head,
    row_head_components,
    format_geometry,
    row_efficiency,
    head_from_pressures,
    correct_curve,
    trim_curve,
    diameter_for_rated,
    fit_model,
)
from .acceptance import (
    criteria_for,
    criteria_label,
    standard_label,
    available_standards,
    available_clients,
    default_tolerances,
    check_compliance,
    check_mechanical_run,
    npsha_from_suction,
    check_npsh_set,
)
from .reports import (
    build_report_png,
    report_summary_for,
    comparison_for,
    DEFAULT_SIGNATORY_ROLES,
    cover_from_settings,
    open_points_from_notes,
    assemble_report_data,
    generate_docx,
    generate_tex,
    generate_pdf,
    generate_html,
    REPORT_FORMATS,
    export_reports,
)
from .engineering import (
    SYSTEM_CURVE_MODES,
    make_system_curve,
    solve_operating_point,
    export_pumpcurve,
    select_pumps,
    rated_from_candidate,
)
from .summary import (
    SUMMARY_FIELDS,
    SUMMARY_FORMATS,
    export_test_summary,
    form_title,
    test_data_summaries,
)

__all__ = [
    "SUMMARY_FIELDS",
    "SUMMARY_FORMATS",
    "export_test_summary",
    "form_title",
    "test_data_summaries",
    "BindingError",
    "make_rated_fluid",
    "water_density_kgm3",
    "water_dynamic_viscosity_cP",
    "water_kinematic_viscosity_cst",
    "make_fluid",
    "make_design_point",
    "row_head",
    "row_head_components",
    "format_geometry",
    "row_efficiency",
    "head_from_pressures",
    "correct_curve",
    "trim_curve",
    "diameter_for_rated",
    "fit_model",
    "criteria_for",
    "criteria_label",
    "standard_label",
    "available_standards",
    "available_clients",
    "default_tolerances",
    "check_compliance",
    "check_mechanical_run",
    "npsha_from_suction",
    "check_npsh_set",
    "build_report_png",
    "report_summary_for",
    "comparison_for",
    "DEFAULT_SIGNATORY_ROLES",
    "cover_from_settings",
    "open_points_from_notes",
    "assemble_report_data",
    "generate_docx",
    "generate_tex",
    "generate_pdf",
    "generate_html",
    "REPORT_FORMATS",
    "export_reports",
    "SYSTEM_CURVE_MODES",
    "make_system_curve",
    "solve_operating_point",
    "export_pumpcurve",
    "select_pumps",
    "rated_from_candidate",
]
