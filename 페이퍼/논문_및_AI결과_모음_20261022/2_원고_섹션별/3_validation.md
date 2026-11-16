# 3. Ground motions and model validation

> Draft v0 (2026-10-21). Numbers: `페이퍼/코드/results/exp1_c30_k1.0.log`, records `페이퍼/입력/README.md`.

## 3.1 Ground motions

The original study used fifteen bi-directional PEER records: twelve stations of the 1979 Imperial Valley earthquake, Pacoima Dam (1994 Northridge), KJMA (1995 Kobe) and CHY006 (1999 Chi-Chi). Eight of these pairs could be obtained in their original PEER format (Nos. 1, 2, 3, 4, 11, 13, 14 and 15 of the original Table 2); for the remaining seven only one component or aftershock records were available, and they were excluded rather than substituted. Three additional pairs are used to widen the frequency content: El Centro 1940 and two moderate Korean events recorded at short epicentral distance (Pohang 2017, station BUS2; Gyeongju 2016, station CHJ2). All eleven pairs are used in the evaluation of Sections 4–6; the eight PEER pairs alone are used for the comparison with the original results below.

Following the original study, each horizontal component is scaled to a peak ground acceleration of 35 cm/s² (frequent earthquake level of the Chinese code). The original paper does not state whether scaling was applied per component or per pair; per-component scaling is adopted here.

*TODO: Table 2 — records, station, distance, PGA before scaling, dominant frequency; Fig. G1 — Fourier spectra of all records with the building frequencies 0.337 and 1.01 Hz marked.*

## 3.2 Validation

**Natural frequencies.** The ten X-direction natural frequencies of the uncontrolled model coincide with the original Table 1 to four decimal places, and the first-mode mass participation is 83.76%, as reported.

**Passive TLCD and damping calibration.** Table 3 compares the mean reductions of the six performance indices (peak and RMS of the roof X and Y displacements and of the roof rotation) over the eight available PEER pairs with the original fifteen-pair means. With the calibrated damping of Section 2.4 the passive TLCD reproduces the original mean reduction closely (15.56% vs 16.00%), including the dominant X-RMS index (33.19% vs 33.54%).

**Table 3.** Mean reduction (%) of the six indices. Present model: eight PEER pairs; original: fifteen pairs.

| Case | Source | X peak | Y peak | θ peak | X RMS | Y RMS | θ RMS | Mean |
|---|---|---|---|---|---|---|---|---|
| Passive TLCD ×2 | Original | 15.39 | 11.45 | 9.85 | 33.54 | 14.33 | 11.43 | 16.00 |
|  | Present | 12.09 | 13.35 | 8.92 | 33.19 | 14.95 | 10.86 | 15.56 |
| S-TLCD ×2 | Original | 13.29 | 10.40 | 9.52 | 33.46 | 16.81 | 13.06 | 16.09 |
|  | Present | 9.72 | 12.03 | 6.61 | 35.46 | 17.43 | 11.35 | 15.43 |
| RS-TLCD | Original | 15.48 | 13.74 | 11.50 | 38.03 | 18.00 | 16.03 | 18.80 |
|  | Present | 10.67 | 11.41 | 9.15 | 36.90 | 14.29 | 9.46 | 15.31 |

**Limitation.** The semi-active S-TLCD and RS-TLCD are reproduced less well. In the original study the RS-TLCD improves on the passive TLCD by 2.8 points on average, whereas in the present model the two are nearly equal (15.31% vs 15.56%), mainly because of lower peak reductions. Plausible causes are the unreported cross-sections (which set the absolute damping level), details of the wavelet identification, and the seven missing records. Because every controller in this study — including the original wavelet law used as the baseline — is evaluated in the same model and with the same records, this discrepancy affects absolute values but not the comparisons on which the conclusions rest.

*TODO: check the original S-TLCD and RS-TLCD "Mean" values (computed here from the original Table 7 rows); decide whether a per-record comparison with the original Tables 4–6 is needed.*
