# Mechanical running test

The mechanical run is typically 4 h at rated flow, logged every 15 min.  `pump.mechanical_run`
models the log, checks it against criteria and plots the trends for the report.

## The log

- A `Channel` has a name and a **role** (`vibration_filtered`, `vibration_unfiltered`,
  `bearing_temperature`, `oil_temperature`, `oil_pressure`, `seal_pressure`, `flow`,
  `differential_pressure`, `power`, `other`).
- A `RunReading` is a clock time ("HH:MM") and a value per channel, each a Pint quantity in
  the unit the engineer logged (for example in/s and degF).
- Elapsed time is measured from the first reading and is monotone; the clock may wrap past
  midnight.

## The checks

For every channel:

- an **upper limit per role** compared with the channel maximum,
  $\max_t x(t) \le x_{limit}$ (the limit is converted to the channel's unit);
- an optional **stabilisation rule** per role: over the last window $W$ of the run

$$
\max_{t \in W} x(t) - \min_{t \in W} x(t) \le \Delta x_{allowed}
$$

  (temperatures are differenced on kelvin and expressed in `delta_degF` or `delta_degC`).

And for the run: the **duration** (first to last reading) must reach the minimum.

Every check has a status of `pass`, `fail` or `info`.  A check without a configured
criterion is `info`, never pass or fail.  The result passes when nothing fails, and
`fully_assessed` is false while the duration or any vibration, bearing-temperature or
oil-temperature channel is still `info`.  The verdict reads `PASSED`, `FAILED` or
`PASSED (not fully assessed)`; with unverified criteria the report adds *(unverified
limits)*.

## The values shipped (all unverified)

| Criterion | Value | Source |
|---|---|---|
| Minimum duration | 4 h at rated flow, with oil-temperature stabilisation | Amarinth bulletin MP2606-100 rev A |
| Filtered (discrete) vibration | 2.0 mm/s RMS (allowable region 2.6) | idem, horizontal pumps, preferred region |
| Unfiltered (overall) vibration | 3.0 mm/s RMS (allowable region 3.9) | idem |
| Stabilisation | not configured | - |

Open questions: the limits are **RMS**, so it matters whether a test sheet's "in/s" is RMS or
peak (B-34004A's unfiltered 0.16 in/s is 4.06 mm/s if RMS, which fails 3.0, but 2.87 mm/s if
peak); and the API 610 allowance for pumps above 3600 rpm or 300 kW per stage (this pump runs at
10 300 rpm) is not applied.  See {doc}`acceptance-tolerances`.

## Worked notebook

[UC-11 - mechanical run](../../use_cases/UC-11_mechanical_run.ipynb): a 4 h log in in/s and degF,
the shipped criteria (not fully assessed), an illustrative full criteria set, and three failures
(a vibration spike, a short run, an unstable oil temperature).

## API

{doc}`API reference <../api/pump>`: `pump.mechanical_run` (`MechanicalRunLog`, `MechanicalRunCriteria`,
`MechanicalRunChecker`, `plot_mechanical_run`) and `pump.acceptance.AcceptanceCriteria.mechanical_run`.
