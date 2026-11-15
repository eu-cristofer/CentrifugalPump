# Acceptance tolerances (data-driven)

A performance test is accepted when the predicted values at the rated point fall inside
the tolerances of the governing standard.  The tolerances are **data**, not code: they live
in TOML files under `pump/standards/` and are loaded by `pump.acceptance.AcceptanceCriteria`.

## What is checked

The predicted values come from the fitted curve at the *rated* capacity, and the deviation
is always

$$
\delta = \frac{x_{predicted} - x_{rated}}{x_{rated}}
$$

(`pump.acceptance.deviation`, used by both the library and the workbench).

| Check | Rule | Keyed by |
|---|---|---|
| Rated head | $-t_- \le \delta_H \le +t_+$ | rated differential head band |
| Shut-off head | $-t_- \le \delta_{H_0} \le +t_+$ | rated differential head band |
| Breaking power | $\delta_P \le +t$ | - |
| Efficiency | $\delta_\eta \ge -t$ | - |
| Parallel operation | $H_0 / H_{rated} \ge r$ | - (only when `parallel` is set) |

The shut-off head is flagged *extrapolated* when no test point lies below a fraction of
the rated capacity.

## The values shipped (all `verified = false`)

**Head tolerance** by rated differential head (`head_bands`):

| Edition | $\le$ 150 m | 151 - 300 m | > 300 m | Source |
|---|---|---|---|---|
| API 610 8th | +5 / -2 % | +3 / -2 % | +/- 2 % | *inferred from the 10th* |
| API 610 10th | +5 / -2 % | +3 / -2 % | +/- 2 % | Amarinth bulletin |
| API 610 11th | +/- 3 % | +/- 3 % | +/- 3 % | Amarinth bulletin |
| API 610 12th | +/- 3 % | +/- 3 % | +/- 3 % | seed: pre-sprint-5 code defaults |

**Shut-off head**, all editions: +/-10 % up to 75 m, +/-8 % up to 300 m, +/-5 % above
(rated differential head).  **Breaking power**: +4 %.  **Efficiency**: -3 % (seed).
**Parallel operation** shut-off ratio: 1.10 (seed).  **Shut-off extrapolation** threshold:
5 % of the rated capacity (seed).

**Mechanical run** (`mechanical_run` table): 4 h at rated flow; horizontal-pump vibration
(preferred region, mm/s RMS) 3.0 overall, 2.0 discrete.  See {doc}`mechanical-run`.
**NPSH margin**: not configured, see {doc}`npsh`.  **Preferred operating region** for
pump selection: 70 - 120 % of the BEP flow.

## The `verified` flag and the sources

Every table carries `verified = false|true` and a `source` string.  **No row is verified**:
the values are secondary-source or seed values, and the standard text itself was not
consulted.

- The main secondary source is the **Amarinth technical bulletin MP2606-100 rev A (Dec-11),
  "Testing procedures API 610 10th and 11th"** (head bands of the 10th and 11th editions,
  the 4 h mechanical run, the horizontal-pump vibration limits).
- The **8th edition is inferred from the 10th**, because no public 8th-edition text was
  found.  B-34004A (333.8 m) therefore gets +/-2 % on head, which its predicted +1.72 %
  passes, but tightly.
- Shut-off and power values are corroborated by secondary sources; efficiency, parallel
  operation and extrapolation values are seeds.

A verdict computed with unverified criteria is **provisional** and says so: the node
status, the banner and the report read *APPROVED (unverified criteria)* or *FAILED
(unverified limits)*.  `AcceptanceCriteria.unverified` lists the parts still to confirm,
and the report lists them too.  Never flip a flag to `true` without a clause-level source.

## How it is wired

```toml
[editions."11"]
label = "API 610 11th edition"
source = "..."
verified = false
power_tol_plus = 0.04
head_bands = [
  { max_rated_head = "inf m", tol_minus = 0.03, tol_plus = 0.03 },
]
