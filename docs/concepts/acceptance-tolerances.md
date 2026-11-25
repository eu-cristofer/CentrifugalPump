# Acceptance tolerances (data-driven)

A performance test is accepted when the values predicted by the fitted curve at the *rated*
flow fall inside the tolerances of the governing standard.  The tolerances are **data**,
not code: they live in TOML files under `pump/standards/` and are loaded by
`pump.acceptance.AcceptanceCriteria`.

## What is checked

The deviation is always

$$
\delta = \frac{x_{predicted} - x_{rated}}{x_{rated}}
$$

(`pump.acceptance.deviation`, used by both the library and the workbench).

| Check | Rule | Part of the verdict? |
|---|---|---|
| Rated head | $-t_- \le \delta_H \le +t_+$, band chosen by the rated head | yes |
| Shut-off head | $-t_- \le \delta_{H_0} \le +t_+$, band chosen by the rated head | yes |
| Rated power | $\delta_P \le +4\,\%$ | yes |
| Efficiency | $\delta_\eta \ge -t$ **only if the purchaser specified $t$** | no, otherwise information only |
| Rising curve (when specified) | the negative shut-off tolerance applies only if the curve still rises to shut-off | yes |
| Parallel operation | $H_0 / H_{rated} \ge 1.10$ | yes, when `parallel` is set |
| Rated NPSH | tested NPSH3 at rated flow $\le$ quoted NPSHr (+0 %) | yes, NPSH verdict |
| Test speed | every tested speed within ±3 % of the rated speed | yes |

The shut-off head is flagged *extrapolated* when no test point lies below 5 % of the rated
flow.  This threshold is a tool setting, not a value from the standard.

An extrapolated shut-off head is not a measurement: with the lowest point far from Q = 0,
the predicted value depends on the fit degree and on which points are kept.  Shut-off may
be left out of the test only where the standard allows it: high-energy and multistage
pumps (8th 4.3.3.2.1 note), also integral-gear pumps (11th 8.3.3.3 a) note), and in the
12th edition when the power density P / (D_imp · D_nozzle²) exceeds about 13 MW/m³
(8.3.3.4).  N-553 rev D/E make the shut-off point a "shall" (9.14 / 9.13), so an omission
needs the client's concurrence.  See {doc}`../training/TR-01-witness-performance-test` §4.1.

## The values, by edition

Checked on 2026-11-16 against the owner's licensed copies of API 610 8th, 11th and 12th
editions.  The standard texts are kept locally and never committed.

**Rated differential head** (`head_bands`)

| Edition | 0-75 m | 75-150 m | 150-300 m | > 300 m | Clause |
|---|---|---|---|---|---|
| API 610 8th | -2 / +5 % | -2 / +5 % | -2 / +3 % | -2 / +2 % | Table 4-2 |
| API 610 10th | -2 / +5 % | -2 / +5 % | -2 / +3 % | -2 / +2 % | *not checked (secondary source)* |
| API 610 11th | ±3 % | ±3 % | ±3 % | ±3 % | Table 16 |
| API 610 12th | ±3 % | ±3 % | ±3 % | ±3 % | Table 16 |

**Shut-off head** (`shutoff_bands`): the band edges differ between editions.

| Edition | ±10 % up to | ±8 % up to | ±5 % above | Clause |
|---|---|---|---|---|
| API 610 8th | 150 m | 300 m | 300 m | Table 4-2 |
| API 610 10th / 11th / 12th | 75 m | 300 m | 300 m | Table 16 (10th not checked) |

A pump rated at 120 m therefore gets ±10 % at shut-off under the 8th edition but ±8 %
under the 11th.  Before 2026-11-16 the 8th edition used the 75 m edge, which was wrong.

**Rated power**: +4 %, from all causes.  Cumulative tolerances are not acceptable: the
power after correction for flow, speed, density and viscosity must not exceed 104 % of the
rated value.

**Efficiency**: *not a rated value* (8th Table 4-2 note; 11th/12th Table 16 note c; the
12th gives the reason as a test uncertainty of about ±2.5 %).  No edition defines
`efficiency_tol_minus`, so the Compliance node reports efficiency as **information** and
leaves it out of the verdict.  When the purchaser specifies an efficiency tolerance, tick
*Efficiency is guaranteed* in the Compliance node and enter it.  For example, N-553 rev E
9.14 asks for −0 % for drivers of 1 MW or more.

**Rated NPSH**: +0 %.  The NPSH3 measured at the rated point must not exceed the quoted
value (8th 4.3.4.1.3; 11th 8.3.4.3.4).  Enter the quoted NPSHr in the NPSH node to judge it.
API 610 has **no** NPSHa/NPSHr margin rule.  That rule comes from the client (see below).

**Preferred operating region**: 70-120 % of the BEP flow, with the rated flow within
80-110 % (8th 2.1.12; 11th 6.1.12; 12th 6.1).

**Test speed**: within 3 % of the rated speed unless otherwise agreed (8th 4.3.3.2.3;
11th 8.3.3.3 c).  Results are corrected to the rated speed.  The Compliance node checks the
worst tested speed (`test_speed_tol = 0.03`) as the **Test speed** row.

## One engine, three outcomes

Every check above is made by `pump.acceptance.evaluate_performance`, used by both the
library's `PerformanceChecker` and the workbench's Compliance node
([ADR 0012](../adr/0012-single-performance-verdict-engine.md)).  Each row is `pass`,
`fail`, `info` (reported, not judged) or `not evaluated` (required but not computable;
the reason is in the row's note).  The verdict is:

- **APPROVED** when nothing fails and everything required was evaluated;
- **REJECTED / NOT APPROVED** when any judged check fails;
- **NOT FULLY ASSESSED** when nothing fails but a required check could not be made,
  for example no power column, so power cannot be predicted.  Never an approval.

## Client overlay: Petrobras N-553 rev E

`pump/standards/clients/n553.toml` changes only what N-553 rev E changes:

| Item | Rule | Clause |
|---|---|---|
| NPSH margin | at rated flow, NPSHa - NPSHr $\ge$ 0.8 m **and** NPSHa/NPSHr $\ge$ 1.15 | 7.3 |
| NPSHr at every point | when the margin is < 1 m or the ratio < 1.20 | 9.22 note |
| Temperature stabilisation | no rise > 2 K in 30 min, after a 1 h warm-up | 9.20 |
| 4 h mechanical run | when ndm $\ge$ 350 000 or the energy-density criterion is met | 9.21 |
| Efficiency | −0 % at rated flow, drivers $\ge$ 1 MW only (not encoded: use the override) | 9.14 |

**Check the revision on the datasheet.**  P-9001 A/B calls for *N-553C*.  Rev C was not
available.  Rev D (checked) words the NPSH rule differently: 0.8 m *or* a ratio of 1.25,
whichever is greater, from minimum continuous stable flow up to the rated flow.

## The `verified` flag

Every edition and overlay carries `verified` and a `source` naming its clauses.

- `verified = true` on an edition covers its **performance tolerances**.
- A merged sub-table (mechanical run, NPSH, selection) is verified only when **every**
  layer that contributes to it is.  A verified overlay that adds one rule does not hide an
  unverified base value.
- `AcceptanceCriteria.unverified` lists every open part (it feeds the report's
  "Deviations and open points"); `performance_unverified` lists only the parts that bear
  on the performance verdict.

Still open:
- the **10th edition**, which was not available;
- the **mechanical run** in every edition: the 8th edition has no mechanical running
  test, so the duration comes from the purchase order;
- the **11th/12th high-speed vibration rule** (Figures 34 / 35): applied, but with
  exponents reconstructed from the figure, so unverified.  See {doc}`vibration`.

A verdict computed with unverified criteria is **provisional** and says so: *APPROVED
(unverified criteria)* or *FAILED (unverified limits)*.  Never flip a flag to `true`
without a clause-level source.

## How it is wired

```toml
[editions."8"]
label = "API 610 8th edition"
source = "API 610 8th ed. Table 4-2 ..."
verified = true
power_tol_plus = 0.04
# no efficiency_tol_minus: efficiency is not a rated value
head_bands = [
  { max_rated_head = "150 m", tol_minus = 0.02, tol_plus = 0.05 },
  { max_rated_head = "300 m", tol_minus = 0.02, tol_plus = 0.03 },
  { max_rated_head = "inf m", tol_minus = 0.02, tol_plus = 0.02 },
]
```

Training: {doc}`../training/TR-01-witness-performance-test`.
