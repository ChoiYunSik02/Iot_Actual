# 3. Ground motions and model validation

> Draft v1 (2026-10-22), replaces `3_validation.md` (v0). Changes: the rotation law of Section 2.2 now follows Eq. (20) of the original study literally (stiffness ∝ cos θ · m_dx); Table 3 and the limitation paragraph are recomputed. Numbers: `페이퍼/코드/README_v2_20261022.md`. Code: `rstlcd_cos2.py`.

## 3.1 Ground motions

The original study used fifteen bi-directional PEER records: twelve stations of the 1979 Imperial Valley earthquake, Pacoima Dam (1994 Northridge), KJMA (1995 Kobe) and CHY006 (1999 Chi-Chi). Eight of these pairs could be obtained in their original PEER format (Nos. 1, 2, 3, 4, 11, 13, 14 and 15 of the original Table 2); for the remaining seven only one component or aftershock records were available, and they were excluded rather than substituted. Three additional pairs are used to widen the frequency content: El Centro 1940 (N–S/E–W components, from a public compilation; whether it is identical to the corrected PEER version was not checked) and two moderate Korean events recorded at long epicentral distance by broadband velocity sensors of the KMA network (Pohang 2017, ML 5.4, station KS.BUS2, 98 km; Gyeongju 2016, ML 5.8, station KS.CHJ2, 164 km). The Korean records have peak accelerations of only 1–3 cm/s², were converted from velocity by the instrument sensitivity, differentiated and band-passed at 0.1–8 Hz, and are used for 60 s starting 5 s before the P arrival. They are far-field records and serve only as waveforms with different spectral content once scaled. All eleven pairs are used in the evaluation of Sections 4 and 5; the eight PEER pairs alone are used for the comparison with the original results below.

The eleven pairs belong to only seven independent earthquakes: five of them (Nos. 1, 2, 3, 4 and 11) are stations of the same Imperial Valley event. This matters for the statistics: in Sections 4 and 5 records of the same earthquake are always treated as one group, both when training and when averaging differences between methods.

Following the original study, each horizontal component is scaled to a peak ground acceleration of 35 cm/s² (frequent earthquake level of the Chinese code). The original paper does not state whether scaling was applied per component or per pair; per-component scaling is adopted here.

**Table 2.** Ground-motion pairs. PGA before scaling is the peak of each recorded component; dominant frequency is the Fourier-amplitude peak in 0.1–5 Hz after scaling; Arias interval is the 5–95% window of the summed X+Y energy.

| Record | Earthquake | PGA X/Y before scaling (cm/s²) | Dominant f X/Y (Hz) | Arias 5–95% (s) |
|---|---|---|---|---|
| PEER 1 El Centro Array #11 | Imperial Valley 1979 | 360 / 372 | 4.12 / 3.78 | 6–15 |
| PEER 2 Aeropuerto Mexicali | Imperial Valley 1979 | 301 / 266 | 0.65 / 3.27 | 2–11 |
| PEER 3 El Centro Differential Array | Imperial Valley 1979 | 345 / 471 | 0.43 / 0.78 | 5–12 |
| PEER 4 Brawley Airport | Imperial Valley 1979 | 160 / 215 | 0.40 / 0.65 | 6–21 |
| PEER 11 El Centro Array #3 | Imperial Valley 1979 | 261 / 217 | 0.40 / 0.36 | 6–19 |
| PEER 13 Pacoima Dam | Northridge 1994 | 408 / 426 | 1.97 / 2.10 | 3–7 |
| PEER 14 KJMA | Kobe 1995 | 818 / 618 | 1.45 / 1.43 | 8–17 |
| PEER 15 CHY006 | Chi-Chi 1999 | 339 / 357 | 0.81 / 0.59 | 32–57 |
| El Centro 1940 | El Centro 1940 | 342 / 210 | 1.46 / 2.37 | 2–26 |
| Pohang 2017 BUS2 | Pohang 2017 | 2 / 1 | 2.83 / 2.79 | 8–37 |
| Gyeongju 2016 CHJ2 | Gyeongju 2016 | 3 / 3 | 1.11 / 1.33 | 24–37 |

*TODO: Fig. G1 caption (Fourier spectra with building frequencies 0.337 and 1.01 Hz marked).*

## 3.2 Rotation law of the RS-TLCD

Equations (16), (17) and (20) of the original study give the equivalent damper mass in the two directions as m_dx = m_d cos θ and m_dy = m_d sin θ, and the damper stiffness in the X direction as

$$
k_{dx}(t) = \frac{2\,m_{dx}\,g}{H_{vL}+H_{vR}+\lambda B}\cos\theta(t) = m_{dx}\,\omega_d^2\cos\theta(t) \tag{5 [20]}
$$

so that the stiffness carries cos θ twice (once through m_dx), and the frequency of the damper projected on the X axis is ω_d√(cos θ), not ω_d. The first version of the present model (Draft v0) used k_dx = m_dx ω_d², i.e. cos θ only once. Table 3 shows that the reading matters for the semi-active result, and the literal Eq. (5) is adopted from this draft on. Passive and S-TLCD cases do not rotate and are unaffected.

**Table 3.** Sensitivity of the RS-TLCD reproduction to the rotation law: mean reduction (%) of the six indices over eight PEER pairs, damping calibration of Section 2.4.

| Rotation law | Passive TLCD | S-TLCD | RS-TLCD | RS − passive |
|---|---|---|---|---|
| k = m_dx ω_d² (v0) | 15.56 | 15.43 | 15.31 | −0.25 |
| **Eq. (5), literal (adopted)** | 15.56 | 15.43 | **16.12** | **+0.56** |
| mass-conserving, m_dx = m_d cos²θ | 15.56 | 15.43 | 12.89 | −2.68 |
| *Original study (15 pairs)* | *16.00* | *16.09* | *18.80* | *+2.80* |

Only the literal reading moves the semi-active result towards the original, in the direction of the reported advantage of rotation. Note that with m_dx = m_d cos θ and m_dy = m_d sin θ the two directional masses add up to m_d(cos θ + sin θ), up to √2 m_d at 45°, so the equations as printed do not conserve the liquid mass. The mass-conserving projection reproduces the original RS-TLCD result considerably worse (12.89%), which suggests that the printed formulation, not a mass-conserving one, underlies the reported performance. We retain the printed formulation so that comparisons with the original controller are made on identical equations, and we state this property as a limitation: absolute reductions at θ ≠ 0 should be read as those of the printed model.

## 3.3 Validation

**Natural frequencies.** The ten X-direction natural frequencies of the uncontrolled model coincide with the original Table 1 to four decimal places, and the first-mode mass participation is 83.76%, as reported.

**Passive TLCD and damping calibration.** Table 4 compares the mean reductions of the six performance indices (peak and RMS of the roof X and Y displacements and of the roof rotation) over the eight available PEER pairs with the original fifteen-pair means. With the calibrated damping of Section 2.4 the passive TLCD reproduces the original mean reduction closely (15.56% vs 16.00%), including the dominant X-RMS index (33.19% vs 33.54%).

**Table 4.** Mean reduction (%) of the six indices. Present model: eight PEER pairs; original: fifteen pairs.

| Case | Source | X peak | Y peak | θ peak | X RMS | Y RMS | θ RMS | Mean |
|---|---|---|---|---|---|---|---|---|
| Passive TLCD ×2 | Original | 15.39 | 11.45 | 9.85 | 33.54 | 14.33 | 11.43 | 16.00 |
|  | Present | 12.09 | 13.35 | 8.92 | 33.19 | 14.95 | 10.86 | 15.56 |
| S-TLCD ×2 | Original | 13.29 | 10.40 | 9.52 | 33.46 | 16.81 | 13.06 | 16.09 |
|  | Present | 9.72 | 12.03 | 6.61 | 35.46 | 17.43 | 11.35 | 15.43 |
| RS-TLCD | Original | 15.48 | 13.74 | 11.50 | 38.03 | 18.00 | 16.03 | 18.80 |
|  | Present (Eq. 5) | 10.43 | 12.93 | 6.69 | 37.10 | 18.88 | 10.68 | 16.12 |

**Limitation.** The semi-active cases are reproduced less well. In the original study the RS-TLCD improves on the passive TLCD by 2.8 points on average; in the present model the improvement is 0.56 points (16.12% vs 15.56%), and the RS-TLCD mean is 2.7 points below the original, mainly through the peak and torsional indices (θ peak 6.69% vs 11.50%, θ RMS 10.68% vs 16.03%). Plausible causes are the unreported cross-sections (which set the absolute damping level), details of the wavelet identification, the rotation law discussed above, and the seven missing records. Because every controller in this study — including the original wavelet law used as the baseline — is evaluated in the same model and with the same records, the discrepancy is expected to affect absolute values more than the ranking of methods, but this cannot be guaranteed: a model error can affect different controllers differently. The conclusions of Sections 4 and 5 are therefore stated for the present model.

*TODO: check the original S-TLCD and RS-TLCD "Mean" values (computed here from the original Table 7 rows); per-record comparison with the original Tables 4–6; sensitivity of Sections 4–5 to the damping multiplier (×20, ×30, ×40).*
