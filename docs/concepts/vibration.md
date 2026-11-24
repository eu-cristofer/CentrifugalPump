# Vibration: by pump type, and the high-speed chart

API 610 judges **bearing-housing vibration velocity, RMS**, measured at every test point
except shut-off (8th ed. 2.8.3.2; 11th ed. 6.9.3.2).  Each measurement gives two numbers:
- **overall**: the unfiltered reading, 5 Hz to 1 000 Hz;
- **filtered**: the largest *discrete frequency* line in the FFT spectrum.  This is not
  necessarily the pump's 1× running-speed line.

## Where to measure depends on the pump type

Set the **API 610 pump type** on the Rated Point.  The Test Points vibration columns, the
Mechanical Run limits and the test data summary all follow it (`pump.vibration`).

| Type | Measurement locations | Figure |
|---|---|---|
| OH1, OH2 (horizontal overhung) | drive-end and non-drive-end bearing housing; H, V, A | 8th 2-8A · 11th 31 · 12th 32 |
| OH3, OH4, OH5 (vertical in-line) | driver mounting surface; pump bearing housing | 11th 33a · 12th 34a (drawn for OH3) |
| **OH6** (high-speed integrally geared) | **gearbox housing**, stud-mounted sensor | 11th 33b · 12th 34b |
| BB1-BB5 (between bearings) | drive-end and non-drive-end bearing housing; H, V, A | 8th 2-8A · 11th 31 · 12th 32 |
| VS1-VS7 (vertically suspended) | pump thrust bearing housing or motor mounting flange | 8th 2-8B · 11th 32 · 12th 33 |

## Limits

In the **preferred operating region**:

| Family | Overall | Discrete | Clause |
|---|---|---|---|
| OH and BB | 3.0 mm/s RMS | 2.0 mm/s RMS | 8th Table 2-5 · 11th/12th Table 8 |
| VS | 5.0 mm/s RMS | 3.4 mm/s RMS | 8th Table 2-6 · 11th/12th Table 9 |

Outside the preferred region but inside the allowable region, add **30 %**.  Shaft
displacement (pumps with proximity probes) has its own limits and is not handled by the
tool yet.

## The high-speed chart (11th ed. Figure 34, 12th ed. Figure 35)

For OH and BB pumps running **above 3600 r/min or absorbing more than 300 kW per stage**,
the 11th and 12th editions raise the overall limit.  The 8th edition has no such
allowance.

**Method**, as the tool applies it (`pump.vibration.HighSpeedRule`):

1. Take the rated speed *n* (r/min).
2. Take *P*: the power at the **BEP of the rated impeller**, converted to **relative
   density 1.0**, **per stage** (the figure's definition).  The tool uses the fitted curve:
   *P* = power at BEP × 1000 / ρ_test ÷ stages.  Below 300 kW it uses 300 kW, the figure's
   lowest curve.
3. Overall limit: *v_u* = 3.0 · (*n*/3600)^0.30 · (*P*/300)^0.21 mm/s, kept between
   **3.0** and **4.5** mm/s (the figure's "transition from 3.0 to 4.5 mm/s").
4. Discrete limit: *v_f* = **0.67** · *v_u* (Note 2).
5. Round both to **two significant figures**, as the tables require.

The chart draws one curve per power (≤ 300, 500, 700, 1 000, 1 500, 2 000, ≥ 3 000 kW per
stage) against speed on a log axis from 500 to 30 000 r/min, and marks the pump.  The
test data summary includes the chart whenever the rule applies.

**Provenance.** The exponents 0.30 and 0.21 are illegible in the local text conversion of
the standard.  They were reconstructed and checked against the figure's own labels: the
≥ 3 000 kW curve reaches 4.5 mm/s near 2 800 r/min, and the ≤ 300 kW curve leaves 3.0 at
3 600 and reaches 4.5 near 13 900 r/min.  The rule is therefore stored `verified = false`.
Confirm it against the printed figure.

**Example (P-9001, OH6).**  *n* = 10 212 r/min and *P* ≈ 25 kW, so 300 kW is used:
*v_u* = 3.0 · (10 212/3600)^0.30 = **4.1 mm/s**, *v_f* = **2.7 mm/s**.  That applies only
under the 11th/12th editions.  P-9001 is bought to the 8th edition, so its limits stay
3.0 / 2.0 mm/s.

## RMS, peak and the vendor's word

Limits are RMS only.  The Vendor A spectra for P-9001A read "inch/s pk", but the vendor
states that the values are RMS (recorded by the owner on 2026-11-17).  They are entered
as RMS with that provenance noted in the project.

The test data summary also draws **vibration against flow** in the Figure M.4 format: the basic limit across the preferred region, the +30 % limit outside it, and every test point.

Worked exercise: [TR-01](../training/TR-01-witness-performance-test.md), exercise 10.
