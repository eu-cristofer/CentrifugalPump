# TR-01 · Witnessing an API 610 performance test

**Goal.** By the end you can say, for any test point the vendor shows you, *which*
tolerance applies, *whether* it passes, and *what to ask* when it is unclear.  The
running example is B-34004 A/B: a Sundyne LMV-311 (OH6, integrally geared) to API 610 8th
edition plus Petrobras N-553.

**Companion notebook.** [`use_cases/TR-01_witness_training.ipynb`](../../use_cases/TR-01_witness_training.ipynb)
runs every check below with the `pump` library and asserts the exercise answers.

---

## 1 · Before test day: read the datasheet like an inspector

Write these down; every later judgement depends on them.

| Item | Why | B-34004 |
|---|---|---|
| API 610 **edition** | the tolerance bands differ between editions (§2) | 8th |
| Client spec and **revision** | the overlay adds the NPSH margin, stabilisation, efficiency | N-553 **rev C** (the tool has rev E: note the gap) |
| Rated Q, H, N, P, SG, viscosity | the rated point the curve is judged at | 9.80 m³/h, 333.8 m, 10 212 rpm, 26.9 kW, 0.999, 0.52 cSt |
| Shut-off head | judged at Q = 0 | 357.4 m |
| NPSHa and **quoted NPSHr** | margin rule and rated-NPSH rule (§5) | NPSHa 2.4 m |
| Rising curve / parallel operation specified? | changes the shut-off rule (§4) | no |
| Efficiency guaranteed? | otherwise efficiency is information only (§3) | no (37 kW driver) |
| Impeller rated / max / min | trim limits, catalogue | 128 / 131 / 125 mm |

In the workbench: enter these in **Rated Point** (the ⓘ next to *Impeller diameter*
explains the three diameters), pick *Standard / edition* = API 610 8th and *Client
overlay* = N-553.

## 2 · Which tolerance applies

All checks use the curve fitted through the test points, corrected to rated speed and
density, and evaluated **at the rated flow**.  Single raw points are not judged.  The 12th
edition says so explicitly: a least-squares spline or polynomial, typically third order or
higher, for head and power, then corrected for speed, viscosity and density.

| | API 610 8th (Table 4-2) | API 610 11th / 12th (Table 16) |
|---|---|---|
| Rated head, 0-150 m | −2 / +5 % | ±3 % |
| Rated head, 150-300 m | −2 / +3 % | ±3 % |
| Rated head, > 300 m | −2 / +2 % | ±3 % |
| Shut-off, ±10 % up to | 150 m rated head | 75 m rated head |
| Shut-off, ±8 % up to | 300 m | 300 m |
| Shut-off, ±5 % above | 300 m | 300 m |
| Rated power | +4 % | +4 %, from all causes |
| Efficiency | "not a rating value" | not rated unless the purchaser specifies it (note c) |
| Rated NPSH | +0 % | 0 % |

Three traps:
1. **The band is chosen by the rated head**, also for the shut-off check, never by the
   shut-off head.
2. **The edges move between editions.**  A 120 m pump has ±10 % at shut-off under the
   8th, but ±8 % under the 11th.
3. **No cumulative tolerances.**  The +4 % on power is after correcting for flow, speed,
   density and viscosity, from all causes together.

Also check the **test speed**: within 3 % of the rated speed unless otherwise agreed (8th
4.3.3.2.3; 11th 8.3.3.3 c).  The Compliance node shows it as the *Test speed* row, judged
on the worst point.  N-553 rev E adds that, for a fixed-speed motor, results are
corrected to the actual driver speed.

## 3 · Efficiency is not a pass/fail item (usually)

API 610 does not rate efficiency.  The 12th edition gives the reason: test efficiency is
uncertain by about ±2.5 %.  So an efficiency 3 % below the datasheet is **not** a
rejection unless the purchase order specified an efficiency tolerance.  N-553 rev E 9.14
does that only for drivers of **1 MW or more** (−0 %).

In the workbench the Compliance node shows efficiency as `info` and leaves it out of the
verdict.  Tick *Efficiency is guaranteed* and enter the tolerance only when the contract
says so.

## 4 · Shut-off head and the rising curve

The shut-off head is predicted at Q = 0.  When no test point lies near Q = 0 it is an
**extrapolation**; the tool flags it (no point below 5 % of rated flow).  Ask whether a
shut-off point was taken: the 8th edition lists shut-off as one of the five minimum test
points (4.3.3.2.1), but high-energy pumps may skip it.

When a **rising curve** is specified (always the case with parallel operation):
- the head must rise continuously from rated flow back to shut-off;
- with parallel operation, the head rise to shut-off must be at least **10 %** (8th
  2.1.11; 11th 6.1.11);
- the **negative** shut-off tolerance may be used only if the tested curve still rises
  (note a of the tolerance table).

The tool applies all three when *Parallel operation* is ticked on the Rated Point.

## 5 · NPSH: two separate rules

| Rule | From | Test |
|---|---|---|
| Rated NPSH +0 % | API 610 | NPSH3 tested at rated flow ≤ the **quoted** NPSHr |
| NPSH margin | the client | N-553 rev E 7.3: NPSHa − NPSHr ≥ 0.8 m **and** NPSHa/NPSHr ≥ 1.15, at rated flow |

NPSH3 is the NPSHa at which the head has dropped 3 % at constant flow.  N-553 rev E (9.22
note) asks for NPSHr at **every** test point when the margin is below 1 m or the ratio
below 1.20.  Rev D's rule is different (0.8 m or ratio 1.25, whichever is greater, across
the whole range), so the revision matters.

## 6 · Vibration: RMS only

The API 610 bearing-housing limits are **RMS**.  For OH and BB pumps in the preferred
operating region the limits are 3.0 mm/s overall and 2.0 mm/s at discrete frequencies.
Outside the preferred region but inside the allowable region they may be 30 % higher.

The 8th edition (2.8.3.7 note) states that true-peak values are for information only and
are not used for acceptance.  When US units are specified, true peak is recorded **in
addition** (4.3.3.3.1).  A sheet in **in/s** must therefore say which it is.  Never divide
a peak value by √2 to get RMS: that only holds for a pure sine wave.

The 11th and 12th editions raise the limits for pumps above 3600 r/min or 300 kW per stage
(Figure 34 / 35).  The 8th edition has no such allowance.  The tool does not apply the
11th/12th allowance yet, so its limits are conservative for high-speed pumps.

N-553 rev E also asks for vibration at each test flow within ±5 % of that flow.

## 7 · The mechanical run

- **Duration.**  The 8th edition has no mechanical running test.  The 11th/12th run 4 h at
  rated flow *if specified*.  N-553 rev E 9.21 requires 4 h when ndm ≥ 350 000 or the
  energy-density criterion is met.
- **Stabilisation.**  N-553 rev E 9.20 requires at least a 1 h warm-up, then oil and
  bearing temperatures are stable when they rise no more than 2 K in 30 min.  The tool
  checks this from the log.
- **Bearing temperatures** (11th 6.10.2.4): with pressurised oil, the outlet is below 70 °C
  and the oil rise at most 28 K; with ring-oil or splash lubrication, the sump is below
  82 °C and the rise at most 40 K above ambient.

## 8 · The test data summary (Annex M / 8th App. T)

The 11th/12th editions give an example *test data summary* form in Annex M; the 8th
edition has the same form as Appendix T.  It is the one-page record the vendor certifies
and the purchaser's witness signs:
- the header: customer, purchaser, order, item, serial, size and type, stages, curve no.,
  test date, signatures;
- overall hydraulic performance at rated flow (flow, head, power, NPSH3, shut-off head,
  speed): rated, tested, deviation and acceptance tolerance;
- pump construction data (impeller diameter, patterns, vanes, blade-tip clearance);
- mechanical performance: maximum bearing-housing vibration (RMS) at rated flow and in the
  preferred and allowable operating regions, tested vs specified;
- bearing temperatures, and the test curve.

In the workbench: *Report Export ▸ Export test data summary* writes it as Word, LaTeX,
PDF and Excel, one page per pump; the CLI flag is `--summary`.  Values the project holds
are filled in.  Blank fields are things the project does not know (order number, patterns,
vanes, ambient temperature): write them in by hand rather than guess.

To fill the three vibration columns, tick *Vibration columns* in the Test Points table and
enter the RMS readings at each point (drive end / non-drive end, overall / filtered):
- **rated flow** is the maximum over points within ±5 % of rated flow;
- **preferred region** is 70-120 % of the BEP flow of the tested curve;
- **allowable region** covers every point except shut-off, with the specified limit +30 %.

Without per-point readings, the rated-flow column falls back to the mechanical run.

## 9 · Witness checklist

Before the test:
- [ ] Edition, client spec revision, rated point and quoted NPSHr entered.
- [ ] Rising curve / parallel operation and efficiency guarantee settled with the contract.
- [ ] Instrument calibration certificates seen (N-553: type and serial number in the report).

During the test:
- [ ] At least 5 points: shut-off, minimum flow, between minimum and rated, rated, and
  maximum (at least 120 % of BEP) (8th 4.3.3.2.1).
- [ ] Test speed within 3 % of rated.
- [ ] Vibration in **RMS**, at each point except shut-off.
- [ ] NPSH 3 % head-drop data, if specified.

At the end:
- [ ] Head, shut-off, power and test speed inside the bands at the rated flow (Compliance
  node).  **NOT FULLY ASSESSED** means a required check could not be computed: find out
  why (a missing column?) before signing.
- [ ] Efficiency reported; judged only if guaranteed.
- [ ] NPSH: margin rule and rated NPSH +0 % (NPSH node).
- [ ] Mechanical run: duration, stabilisation, vibration (Mechanical Run node).
- [ ] Report exported (Word / PDF), open points listed, signatures if required.
- [ ] Test data summary exported, blanks completed by hand, signed by vendor and witness.

---

## Exercises

Work them by hand from §2-§7, then check with the notebook.

1. A pump is rated at **120 m**.  Give the head band and the shut-off band under API 610
   8th, then under the 11th.
2. B-34004A, API 610 8th: rated 333.8 m, predicted at rated flow **339.5 m**.  Pass?  By
   how much margin?  Would the answer change under the 11th edition?
3. Same pump: rated power **26.9 kW**, predicted **24.6 kW**.  Pass?
4. Rated efficiency **32.7 %**, test **31.5 %** (−3.7 %), driver 37 kW, API 610 8th +
   N-553 rev E.  Accept or reject?
5. NPSHa **2.4 m**, tested NPSH3 at rated flow **1.6 m**, quoted NPSHr **1.5 m**, N-553
   rev E.  Judge the margin rule and the rated-NPSH rule.  Is anything else required?
6. The Sundyne sheet shows unfiltered vibration **0.16 in/s** at a point inside the
   preferred operating region.  What is the verdict if that is RMS?  And if it is true peak?
7. Rated speed **10 212 rpm**, test speed **10 301 rpm**.  Acceptable?
8. Parallel operation is specified.  The predicted shut-off head is **3 % below** the rated
   shut-off head (rated head 333.8 m), but the fitted curve droops: the head at 40 % of
   rated flow is higher than at Q = 0.  Pass?

9. The BEP flow of the tested curve is 10 m³/h and rated flow is 10 m³/h.  DE overall
   vibration (RMS): 2.8 mm/s at 5 m³/h, 2.1 at 9.9, 2.6 at 11.0 and 3.4 at 12.5 m³/h
   (shut-off not measured).  Fill in the summary's three columns, tested vs specified.

## Answers

1. **8th:** head −2/+5 % (0-150 m); shut-off ±10 % (up to 150 m).  **11th:** head ±3 %;
   shut-off ±8 % (75-300 m).
2. δ = (339.5 − 333.8)/333.8 = **+1.71 %**, inside −2/+2 %, so it **passes**, with 0.29
   percentage points left.  Under the 11th (±3 %) it passes with more room.
3. δ = (24.6 − 26.9)/26.9 = **−8.6 %**, below the +4 % limit, so it **passes**.  A power
   lower than rated is not a defect.
4. **Not judged.**  API 610 does not rate efficiency, and N-553 rev E sets −0 % only for
   drivers of 1 MW or more.  Report it for information and raise it as a comment if it
   matters to the client.
5. Margin 2.4 − 1.6 = 0.8 m ≥ 0.8 ✓; ratio 2.4/1.6 = 1.50 ≥ 1.15 ✓; but NPSH3 1.6 m >
   quoted 1.5 m, so **rated NPSH +0 % fails** and the NPSH verdict fails.  Also, because the
   margin is below 1 m, N-553 rev E asks for NPSHr at every test point except shut-off.
6. 0.16 in/s = **4.06 mm/s**.  If RMS: above 3.0 mm/s, so it **fails**.  If true peak: it
   **cannot be used** for acceptance (8th 2.8.3.7 note), so ask for the RMS readings; do not
   estimate RMS as peak/√2.
7. (10 301 − 10 212)/10 212 = **+0.87 %**, within 3 %, so it is acceptable.  Results are
   still corrected to 10 212 rpm.
8. −3 % is inside the ±5 % band (rated head above 300 m), **but** a negative shut-off
   tolerance is allowed only if the curve still rises to shut-off.  It does not, so it
   **fails**.  Parallel operation also needs a head rise of at least 10 % from rated to
   shut-off, so check that too.
9. Rated flow (within ±5 %): **2.1 / 3.0**.  Preferred region (7-12 m³/h): **2.6 / 3.0**.
   Allowable region (every point except shut-off): **3.4 / 3.9**.  The 12.5 m³/h point is
   outside the preferred region, so it is judged against 3.0 × 1.3 = 3.9 mm/s.
