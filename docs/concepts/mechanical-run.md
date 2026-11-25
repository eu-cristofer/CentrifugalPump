# Mechanical running test

The mechanical run is typically 4 h at rated flow, logged every 15 min.  `pump.mechanical_run`
models the log, checks it against criteria and plots the trends for the report.

## The log

- A `Channel` has a name, a **role** (`vibration_filtered`, `vibration_unfiltered`,
  `bearing_temperature` (bearing metal / outer ring), `oil_temperature` (oil sump),
  `oil_inlet_temperature`, `oil_outlet_temperature`, `housing_temperature` (bearing-housing
  surface), `ambient_temperature`, `oil_pressure`, `seal_pressure`, `flow`,
  `differential_pressure`, `power`, `other`) and an optional bearing **location** ("DE",
  "NDE", ...), which pairs an oil outlet with the oil inlet of the same bearing.
- The log states the **lubrication system** of the bearings: ring-oil / splash,
  pressurized (forced-feed), pure oil mist or grease.  The temperature rules depend on it.
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

  The rule can judge the **rise above ambient** instead of the temperature itself (12th
  8.3.4.2.1), wait for a **warm-up** before the window starts (N-553 rev E 9.20 NOTE 1),
  and be **information only** when the edition runs to stabilisation only "if
  specified".  When the readings are sparser than the window (every 15 min against a
  10 min window), the window reaches back to the last reading before it, so the change
  is taken over at least the window.

For the run: the **duration** (first to last reading) must reach the minimum.

And the **bearing temperature rules** of the lubrication system, across channels:

| Lubrication | Rule | 8th (2.9.2.3) | 11th (6.10.2.4) | 12th (6.10.2.7) | N-553 rev E (7.35 c) |
|---|---|---|---|---|---|
| Pressurized | oil rise, outlet − inlet of each bearing | ≤ 28 K | ≤ 28 K | ≤ 28 K | |
| | bearing metal (if sensors supplied) | < 93 °C | < 93 °C | ≤ 93 °C | |
| | oil outlet, design at 43 °C ambient | < 71 °C *(info)* | < 70 °C *(info)* | | |
| Ring-oil / splash | sump rise above ambient, at each reading | ≤ 39 K | ≤ 40 K | ≤ 39 K | |
| | bearing metal / outer ring (if sensors) | | ≤ 93 °C | ≤ 93 °C | |
| | sump, design at 43 °C ambient | < 82 °C *(info)* | < 82 °C *(info)* | | |
| Pure oil mist | bearing-housing surface | | | ≤ 71 °C | < 70 °C |
| | housing rise above ambient | | | | ≤ 35 K |
| | bearing metal (if sensors) | | | ≤ 88 °C | ≤ 93 °C |
| Grease | housing rise above ambient | | | ≤ 39 K (9.1.2.7) | |
| | housing, design at 43 °C ambient | < 82 °C *(info, 5.1.2.11)* | < 82 °C *(info, 9.1.2.7)* | | |

Where the edition and the client both set a limit, both apply: the stricter one is kept.
The design limits at 43 °C ambient are reported for information; the shop test is judged
on the rises.  A rule whose channels are missing (no oil inlet, no ambient...) is
**not evaluated**; a bearing metal limit without bearing sensors in the log is
information ("if sensors are supplied").  A log without a stated lubrication system
cannot be judged on temperatures at all.

Every check has a status of `pass`, `fail`, `info` or `not evaluated`.  A check without a
configured criterion is `info`, never pass or fail.  The result passes when nothing fails,
and `fully_assessed` is false while the duration or any vibration channel is still
`info`, or any required check (a temperature rule, a required stabilisation) is `not
evaluated`.  The verdict reads `PASSED`, `FAILED` or
`PASSED (not fully assessed)`; with unverified criteria the report adds *(unverified
limits)*.

## The values shipped

| Criterion | Value | Source |
|---|---|---|
| Unfiltered (overall) vibration | 3.0 mm/s RMS, +30 % outside the preferred region | API 610 8th Table 2-5; 11th/12th Table 8 |
| Filtered (discrete) vibration | 2.0 mm/s RMS, +30 % outside the preferred region | same |
| Minimum duration | 4 h at rated flow | 11th 8.3.4.2.2 / 12th 8.3.4.2, *if specified*; the 8th edition has no run test |
| Bearing temperatures | by lubrication system (table above) | 8th 2.9.2.3, 11th 6.10.2.4, 12th 6.10.2.7; N-553 rev E 7.35 c |
| Stabilisation | 12th: rise above ambient ≤ 1 °C over 10 min, *if specified* (information); N-553 rev E: no rise > 2 K in 30 min after a 1 h warm-up (required) | 12th 8.3.4.2.1; N-553 rev E 9.20 |

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
for the RMS readings.  P-9001A's unfiltered 0.16 in/s is 4.06 mm/s; read as RMS, it
**fails** 3.0 mm/s under the 8th edition.

## In the workbench

**MRT Log** holds the readings.  Like Test Points, it offers **standard channels**: pick
the lubrication system and it adds the temperature channels its rules need (oil inlet
and an outlet per bearing; or the sump; or the bearing housings; plus the ambient), wire
the Rated Point and the vibration channels follow the pump type's API 610 measurement
locations, and tick the optional groups (ambient, bearing metal, oil and seal pressure,
power).  Custom channels stay possible, and readings already entered are never dropped.
**MRT Check** judges them.  The check takes the rated point
(edition, client overlay and pump type select the limits), and optionally the fitted
curve (BEP power for the 11th/12th-edition high-speed vibration rule).  Overrides entered
in the check mark the verdict as provisional.

## Worked notebook

[UC-11 - mechanical run](../../use_cases/UC-11_mechanical_run.ipynb): a 4 h log in in/s and degF,
the shipped criteria (not fully assessed), an illustrative full criteria set, and three failures
(a vibration spike, a short run, an unstable oil temperature).

## API

{doc}`API reference <../api/pump>`: `pump.mechanical_run` (`MechanicalRunLog`, `MechanicalRunCriteria`,
`MechanicalRunChecker`, `plot_mechanical_run`) and `pump.acceptance.AcceptanceCriteria.mechanical_run`.
