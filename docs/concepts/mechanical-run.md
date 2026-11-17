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

## The values shipped

| Criterion | Value | Source |
|---|---|---|
| Unfiltered (overall) vibration | 3.0 mm/s RMS, +30 % outside the preferred region | API 610 8th Table 2-5; 11th/12th Table 8 |
| Filtered (discrete) vibration | 2.0 mm/s RMS, +30 % outside the preferred region | same |
| Minimum duration | 4 h at rated flow | 11th 8.3.4.2.2 / 12th 8.3.4.2, *if specified*; the 8th edition has no run test |
| Stabilisation | none in the API tables; N-553 rev E: no rise > 2 K in 30 min, after a 1 h warm-up | N-553 rev E 9.20 |

The mechanical-run part stays **unverified**, for two reasons:
- under the 8th edition the duration comes from the purchase order;
- the 11th and 12th editions allow higher vibration for pumps above 3600 r/min or 300 kW
  per stage (Figures 34 / 35), and that allowance is not applied: its formula is illegible
  in the local copy.  The tool keeps the conservative 3.0 / 2.0 mm/s.

## RMS, not peak

API 610 bearing-housing limits are **RMS**.  The 8th edition says so in its own words:
true-peak values "are for information and diagnostic purposes only and are not to be used
to determine the acceptability of the equipment" (2.8.3.7 note).  When US units are
specified, true-peak velocities shall *also* be recorded (4.3.3.3.1).  US vendors
therefore often print both, or only peak.

So a test sheet in **in/s** needs one question answered: RMS or true peak?  Do not convert
a peak value to RMS by dividing by $\sqrt 2$: that holds only for a pure sine wave.  Ask
for the RMS readings.  B-34004A's unfiltered 0.16 in/s is 4.06 mm/s; read as RMS, it
**fails** 3.0 mm/s under the 8th edition.

## Worked notebook

[UC-11 - mechanical run](../../use_cases/UC-11_mechanical_run.ipynb): a 4 h log in in/s and degF,
the shipped criteria (not fully assessed), an illustrative full criteria set, and three failures
(a vibration spike, a short run, an unstable oil temperature).

## API

{doc}`API reference <../api/pump>`: `pump.mechanical_run` (`MechanicalRunLog`, `MechanicalRunCriteria`,
`MechanicalRunChecker`, `plot_mechanical_run`) and `pump.acceptance.AcceptanceCriteria.mechanical_run`.
