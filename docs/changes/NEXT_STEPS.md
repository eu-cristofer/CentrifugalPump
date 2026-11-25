# Next steps (after 001_masterpiece)

Recorded 2026-11-15. Project [001_masterpiece](001_masterpiece/README.md) is complete (14/14 sprints, `Status: ready to archive`) on branch `feat/masterpiece`. This file lists what remains, in priority order. Tick items as they are done.

## 0. Public split cutover (owner, 003_public-split)
Cutover done 2026-11-24. Still open: pushing the local `main` to the archive, and the last item.
- [x] Set the old GitHub repo to **private** (done 2026-11-24).
- [x] Merge `feat/public-split` into `main` locally (done 2026-11-24). Pushing it to the archive needs `PUMP_LEAK_SKIP=1`: still open.
- [x] Rename the GitHub repo `CentrifugalPump` → `CentrifugalPump-archive` (private, frozen; done 2026-11-24).
- [x] `sh tools/make_public_snapshot.sh ../CentrifugalPump-public` → review → create the **public** repo `CentrifugalPump` → `git -C ../CentrifugalPump-public remote add origin <url>` → push `main` (done 2026-11-24; the first CI fixes are PR #1).
- [x] Create the **private** repo `CentrifugalPump-data` and push `../CentrifugalPump-data` (done 2026-11-24).
- [x] Public repo settings: secret `LEAK_WORDLIST` (contents of `wordlist.txt`); Settings → Pages → Source "GitHub Actions"; run the Pages workflow (done 2026-11-24; docs and `/app/` live).
- [ ] Work from the public clone from then on (re-clone into `~/GitHub/CentrifugalPump`, keep this folder as the archive, run `sh tools/install_hooks.sh`).

## 1. Ship it
- [x] Push `feat/masterpiece` — done 2026-11-15. First CI run: 581 passed, 4 failed, all in one fixture test that compared floats digit for digit; Linux and macOS BLAS differ at about 1e-16. That test now compares numbers to 1e-9 relative and everything else exactly.
- [ ] Open a PR to `main`.
- [x] Fix whatever CI reports (2026-11-17): mypy clean (71 → 0: dynamic point attributes declared for type checkers, Optional caches, Path variables, explicit Quantity annotations) and `sphinx-build -W` clean (`Q_` type alias, `napoleon_use_ivar`, a "Project records" toctree, every `pump` module in the API reference). Both CI jobs are now **blocking**; only the LaTeX job stays non-blocking (needs TeX on the runner).
- [ ] Archive the project: `/sprint-loop archive 001_masterpiece`.

## 2. Before / at the P-9001B witness test (owner)
- [x] **Vibration units.** Vendor A states its in/s readings are **RMS** (owner, 2026-11-17), although the FFT printouts say "inch/s pk". The per-point gearbox-housing readings (spectra pp. 6-11) are in the reference project: overall 3.5-3.8 mm/s, above the 8th-edition 3.0 limit.
- [x] **API 610 8th edition tolerance table.** Done 2026-11-16 from the licensed text: Table 4-2 confirms head −2/+2 % above 300 m (P-9001A +1.72 % passes). It also showed that the 8th's shut-off bands split at **150 m**, not 75 m (fixed), and that efficiency is "not a rating value" (now information only).
- [x] **High-speed vibration allowance.** Not applicable to the 8th edition (Table 2-5 has none). The 11th/12th allowance (Figures 34/35) is still not applied; its formula is illegible in the local text conversion, so confirm it from the printed standard.
- [x] **N-553 client overlay.** Filled from **rev E** (NPSH margin, temperature stabilisation). ⚠ The P-9001 datasheet calls for **N-553 rev C**, which is not available: confirm the rules match rev C, or obtain rev C.
- [x] **NPSH margin rule.** N-553 rev E 7.3: ≥ 0.8 m **and** ratio ≥ 1.15 at rated flow. P-9001A passes (1.32 m, 2.22). API "rated NPSH +0 %" is judged once the quoted NPSHr is entered in the NPSH node.
- [ ] **Quoted NPSHr.** Read it from the datasheet / proposal and enter it in the NPSH node.
- [ ] **Mechanical-run duration.** The 8th edition defines no running test; confirm the 4 h (N-553 rev E 9.21: ndm ≥ 350 000 or energy density) from the purchase order.
- [ ] **SG discrepancy.** The datasheet says 0.999, but Vendor A's conversion used 0.990 and 0.50 cSt. Ask why.
- [ ] **Datasheet typo.** The body says "P-9001A/B" but the title says P-9001A/B.
- [ ] On test day:
  - open `examples/user/P-9001A_MRT_reference.pumpflow`;
  - fill the P-9001B Test Points, Mechanical Run and NPSH sheets in the units printed by the vendor;
  - run Report Export ▸ Export all (docx + tex + pdf + html);
  - save as `P-9001B_witness.pumpflow`.

- [ ] **Shut-off not tested (2026-11-25 FAT).** The vendor took no shut-off point (lowest at 35 % of rated flow); the tool extrapolates H(0) and fails it. Ask for the agreed exemption (integral-gear, 12th 8.3.3.4 power density ≈ 83 MW/m³) and a statement that the head rises to shut-off (N-553 rev E 6.1.11; the curve droops slightly at low flow). Confirm the governing API edition (the datasheet cites ISO 13709 / API 610 12th; the tool uses the 8th). See TR-01 §4.1.
- [ ] **Tool: shut-off not tested.** Report an extrapolated shut-off head as *not evaluated* instead of pass/fail, and add a "shut-off not tested" waiver with a required reason on the Compliance node, printed in the report. Optionally compute the 12th-edition power density. Moves verdicts: run `check.sh`.

## 3. Confirm researched values against the standards (owner)
On 2026-11-16 the 8th, 11th and 12th editions and N-553 rev D/E were checked against the owner's licensed texts (kept in the private data repo under `standards/`, never published). Still open:
- [x] API 610 11th/12th head, shut-off and power tolerances, vibration table, POR (Table 16, Table 8, 6.1.12).
- [ ] API 610 10th edition: no text available; still Amarinth bulletin values, `verified = false`.
- [x] API 610 11th/12th high-speed vibration allowance (Figures 34/35): applied, with the chart (2026-11-17). Exponents 0.30/0.21 reconstructed from the figure: **confirm against the printed figure**, then set `verified = true`.
- [ ] Pump type on every project (Rated Point): drives vibration locations and limits.
- [ ] Shaft displacement (proximity probes) limits: coefficients differ in the local text (8th 6.5e6 vs 11th OCR 6,2e6), confirm before encoding.
- [x] Test-speed check (within 3 % of rated, 8th 4.3.3.2.3 / 11th 8.3.3.3 c): the Compliance node's "Test speed" row (2026-11-17).
- [ ] HI 9.6.7 viscosity equations (`pump/viscosity.py`). They are validated independently, not against the standard text; buying ANSI/HI 9.6.7 would allow pinning its worked example.
- [x] Preferred operating region 70–120 % of BEP (8th 2.1.12, 11th 6.1.12, 12th 6.1).
- [x] Mechanical-run temperature-stabilisation rule: N-553 rev E 9.20 (2 K / 30 min after a 1 h warm-up).

## 3b. Code review findings (2026-11-16)
- [x] A1–A3: efficiency information only; 8th shut-off bands; rising-curve rule; rated NPSH +0 %.
- [x] B1: one engine, `pump.acceptance.evaluate_performance` (ADR 0012), 2026-11-17.
- [x] B2: a check that cannot be computed is "not evaluated", and the verdict reads NOT FULLY ASSESSED, never an approval.
- [x] B3: shut-off rows are detected against a fraction of the rated flow, not `capacity.m < 0.1`.
- [x] B4: `pumpflow/binding/` package (_common, curves, acceptance, reports, engineering), same public names (2026-11-17).
- [x] C1: `CLAUDE.md` refreshed (2026-11-17).

## 3c. UI/UX review (2026-11-17)
- [x] One verdict vocabulary (`ComplianceResult.verdict_text`); Report Export no longer shows NOT FULLY ASSESSED as REJECTED.
- [x] Tolerance overrides reach the report (stated with the criteria default and a reason); report summary limits use the same tolerances as the verdict.
- [x] Override editing collapsed behind "Override acceptance criteria…" with a Reason field.
- [x] Canvas verdict pill + OVERRIDDEN / PROVISIONAL chips; state glyphs (✓ ! ✗); zoomed-out overview.
- [x] Node windows open sized to their content; table headers not clipped.
- [ ] Shared rated point / fluid without wires (proposal in `docs/UI_SPEC.md` §11.1; decide first).
- [x] Rated Point: the free-text "Standard" is now "Label on report cover", under the edition combos (UI_SPEC §12).
- [x] Test Points: bench-geometry rows (label, value, unit) disabled while "Apply bench geometry" is off; disabled fields styled (`disabled-*` tokens).
- [x] Checked checkboxes draw a tick (`check-mark` token, `style.check_mark_path`).
- [ ] Decimal separator follows the OS locale; tie it to the report language or a setting.
- [x] Toolbox and Add node menu grouped (Inputs / Corrections / Curves & analysis / Checks / Output); distinct monochrome glyphs; dock titled "Nodes".
- [ ] Toolbox: glyphs have different widths, so titles do not line up; draw the glyph in a fixed-width column.
- [x] Welcome: "Demo pipeline" replaces "Skip"; "&" escaped; recent projects show folder and modified date.
- [ ] Form rows: long labels ("Discharge gauge elevation z_d") push their field right; align fields per section.
- [ ] Dark theme (tokens have only `light`).

## 3d. Web version follow-ups (002_web)
- [ ] Web forms for the other six node kinds (Point, Trim, Performance Explorer, System Curve, Operating Point, Pump Selection). They load and evaluate today and show "Edit this node in the desktop app".
- [ ] LaTeX/PDF report in the browser. Not possible offline today: use "Print to PDF" or the desktop.
- [ ] Dark theme for the web (the tokens have only `light`).
- [ ] Performance Plot: PNG export and a zoom toolbar.
- [x] Hosting decision: GitHub Pages, docs at the root and the app under `app/` (2026-11-23, 003_public-split).
- [x] Serve under a sub-path: the worker derives `py/` from the build base (`PUMPFLOW_BASE`); the app runs at `/app/` on Pages (2026-11-23).
- [ ] Undo granularity in the forms (one undo step per field edit today).

## 4. Product follow-ups (candidate sprints for a 002 project)
- [x] API 610 test data summary export (Annex M / 8th App. T): Word, LaTeX, PDF, Excel; Test Points vibration columns (2026-11-17).
- [ ] Vendor allowable-operating-region limits (min continuous stable flow / max flow) on the Rated Point, so the summary's allowable column uses them instead of "every tested point except shut-off".
- [ ] Shaft-displacement (proximity probe) readings for the summary's shaft rows.
- [ ] Render Markdown notes in reports. They are printed raw today: pipes, asterisks.
- [ ] Overlay the system curve and operating point on the Performance Plot and Explorer (deferred in S11).
- [ ] GUI for the NPSH 3 % head-drop sweep (library-only today: `pump.npsh.npsh3_from_sweep`).
- [ ] An "Export curve to catalogue" button on Curve Fit / Report Export (`binding.export_pumpcurve` exists).
- [ ] ISO 9906 grade tables (1B/2B) in `pump/standards/`, once confirmed values are available.
- [ ] Owner working files `examples/user/P-9001.pumpflow` and `P-9003.pumpflow` still carry sample-leftover rated values. Fix them or delete them; they are excluded from the catalogue.
- [ ] Optional: the HI large-trim correction (only pure affinity is implemented, with a 5 % warning).

## Never
- Commit the customer PDFs in `examples/user/*.PDF`.
- Invent standard values: ship them `verified = false` with an honest `source`.
