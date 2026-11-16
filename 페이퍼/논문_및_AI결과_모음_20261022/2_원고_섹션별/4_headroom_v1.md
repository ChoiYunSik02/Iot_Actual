# 4. How much can be gained by setting the damper in advance?

> Draft v1 (2026-10-22), replaces the Oracle part of `03_본론_구조.md` (old Chapter 4). All numbers are from the present model with the literal rotation law (Eq. 5): `페이퍼/코드/README_v2_20261022.md`, `results/ai_eval_v2_cos2.json`, `results/exp_switch_cos2.json`, `results/exp_switch2_cos2.json`.

## 4.1 Reference strategies

All strategies use the original damping law (orifice switching, 1 s) and differ only in how the damper frequency f and the turntable angle θ are chosen. The mean reduction of the six indices of Section 3 is the performance measure, averaged over the eleven records. The strategies are listed in Table 5.

**Table 5.** Reference strategies compared in Sections 4 and 5.

| Label | Strategy | Needs the earthquake? |
|---|---|---|
| E1b | passive TLCD detuned to 0.3204 Hz (no rotation) | no |
| E2 | original RS-TLCD, wavelet identification after the building responds | no |
| Fixed | RS-TLCD set from t = 0 to one (f, θ) cell, the same for all earthquakes; the cell with the highest mean label score of the training data (Section 5.2), excluding the earthquake under test | no |
| Oracle | for each record the best of 49 cells (7 frequencies in the tunable range × 7 angles, 0–90°), set from t = 0 | yes — not realisable |

The Oracle is the upper bound of *constant* settings only; Section 4.4 treats settings that change once during the event.

## 4.2 Results

**Table 6.** Mean reduction (%) over eleven records. Building stiffness ×0.9025, ×1, ×1.1025 corresponds to a fundamental frequency of 0.3204, 0.3373, 0.3542 Hz (stiffness loss or gain).

| Building | E1b | E2 | Fixed | Oracle | Fixed − E2 | Oracle − Fixed |
|---|---|---|---|---|---|---|
| 0.3204 Hz (×0.9025) | 15.93 | 16.17 | 18.34 | 21.65 | 2.17 | 3.31 |
| 0.3373 Hz (×1) | 13.36 | 14.04 | 15.81 | 17.60 | 1.77 | 1.80 |
| 0.3542 Hz (×1.1025) | 13.32 | 13.25 | 14.78 | 15.99 | 1.53 | 1.22 |

Two findings follow.

1. **A constant (f, θ) set before the earthquake is ahead of identifying the frequency afterwards, in direction.** The Fixed cell of Table 6 is chosen without the earthquake under test (highest mean label score of the training data), so it is deployable; the record-averaged Fixed − E2 is 1.5–2.2 points, but averaged over the seven earthquakes it is +1.31 ± 1.20 (nominal, 5 of 7 earthquakes), +1.71 ± 1.52 (0.3204 Hz, 3 of 7) and +1.00 ± 0.67 (0.3542 Hz, 5 of 7). If the cell is instead chosen from the real records of the other earthquakes, the nominal building gives +0.84 ± 1.24 points (5 of 7); the sign is the same under the other rotation laws (+1.52 ± 0.77, +2.20 ± 1.46) and damping scalings (+0.74 ± 1.05 at ×20, +0.68 ± 1.18 at ×40), but for the adopted model the difference is within one standard error. If the fixed setting may use a ±20% range while the original device keeps ±5%, the difference is −0.39 ± 0.70. In the first 8 s after the trigger the fixed setting reduces the peak roof displacement by 5.10% against 3.92% for the original logic, consistent with the original logic acting only after the building has responded.
2. **Knowing the earthquake would add a further 1.2–3.3 points** (Oracle − Fixed), which is the maximum that a predictor choosing one constant per earthquake could gain. It is largest when the building is softer than designed (3.3 points at 0.3204 Hz).

The Oracle is not an upper bound for strategies outside the 49 constant cells. For the nominal building the original RS-TLCD, whose frequency and angle change during the event, exceeds the Oracle on Pacoima Dam (22.01% vs 20.78%) and KJMA (18.94% vs 17.35%), and the detuned passive TLCD, whose orifice is not switched, exceeds it on Aeropuerto Mexicali (24.03% vs 22.95%) and El Centro Differential Array (22.74% vs 22.38%) (Fig. 4). The first observation shows that a setting that varies in time can outperform every constant setting on some records (Section 4.4); the second, that the semi-active damping law, which all RS-TLCD strategies share, is not beneficial on every record. Both effects lie outside what a choice of a constant (f, θ) can recover and are not counted in the headroom of Section 4.3.

## 4.3 Where the headroom is

For the nominal building and the fixed cell chosen on the eleven records themselves (a choice favourable to the fixed strategy), the best constant is (0.3542 Hz, 45°) with 15.83%, and the Oracle gives 17.60%, i.e. 1.77 points of headroom:

- **Frequency alone** (θ fixed at its best value): 0.73 points. **Angle alone** (f fixed): 0.81 points. In the printed model the two are coupled, because the damper frequency projected on each axis is ω_d√(cos θ) (Section 3.2); the best fixed frequency is the upper bound of the tunable range.
- The mean reduction depends strongly on the angle: 7.6, 11.4, 15.3, 15.8, 10.2, 6.7, 3.5% at θ = 0, 15, 30, 45, 60, 75, 90° (f = 0.3542 Hz). The Oracle angle is 30° for eight records and 45° for three; the Oracle frequency is the upper bound for seven records.
- The headroom is unevenly distributed. The loss of the best fixed cell relative to the Oracle is 7.4 points for Pohang 2017, 2.5 (El Centro Array #11), 2.1 (El Centro 1940), 2.0 (KJMA), 2.0 (El Centro Array #3), 1.3 (Pacoima Dam), 1.0 (Brawley), 0.8 (CHY006), 0.4 (Gyeongju) and 0 for the Mexicali and Differential Array stations. A single record (Pohang 2017) accounts for a large part of the mean headroom.

**Caveat.** At θ = 45° the printed model gives each direction 0.71 m_d of liquid mass and a frequency of ≈ 0.84 ω_d, so the best constant detunes the damper below the building frequency. This is a property of Eq. (5) as printed (Section 3.2), not a design recommendation.

## 4.4 Settings that change once during the event

A constant setting is not the only way to use advance knowledge: a damper kept at its standby state (0.3373 Hz, 0°) during the strong motion and switched afterwards may perform differently. We evaluated a single switch from the standby state to a cell (f, θ) at a time t_s, and searched the 49 cells for each switching rule.

*Switch at a fixed delay after the trigger (0.5 gal).* With t_s = trigger + 8 s the best constant cell reaches 17.18% (vs 15.83% for a constant from t = 0), and the per-record maximum over cell and delay is 19.48%, i.e. 3.65 points above the best constant. For the same cell the gain is concentrated in three Imperial Valley stations and Pacoima Dam (Differential Array +9.2, Mexicali +5.8, Pacoima +2.8, Brawley +1.7 points at 8 s), while El Centro Array #11 (−0.5), KJMA (−6.0), El Centro 1940 (−0.4) and Gyeongju (−1.8) lose and Pohang is unchanged.

*Is this realisable and does it generalise?* Strong motion starts 2–25 s after the trigger in these records, so a delay after the trigger is not a physical reference. We therefore tested causal rules that use only the past ground acceleration: a delay after the strong-motion onset (peak so far ≥ 0.1 m/s², about 30% of the scaled peak), the time since the running peak was last exceeded, and the decay of the 2-s mean-square acceleration relative to its running maximum. The cell was chosen on the training earthquakes only and evaluated on the held-out one (leave-one-earthquake-out; seven earthquakes, Imperial Valley records treated as one).

**Table 7.** Switching rules, nominal building. Post-hoc: best cell on all eleven records. Difference to the constant setting: mean over the seven earthquakes ± standard error.

| Rule | Post-hoc (%) | Difference to constant, leave-one-earthquake-out (points) | Earthquakes improved |
|---|---|---|---|
| constant from t = 0 | 15.83 | — | — |
| trigger + 8 s | 17.18 | +0.16 ± 1.45 | 4/7 |
| trigger + 12 s | 16.38 | +0.03 ± 0.81 | 3/7 |
| trigger + 24 s | 11.24 | −3.63 ± 1.10 | 1/7 |
| onset + 5 s | 16.80 | +0.18 ± 1.20 | 5/7 |
| onset + 8 s | 16.63 | −0.22 ± 1.17 | 3/7 |
| 2-s energy falls to 50% of its maximum | 17.12 | −0.11 ± 1.32 | 4/7 |
| peak not exceeded for 5 s | 17.33 | +0.01 ± 1.48 | 3/7 |
| best rule chosen by cross-validation among 16 | — | −0.89 ± 1.06 | 2/7 |

No rule improves on the constant setting beyond the uncertainty. In-sample differences of 1.4–2.3 points per record come mostly from records of one earthquake (Imperial Valley, five of eleven records) and Pacoima Dam; when that earthquake is left out, the constant cell chosen on the remaining earthquakes also performs poorly on it (12.0% on the Differential Array, against 22.4% for the best cell), so the record-level comparison overstates the differences. Switching too late is harmful (−1.2 points at trigger + 16 s, −3.6 at + 24 s). **We therefore regard the time-varying headroom as an upper bound that we could not realise with a causal rule, and we do not claim it.**

## 4.5 Summary and limitations

- A constant pre-set damper is ahead of the original post-hoc identification in direction (1.5–2.2 points averaged over records; +1.31 ± 1.20 and +0.84 ± 1.24 over earthquakes for the nominal building, with two ways of choosing the constant), but the difference is not resolved at the event level.
- Perfect knowledge of the earthquake would add 1.2–3.3 points if one constant per earthquake is chosen; the headroom is concentrated in a few records.
- These values are for the present model (Section 3.3): the RS-TLCD reproduction is 2.7 points below the original, and the Oracle is evaluated on eleven records from seven earthquakes. Differences below about 1 point between strategies cannot be resolved.
- The fixed strategy and the Oracle use the 35 cm/s² scaling of the original study; the ±20% tunable range was recomputed with the literal rotation law (Section 4.2) and removes the advantage of the fixed setting over the original device.

*TODO: Fig. — mean reduction vs θ and vs f (heat map of the 7 × 7 score map, nominal building); Fig. — per-record Oracle and fixed reductions; recompute the ±20% range with Eq. (5).*
