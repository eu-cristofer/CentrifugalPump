"""Formula explanations for the workbench (UC-10, educational mode).

One dictionary, :data:`FORMULAS`, is the single source of the text shown in
"formula" tooltips (``tooltip(key)``) and mirrored by the concept pages under
``docs/concepts/``.  The module is plain Python (no Qt) so it can be unit-tested
headless.

Each entry is ``key -> (title, text)``.  The equations are those implemented in the
``pump`` library; the HI 9.6.7 equations come from a secondary source and are not
checked against the standard text.
"""

from __future__ import annotations

__all__ = ["FORMULAS", "tooltip"]

FORMULAS = {
    "head": (
        "Total head",
        "H = ΔP/(ρ·g) + (v_d² − v_s²)/(2·g) + (z_d − z_s)\n"
        "ΔP = discharge − suction pressure (gauge or absolute cancel out);\n"
        "ρ = density at the measured water temperature; g = 9.80665 m/s²;\n"
        "v = Q / (π·D²/4) needs both pipe inside diameters; the elevation term "
        "needs both gauge elevations. Without geometry H = ΔP/(ρ·g). "
        "A measured head override wins.",
    ),
    "affinity": (
        "Affinity laws",
        "Q₂/Q₁ = N₂/N₁;  H₂/H₁ = (N₂/N₁)²;  P₂/P₁ = (N₂/N₁)³;  η unchanged.\n"
        "Same laws with the impeller diameter D for a trim (the library warns "
        "beyond 5 % trim). Valid for the same fluid and geometrically similar "
        "operation.",
    ),
    "efficiency": (
        "Efficiency",
        "η = P_hyd / P_shaft = ρ·g·Q·H / P_shaft\n"
        "P_hyd is the hydraulic power with the density of the test water at the "
        "row's temperature; P_shaft is the breaking (motor output) power.\n"
        "API 610 does not rate efficiency: it is judged only when the purchaser "
        "specified a tolerance.",
    ),
    "npsha": (
        "NPSH available",
        "NPSHa = (p_s,abs − p_v)/(ρ·g) + v_s²/(2·g) + z_s\n"
        "p_s,abs = absolute suction pressure (gauge + atmosphere); p_v = vapour "
        "pressure at the liquid temperature; v_s = suction velocity; z_s = tap "
        "elevation above the pump reference. The margin rule comes from the "
        "client (N-553 rev E: NPSHa − NPSHr ≥ 0.8 m and NPSHa/NPSHr ≥ 1.15 at "
        "rated flow); API 610 itself only requires NPSH3 ≤ the quoted NPSHr.",
    ),
    "viscosity_b": (
        "Viscosity parameter B (HI 9.6.7)",
        "B = 26.6·√ν·H^0.0625 / (Q^0.375·N^0.25)  [ν cSt, H ft/stage, Q gpm, "
        "N rpm at the water BEP]\n"
        "C_Q = 2.71^(−0.165·log10(B)^3.15);  C_H = 1 − (1 − C_Q)·(Q/Q_BEP)^0.75;  "
        "C_η = B^(−0.0547·B^0.69)\n"
        "Valid for 1 < B < 40; B ≤ 1 leaves the curve unchanged. Equations from "
        "a secondary source, not checked against the standard text.",
    ),
    "operating_point": (
        "Operating point",
        "H_pump(Q) = H_system(Q), with H_system = H_static + k·Qⁿ (or "
        "Darcy–Weisbach pipe friction).\n"
        "Found by bracketing the first sign change and bisecting; flagged as "
        "extrapolated when it lies outside the tested capacity range.",
    ),
    "trim": (
        "Impeller trim",
        "Q₂/Q₁ = D₂/D₁;  H₂/H₁ = (D₂/D₁)²;  P₂/P₁ = (D₂/D₁)³;  η unchanged.\n"
        "The diameter for a duty (q, h): intersect the parabola H = (h/q²)·Q² "
        "with the fitted head curve at Q₁, then D = D_ref·q/Q₁.",
    ),
}


def tooltip(key: str) -> str:
    """Tooltip text ``"<title>\\n<text>"`` for ``key``.

    Raises
    ------
    KeyError
        If ``key`` is not in :data:`FORMULAS`.
    """
    title, text = FORMULAS[key]
    return f"{title}\n{text}"
