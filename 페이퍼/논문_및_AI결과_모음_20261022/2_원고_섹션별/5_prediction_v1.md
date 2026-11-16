# 5. Predicting the damper setting from the early ground motion

> Draft v1 (2026-10-22), replaces old Chapter 5 and the AI part of old Chapter 7 in `03_본론_구조.md`. Numbers: `페이퍼/코드/results/ai_eval_v2_cos2.json`, produced by `gen_labels_v2.py` and `train_ai_v2.py` (literal rotation law, Eq. 5). Earlier results with the previous rotation law (`README.md`, 2026-10-21) are superseded.

## 5.1 Problem

The learning task is to choose the constant damper setting (f, θ) from the first T_obs seconds of the ground motion after the trigger, so that the reduction of Section 3 is maximised. This is stated as the prediction of the setting that would have performed best, not of the frequency of the incoming motion: the two coincide only if the best setting is determined by the frequency content of the earthquake, which Section 4.3 shows to be only partly the case (the best constant is the upper bound of the tunable range, and the angle matters as much as the frequency).

## 5.2 Training data and labels

A sample consists of a bi-directional ground motion and a building stiffness multiplier k ∈ [0.81, 1.21] (fundamental frequency ±10%). Each sample is labelled with the 7 × 7 map of mean reductions obtained by simulating all 49 constant settings of Section 4.1 (49 simulations per sample); the network learns the map minus its sample mean, so that a poor prediction of the best cell still tends to choose a good neighbouring cell.

- 1,489 synthetic ground motions: Kanai–Tajimi spectrum with Clough–Penzien high-pass filtering applied to white noise, ground frequency 0.5–8 Hz (log-uniform), ground damping 0.2–0.6, duration 15–40 s, Jennings-type envelope, X–Y correlation 0–0.6, intensity ratio 0.5–1.
- 511 variants of the real records: horizontal rotation by 0–180° and time scaling by 0.7–1.4 (which shifts the dominant frequency).
- All samples are scaled to 35 cm/s² per component, with 10 s of free vibration appended.

## 5.3 Input and model

Input (69 values), computed from the first T_obs seconds after the trigger (0.5 gal): log Fourier amplitude of each horizontal component in 32 geometric bands between 0.1 and 5 Hz, normalised to the maximum (64); the logarithm of the peak acceleration of X and of the Y/X peak ratio; sin 2φ and cos 2φ of the principal axis of the two components; and the relative change of the building's fundamental frequency (assumed known from ambient vibration). Model: a fully connected network 69–64–64–(49), ReLU, trained with AdamW (learning rate 2 × 10⁻³, weight decay 10⁻³), mean-square loss on the label map, 400 epochs, the epoch with the lowest loss on a 1/7 validation split is kept. No hyper-parameter search was made.

## 5.4 Evaluation protocol

- **Leave-one-earthquake-out.** For each test record, all records of the same earthquake and all variants derived from them are removed from the training set (the five Imperial Valley stations are one group). Eleven networks are trained per seed.
- **Constant baseline.** The constant cell is the one with the highest mean label score on the same training set, so it is as deployable as the network.
- **Five training seeds**; seed variability is reported separately from the variability across earthquakes.
- **Two ways of applying the prediction.** *Preset*: the predicted cell is applied from t = 0, as if early-warning or other prior information supplied the first T_obs seconds; this is an idealisation. *Online*: the damper stays at its standby state (0.3373 Hz, 0°) and the command is issued at trigger + T_obs, with the pump (2.6 s) and the turntable (30°/s) dynamics of the original design.
- T_obs = 1, 3, 5 s; building 0.3204, 0.3373, 0.3542 Hz.
- Differences between methods are averaged over the seven earthquakes and reported as mean ± standard error across earthquakes.

## 5.5 Results

**Table 8.** Mean reduction (%) over eleven records; AI columns: mean ± standard deviation over five seeds. The constant, E2 and Oracle values are in Table 6. Last two columns: difference to the constant setting (points), mean ± standard error over the seven earthquakes.

| Building (Hz) | T_obs (s) | AI preset | AI online | Preset − Fixed | Online − Fixed |
|---|---|---|---|---|---|
| 0.3204 | 1 | 18.29 ± 0.30 | 17.76 ± 0.30 | +0.74 ± 0.46 | −0.16 ± 0.64 |
|  | 3 | 18.42 ± 0.70 | 18.48 ± 0.53 | +0.55 ± 0.45 | −0.18 ± 0.80 |
|  | 5 | 18.28 ± 0.31 | 18.34 ± 0.31 | +0.31 ± 0.37 | −0.81 ± 1.30 |
| 0.3373 | 1 | 15.21 ± 0.25 | 14.89 ± 0.25 | −0.01 ± 0.37 | −0.57 ± 0.44 |
|  | 3 | 15.58 ± 0.25 | 15.64 ± 0.15 | −0.06 ± 0.19 | −0.65 ± 0.46 |
|  | 5 | 15.55 ± 0.16 | 15.87 ± 0.17 | −0.06 ± 0.12 | −1.00 ± 0.94 |
| 0.3542 | 1 | 14.56 ± 0.15 | 14.25 ± 0.11 | +0.10 ± 0.26 | −0.43 ± 0.40 |
|  | 3 | 14.46 ± 0.26 | 14.62 ± 0.27 | −0.26 ± 0.20 | −0.87 ± 0.65 |
|  | 5 | 14.79 ± 0.27 | 15.34 ± 0.14 | −0.32 ± 0.28 | −1.08 ± 1.14 |

The mean of the nine conditions is +0.11 points (preset) and −0.64 points (online) relative to the constant setting, with no condition in which an improvement exceeds its standard error by a clear margin; the largest, +0.74 ± 0.46 points, is within two standard errors and is one of nine comparisons. Averaged over records instead of earthquakes the differences are −0.18 and −0.17 points, with the preset better than the constant in 2 to 8 of the 11 records depending on the condition.

Further observations:

- **The network does not recover headroom beyond the constant.** The constant setting alone recovers 40–56% of the gap between E2 and the Oracle (1.5–2.2 of 2.7–5.5 points, record average; see Section 4.2 for the event-level uncertainty); the preset networks recover 33–56% of the same gap (Table 9). Expressing the result as "share of the Oracle gain recovered" relative to the original method would credit the network with a gain that a constant also provides.
- **The network had more information than the constant and still did not gain.** The constant cell is chosen once from the training labels of all building states, whereas the network receives the change of the building frequency as an input (Section 5.3). Knowledge of the building state therefore did not translate into a better choice of (f, θ) either.
- **Observation time has no systematic effect.** The preset results at 1, 3 and 5 s differ by at most 0.4 points for a given building (e.g. 15.21, 15.58 and 15.55% for the nominal building), comparable to the seed standard deviation (0.1–0.7), and they do not increase monotonically with T_obs. Averaged over records the online and preset variants are within 0.6 points of each other, but averaged over earthquakes the online variant is below the constant setting in all nine conditions (−0.16 to −1.08 points). The frequency of the Oracle cell is predicted with an error of 6–15 mHz, i.e. 18–43% of the 34 mHz tunable range, for all T_obs.
- **One apparent gain is an artefact of the Oracle definition.** For the stiffer building at T_obs = 5 s the online variant exceeds the constant by +0.57 points when averaged over records, but −1.08 ± 1.14 points over earthquakes; the record average is dominated by El Centro Differential Array, where the delayed switch exceeds even the Oracle of constant settings (26.9% vs 17.3%). This is the delayed-switch effect of Section 4.4, which does not generalise across earthquakes.
- **Korean records.** For the softer building the network exceeds the constant by 1.4–2.0 points on Pohang and Gyeongju (preset, mean of the two records), and is within ±0.3 points for the other two building states. This is two records and cannot be distinguished from variability across seeds and records; Pohang also has the largest headroom (Section 4.3).

**Table 9.** Share of the gap between the original RS-TLCD (E2) and the Oracle that each strategy closes (record averages; AI = mean of five seeds). Gap = Oracle − E2 (points).

| Building (Hz) | Gap | Constant | AI preset (1/3/5 s) | AI online (1/3/5 s) |
|---|---|---|---|---|
| 0.3204 | 5.48 | 40% | 39 / 41 / 38% | 29 / 42 / 40% |
| 0.3373 | 3.56 | 50% | 33 / 43 / 42% | 24 / 45 / 51% |
| 0.3542 | 2.75 | 56% | 48 / 44 / 56% | 36 / 50 / 76% |

The constant closes 40–56% of the gap without any information about the earthquake. The 76% of the online variant (stiffer building, 5 s) is the case discussed above that turns into −1.08 ± 1.14 points relative to the constant at the earthquake level.

## 5.6 Discussion

The result is that, with the information of 1–5 s of ground motion, the network did not select a setting better than the constant one. We see three reasons, none of which we claim to be proven.

1. **Resolution.** The spectral resolution of a window of 1–5 s (0.2–1 Hz) is coarser than the whole tunable range (0.034 Hz) and than the building frequency itself, so the frequency content of the window cannot discriminate settings inside the range. The extra frequency points used in the input FFT interpolate the spectrum and add no information.
2. **The headroom depends on what is hard to predict.** In the previous version of the model, giving the network the magnitude, distance and site class of 1,000 simulated earthquakes (Boore 2003 stochastic method) recovered none of the Oracle headroom in five-fold validation; the headroom there arose from phase and stress-drop variability that the early-warning parameters do not contain. We have not repeated this experiment with the present model.
3. **Little headroom per record.** Apart from a few records (Pohang 2017), the loss of a good constant relative to the Oracle is 0–2.5 points, of the same size as the variability between seeds, so a network trained on 2,000 synthetic samples and evaluated on eleven records cannot show a significant gain.

These findings are specific to the architecture, the data and the evaluation of this study (a small network on synthetic and rotated real records, no hyper-parameter search, no regret-based or recurrent model, eleven test records from seven earthquakes). They show that a gain from prediction is not demonstrated here, not that it cannot exist.

## 5.7 Reading the task as tracking the frequency of the incoming motion

An alternative formulation, suggested by the aim of tuning the damper to the incoming vibration, is to predict the dominant frequency of the ground motion and to set the damper frequency to it. In the present model this reading is not supported by the data. The damper can only move within ±5% of the building frequency (0.3204–0.3542 Hz), whereas the dominant frequencies of the eleven records lie between about 0.2 and 4.1 Hz (Table 2 lists the per-component values), so a predicted input frequency would almost always be clipped to one end of the range. Table 10 relates, for each record, the best constant frequency of the Oracle (Section 4.1) to three spectral descriptors of the input.

**Table 10.** Rank correlation (Spearman) between the best constant damper frequency of a record and a spectral descriptor of the input, computed over the eleven records (n = 11) and over the seven earthquakes (n = 7, Imperial Valley records averaged). For n = 7 the 5% critical value of |ρ| is about 0.79; for n = 11 it is about 0.62.

| Descriptor of the input (0.1–5 Hz) | ρ, eleven records | ρ, seven earthquakes |
|---|---|---|
| Frequency of the Fourier-amplitude peak | −0.31 | −0.20 |
| Spectral centroid | −0.66 | −0.63 |
| Energy in 0.25–0.45 Hz relative to 0.1–5 Hz | +0.01 | +0.12 |

The dominant frequency and the energy near the building frequency are unrelated to the best damper frequency. The centroid has a negative sign, i.e. records with more high-frequency content prefer a lower damper frequency, which is the opposite of tracking the input frequency; with seven independent earthquakes it does not reach significance (|ρ| = 0.63 < 0.79). Seven of the eleven records have their best frequency at the upper end of the range (0.3542 Hz), which reflects the coupling of f and θ in Eq. (5) (Section 4.3) rather than the input spectrum. We therefore keep the formulation of Section 5.1, in which the network chooses the damper frequency and angle that would have performed best; the orifice (valve) law is not predicted and remains the original one (Section 2.3).

## 5.8 Limitations

- Eleven records from seven earthquakes; the five Imperial Valley records are not independent, and the Korean records are only two.
- The labels depend on the literal rotation law of Eq. (5), which does not conserve the damper mass (Section 3.2); the RS-TLCD reproduction is 2.7 points below the original (Section 3.3).
- The preset application is an idealisation. A realistic early-warning application must also account for transmission, computation and actuation times.
- The building stiffness multiplier is assumed known. Noise on the input, as in the robustness test of the original study, was not examined.
- The network was trained and evaluated for the tunable range of the original design (±5%) only; the ±20% range was examined for the constant setting alone (Section 4.2).

*TODO: Fig. — AI vs constant vs Oracle for the nine conditions (event-level differences with error bars); Fig. — per-record reductions at T_obs = 3 s; add the recovery-of-headroom table with the constant baseline; decide whether to repeat the magnitude/distance experiment with the present model.*

