# Next steps (after 001_masterpiece)

Recorded 2026-11-15. Project [001_masterpiece](001_masterpiece/README.md) is complete (14/14 sprints, `Status: ready to archive`) on branch `feat/masterpiece`. This file lists what remains, in priority order. Tick items as they are done.

## 1. Ship it
- [ ] Push `feat/masterpiece` and open a PR to `main`, so the CI workflow (`.github/workflows/ci.yml`) runs for the first time.
- [ ] Fix whatever CI reports. `mypy` and the Sphinx build have **never run** (neither tool was installed locally); both are non-blocking jobs until fixed:
  - `pip install -e ".[dev,docs]"`, then `mypy pump --ignore-missing-imports`, then fix the findings;
  - make the mypy step blocking (remove `continue-on-error`);
  - `sphinx-build -b html docs docs/_build/html -W`: fix the warnings, then make the docs job blocking. The new modules (npsh, viscosity, trim, catalogue, system curve, …) may need adding to `docs/api/pump.rst`.
- [ ] Archive the project: `/sprint-loop archive 001_masterpiece`.

## 2. Before / at the B-34004B witness test (owner)
- [ ] **Vibration units.** Ask Sundyne whether "VIBRATION-IN/SEC" on their sheets is **RMS or peak**. B-34004A unfiltered 0.16 in/s is 4.06 mm/s RMS, so FAILED against 3.0 mm/s; if it is peak, the RMS value is 2.87 mm/s, so passed.
- [ ] **API 610 8th edition tolerance table.** The 8th edition is currently *inferred* from the 10th (head ±2 % above 300 m). B-34004A predicts +1.72 %, which passes, but tightly. Confirm, then set `verified = true` with the clause as `source` in `pump/standards/api610.toml`.
- [ ] **High-speed vibration allowance.** API 610 relaxes the vibration limits for pumps above 3600 rpm or 300 kW per stage. This pump runs at 10 300 rpm; the allowance is not applied yet.
- [ ] **N-553 client overlay.** Fill in `pump/standards/clients/n553.toml` (tolerances, NPSH margin rule, vibration) from the Petrobras standard.
- [ ] **NPSH margin rule.** It is "not configured" today; enter the API/N-553 rule.
- [ ] **SG discrepancy.** The datasheet says 0.999, but Sundyne's conversion used 0.990 and 0.50 cSt. Ask why.
- [ ] **Datasheet typo.** The body says "B-33004A/B" but the title says B-34004A/B.
- [ ] On test day:
  - open `examples/user/B-34004A_MRT_reference.pumpflow`;
  - fill the B-34004B Test Points, Mechanical Run and NPSH sheets in the units printed by the vendor;
  - run Report Export ▸ Export all (docx + tex + pdf + html);
  - save as `B-34004B_witness.pumpflow`.

## 3. Confirm researched values against the standards (owner)
Every value below is stored with its `source` and `verified = false` because the paid standard text was not consulted. Confirm each one, then flip `verified` with a clause reference.
- [ ] API 610 10th/11th head, shut-off and power tolerances and the vibration table. Source: Amarinth bulletin MP2606-100.
- [ ] API 610 12th edition (still pre-S5 seed values).
- [ ] HI 9.6.7 viscosity equations (`pump/viscosity.py`). They are validated independently, not against the standard text; buying ANSI/HI 9.6.7 would allow pinning its worked example.
- [ ] Preferred operating region 70–120 % of BEP, used by pump selection.
- [ ] Mechanical-run temperature-stabilisation rule (not configured).

## 4. Product follow-ups (candidate sprints for a 002 project)
- [ ] Render Markdown notes in reports. They are printed raw today: pipes, asterisks.
- [ ] Overlay the system curve and operating point on the Performance Plot and Explorer (deferred in S11).
- [ ] GUI for the NPSH 3 % head-drop sweep (library-only today: `pump.npsh.npsh3_from_sweep`).
- [ ] An "Export curve to catalogue" button on Curve Fit / Report Export (`binding.export_pumpcurve` exists).
- [ ] ISO 9906 grade tables (1B/2B) in `pump/standards/`, once confirmed values are available.
- [ ] Owner working files `examples/user/B-34004.pumpflow` and `B-22025.pumpflow` still carry sample-leftover rated values. Fix them or delete them; they are excluded from the catalogue.
- [ ] Optional: the HI large-trim correction (only pure affinity is implemented, with a 5 % warning).

## Never
- Commit the customer PDFs in `examples/user/*.PDF`.
- Invent standard values: ship them `verified = false` with an honest `source`.
