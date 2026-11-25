# TR-01 · Witnessing an API 610 performance test

**Goal.** By the end you can say, for any test point the vendor shows you, *which*
tolerance applies, *whether* it passes, and *what to ask* when it is unclear.  The
running example is P-9001 A/B: a Vendor A Model M1 (OH6, integrally geared) to API 610 8th
edition plus Petrobras N-553.

**Companion notebook.** [`use_cases/TR-01_witness_training.ipynb`](../../use_cases/TR-01_witness_training.ipynb)
runs every check below with the `pump` library and asserts the exercise answers.

---

## 1 · Before test day: read the datasheet like an inspector

Write these down; every later judgement depends on them.

| Item | Why | P-9001 |
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
verdict.  Open *Override acceptance criteria…*, tick *Efficiency is guaranteed* and enter
the tolerance only when the contract says so, with the contract reference as the
*Reason*.  Any override puts an `OVERRIDDEN` chip on the node, and the report lists each
changed tolerance next to the criteria default, with your reason.

## 4 · Shut-off head and the rising curve

The shut-off head is predicted at Q = 0.  When no test point lies near Q = 0 it is an
**extrapolation** (no point below 5 % of rated flow): the tool shows the value but does
not judge it, and the verdict is **NOT FULLY ASSESSED** until shut-off is tested or the
omission is waived (§4.1).  Ask whether a shut-off point was taken: the 8th edition lists
shut-off as one of the five minimum test points (4.3.3.2.1), but some pumps may skip it.

When a **rising curve** is specified (always the case with parallel operation):
- the head must rise continuously from rated flow back to shut-off;
- with parallel operation, the head rise to shut-off must be at least **10 %** (8th
  2.1.11; 11th 6.1.11);
- the **negative** shut-off tolerance may be used only if the tested curve still rises
  (note a of the tolerance table).

The tool applies all three when *Parallel operation* is ticked on the Rated Point.

### 4.1 When shut-off was not tested

Not every pump has to be run at shut-off, but skipping it must be justified and agreed
in writing.  What each document says (clause numbers and short phrases only; read your
own copy for the full text):

| Document | Clause | What it says about the shut-off test point |
|---|---|---|
| API 610 8th | 4.3.3.2.1 and its Note | the five points "will normally be" shut-off, minimum flow, …; shut-off "may not be feasible" for **high-energy** (2.1.15) and **multistage** pumps |
| API 610 11th | 8.3.3.3 a) and its Note | same list; the note adds **integral-gear** pumps ("might not be feasible") |
| API 610 12th | 8.3.3.4 | same three pump types, now with a criterion: the **power density** PD = P / (D_imp · D_nozzle²); above a typical **13 MW/m³ (0.286 hp/in³)** it is suggested that the pump not be run at shut-off, because the temperature rises too fast |
| N-553 rev D / rev E | 9.14 / 9.13 (replace item a) of API 8.3.3.3) | "These points **shall be**: 1) shutoff …": the client turns "normally" into "shall" and does not restate the API note, so an exemption needs the client's concurrence |
| N-553 rev E | 6.1.11 (modification) | stable curves "continuous head rise to shutoff" **for all applications**, so the rising-curve question stays open even if the shut-off point is waived |

High-energy means more than 200 m **and** more than 225 kW per stage (8th 2.1.15, 11th
6.1.15).  In the 12th formula, P is the rated power per stage with water, D_imp the
rated impeller diameter and D_nozzle the nominal discharge flange diameter (inlet flange
for double-suction single-stage pumps).

**Worked case (anonymised real FAT, 2026, a P-9001 unit).**  OH6, integrally
geared (gear ratio 2.871), 9.8 m³/h, 333.8 m, 26.9 kW, impeller 125.5 mm, discharge 2 in,
datasheet shut-off head 357.4 m.  The vendor tested six points; the lowest was at
**35 % of rated flow** (3.46 m³/h), so there is no shut-off point.

- *Is the omission defensible?*  Not high-energy (26.9 kW is far below 225 kW), so the
  8th-edition note does not cover it.  It **is** integral-gear (11th, 12th note), and its
  power density is 26.9 kW / (0.1255 m × 0.0508² m²) ≈ **83 MW/m³**, about **6 times**
  the 12th-edition guide value.  So yes under the 11th/12th; under N-553 it still needs
  the client's written concurrence (look for it in the vendor's list of exceptions).
- *Can the shut-off head be judged from the curve?*  **No.**  The tool predicts H(0) by
  extrapolation and flags it.  The answer depends on the fit, not on the pump:

  | Fit | Predicted H(0) | vs 357.4 m (±5 %) |
  |---|---|---|
  | cubic, all six points | 743 m | +108 %, "fail" |
  | cubic, without the run-out point (11.6 m³/h, beyond the end of the curve) | 365 m | +2.1 %, "pass" |
  | quadratic, without the run-out point | 312 m | −12.6 %, "fail" |

  The same choices move the head at rated flow by only 0.5 % (333.2 m vs 331.5 m, both
  inside −2/+2 %).  **Rated-point results are robust; an extrapolated shut-off head is
  not a measurement.**
- *Is there a real concern behind it?*  Yes.  Corrected to rated speed, the head at
  3.5 m³/h (about 367 m) is slightly **below** the head at 6.7 m³/h (about 370 m): the
  curve droops at low flow.  With N-553 rev E's rising-curve rule, ask the vendor for a
  statement (or a shut-off reading) that the head rises to shut-off.

**What to do at the bench**
- Check the contract first: which API edition and which N-553 revision govern, and
  whether the vendor's exceptions list waives the shut-off point.
- Until the omission is agreed, leave the waiver empty: the Compliance node shows the
  shut-off row as **not evaluated** ("shut-off not tested …") and the verdict is
  **NOT FULLY ASSESSED ⚠: Shutoff Head**.  List it as an open point.
- Once it is agreed, type the reason in the Compliance node's **"Shut-off not tested,
  agreed because"** field (pump type, clause, the client's concurrence reference).  The
  row becomes *information* ("waived: …"), the verdict can be **APPROVED ✓ (shut-off not
  tested)**, and the report prints "Shut-off head not tested … Reason: …" under the
  verdict.  The waiver is used only when the shut-off head is extrapolated: a tested
  shut-off point is always judged.
- Do **not** widen the shut-off tolerance with a Compliance override to turn the
  extrapolated value into a pass: an override changes a limit, it does not replace a
  missing measurement.
- Leaving the rated shut-off head blank on the Rated Point skips the check, but the report
  then says nothing about it; use the waiver instead.

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

**Where** you measure depends on the API 610 pump type (set it on the Rated Point):
- OH1/OH2 and BB: drive-end and non-drive-end bearing housings;
- OH3-OH5 (vertical in-line): driver mounting surface and pump bearing housing;
- **OH6 (integrally geared): the gearbox housing**;
- VS: thrust bearing housing or motor mounting flange.

VS pumps have higher limits (5.0 / 3.4 mm/s, Table 9).

The 11th and 12th editions raise the limits for OH and BB pumps above 3600 r/min or
300 kW per stage (Figure 34 / 35):
- overall *v_u* = 3.0·(n/3600)^0.30·(P/300)^0.21, kept between 3.0 and 4.5 mm/s;
- discrete 0.67·*v_u*;
- *P* = BEP power at relative density 1.0, per stage.

The tool applies this rule and draws the chart in the test data summary.  The 8th edition
has no such allowance.  See {doc}`../concepts/vibration`.

N-553 rev E also asks for vibration at each test flow within ±5 % of that flow.

## 7 · The mechanical run

In the workbench the run is two nodes:
- **MRT Log**: type or paste the 15-minute readings.  A new log records the witness
  sheet: time, flow, vibration (overall and filtered) and oil temperature.  The unit of
  each column is picked above it, as in Test Points, and picking another unit converts
  the readings.  Add channels (ΔP, power, bearing temperatures...) if the test sheet has
  them;
- **MRT Check**: wire the log, the rated point and the fitted curve into it.  It gives
  the verdict, the per-channel table (min / max / last / limit) and the trend plot.
  Your own limits (overrides) go here and make the verdict provisional.

Keep the log faithful to the test sheet, and argue about the limits in the check.

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

**The two charts.**  The summary draws its charts in the style of Annex M:
- **Test curve (Figure M.3 format)**: one dotted grid on one flow axis, with every
  quantity on its own scale in its own height band:
  - head (Y1) upper left;
  - efficiency (Y2) lower left;
  - power (Y3) right, middle;
  - NPSH3 (Y4) right, bottom, when the project has an NPSH test.

  Curves are numbered 1-4 and the rated point is marked ◁ on each, with the head
  tolerance as a bar.  Arrow *a* spans the preferred region; arrow *b*, the allowable
  region, is drawn only when the vendor's allowable region is known.  The header repeats
  the pump, the liquid and the rated point, and boxes give the impeller diameters (max /
  rated / min) and the test date.
- **Test points and vibration (Figure M.4 format)**: the head curve with each tested
  point as a star and the region limits hatched.  Under it, vibration against flow, with
  the basic limit across the preferred region and the +30 % limit outside it.  It is drawn
  when the Test Points table has vibration.

Read the second chart first: a point above the red line is a vibration failure, and its
flow tells you which limit applies.  Curves are drawn over the tested range only and are
never extrapolated.

## 9 · Witness checklist

Before the test:
- [ ] Edition, client spec revision, rated point and quoted NPSHr entered.
- [ ] Rising curve / parallel operation and efficiency guarantee settled with the contract.
- [ ] Instrument calibration certificates seen (N-553: type and serial number in the report).

During the test:
- [ ] At least 5 points: shut-off, minimum flow, between minimum and rated, rated, and
  maximum (at least 120 % of BEP) (8th 4.3.3.2.1).  No shut-off point?  Find the
  agreed exemption (high-energy, multistage, integral-gear; 12th power density) and
  record it as an open point (§4.1).
- [ ] Test speed within 3 % of rated.
- [ ] Vibration in **RMS**, at each point except shut-off.
- [ ] NPSH 3 % head-drop data, if specified.

At the end:
- [ ] Head, shut-off, power and test speed inside the bands at the rated flow (Compliance
  node).  **NOT FULLY ASSESSED** means a required check could not be computed: find out
  why (a missing column?) before signing.
- [ ] Efficiency reported; judged only if guaranteed.
- [ ] No `OVERRIDDEN` chip on a Compliance node unless the change is agreed in writing,
  and its reason is filled in (the report prints "Reason: not given" otherwise).
- [ ] NPSH: margin rule and rated NPSH +0 % (NPSH node).
- [ ] Mechanical run: duration, stabilisation, vibration (MRT Log → MRT Check).
- [ ] Report exported (Word / PDF), open points listed, signatures if required.
- [ ] Test data summary exported, blanks completed by hand, signed by vendor and witness.

---

## Exercises

Work them by hand from §2-§7, then check with the notebook.

1. A pump is rated at **120 m**.  Give the head band and the shut-off band under API 610
   8th, then under the 11th.
2. P-9001A, API 610 8th: rated 333.8 m, predicted at rated flow **339.5 m**.  Pass?  By
   how much margin?  Would the answer change under the 11th edition?
3. Same pump: rated power **26.9 kW**, predicted **24.6 kW**.  Pass?
4. Rated efficiency **32.7 %**, test **31.5 %** (−3.7 %), driver 37 kW, API 610 8th +
   N-553 rev E.  Accept or reject?
5. NPSHa **2.4 m**, tested NPSH3 at rated flow **1.6 m**, quoted NPSHr **1.5 m**, N-553
   rev E.  Judge the margin rule and the rated-NPSH rule.  Is anything else required?
6. The Vendor A sheet shows unfiltered vibration **0.16 in/s** at a point inside the
   preferred operating region.  What is the verdict if that is RMS?  And if it is true peak?
7. Rated speed **10 212 rpm**, test speed **10 301 rpm**.  Acceptable?
8. Parallel operation is specified.  The predicted shut-off head is **3 % below** the rated
   shut-off head (rated head 333.8 m), but the fitted curve droops: the head at 40 % of
   rated flow is higher than at Q = 0.  Pass?

9. The BEP flow of the tested curve is 10 m³/h and rated flow is 10 m³/h.  DE overall
   vibration (RMS): 2.8 mm/s at 5 m³/h, 2.1 at 9.9, 2.6 at 11.0 and 3.4 at 12.5 m³/h
   (shut-off not measured).  Fill in the summary's three columns, tested vs specified.
10. An OH6 pump bought to API 610 12th edition runs at **10 212 r/min**, with about 25 kW
   at BEP (relative density 1.0).  Gearbox-housing readings: overall 3.84, largest
   discrete line 2.24 mm/s RMS.  Which limits apply, and does it pass?  And under the
   8th edition?
11. The worked case of §4.1 (OH6, integrally geared, 26.9 kW, impeller 125.5 mm,
   discharge 2 in, lowest test point at 35 % of rated flow, API 610 8th + N-553 rev E).
   Older versions of the tool reported the shut-off head as **743 m, fail
   (extrapolated)** against 357.4 m.
   Is the pump rejected?  Compute the 12th-edition power density.  What do you write in
   the report?

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
10. P = 25 kW is below 300, so use 300: *v_u* = 3.0·(10 212/3600)^0.30 = **4.1 mm/s**,
   *v_f* = 0.67·4.1 = **2.7 mm/s**.  3.84 ≤ 4.1 and 2.24 ≤ 2.7, so it **passes** under the
   12th edition.  Under the 8th edition there is no high-speed allowance: the limits are
   3.0 / 2.0 mm/s and it **fails** both.  This is P-9001A's real situation.
11. **Not rejected on that row, and not accepted on it either.**  The 743 m is an
   extrapolation from 35 % of rated flow to zero; other reasonable fits give 312-365 m,
   so it says nothing about the pump.  PD = 0.0269 MW / (0.1255 m × 0.0508² m²) ≈
   **83 MW/m³** (1.8 hp/in³), about 6 times the 13 MW/m³ guide value, and the pump is
   integral-gear: the 11th/12th notes support skipping shut-off.  Under the 8th edition
   alone it is neither high-energy nor multistage, and N-553 says "shall", so the
   omission needs the client's written concurrence.  In the report: shut-off head **not
   tested**, reason and concurrence reference, plus an open point on the rising curve
   (N-553 rev E), because the head at 35 % of rated flow is slightly below the head at
   68 %.  Do not override the tolerance to make the row pass.  In the tool: without a
   waiver the verdict is **NOT FULLY ASSESSED ⚠: Shutoff Head**; with the agreed reason
   in "Shut-off not tested, agreed because" it is **APPROVED ✓ (shut-off not tested)**
   and the report prints the reason.
