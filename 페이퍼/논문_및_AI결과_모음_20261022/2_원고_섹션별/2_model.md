# 2. Target building and RS-TLCD model

> Draft v1 (2026-10-22; rotation law follows Eq. 20 literally, see 2_2_rotation_patch and Section 3.2). Equation numbers follow this manuscript; the source equation of Fu et al. (2025) is given in brackets. Values: `페이퍼/01_타깃논문_정리.md`. Code: `페이퍼/코드/rstlcd_cos2.py`.

## 2.1 Bi-directionally eccentric 30-storey building

The benchmark structure is the 30-storey bi-directionally eccentric frame of Fu et al. (2025), used here without modification so that the proposed controller can be compared with the original one on identical ground. Each floor is a rigid diaphragm with two horizontal translations and one rotation. The floor mass and mass moment of inertia are m = 9.216 × 10⁵ kg and J = 2.797 × 10⁸ kg·m² at every level. The lateral stiffness is 1.021 × 10⁹ N/m for the first storey and 1.6213 × 10⁹ N/m for the others in both directions, and the torsional stiffness is 3.1651 × 10¹¹ and 5.0261 × 10¹¹ N·m/rad, respectively. The centre of mass is offset from the centre of stiffness by e_x = 6 m and e_y = 2 m. Inherent damping is Rayleigh damping with a 2% ratio in the first two modes. The parameters of the building and the damper are listed in Table 1.

With the damper degrees of freedom appended, the equation of motion is

$$
\mathbf{M}\ddot{\mathbf{U}} + \mathbf{C}(t)\dot{\mathbf{U}} + \mathbf{K}(t)\mathbf{U} = -\mathbf{M}\mathbf{E}\ddot{\mathbf{U}}_g \tag{1 [14]}
$$

where **U** = [u_x1 … u_x30, u_dx, u_y1 … u_y30, u_dy, u_θ1 … u_θ30]ᵀ has 92 entries, **Ü**_g = [ü_xg, ü_yg]ᵀ is the bi-directional ground acceleration, and **E** assigns ü_xg to all X degrees of freedom (floors and damper) and ü_yg to all Y degrees of freedom. The translation–torsion coupling is **K**_xθ = e_y **K**_x and **K**_yθ = e_x **K**_y, built from the storey stiffness only (the damper rows are not coupled to rotation).

The uncontrolled model reproduces the ten X-direction natural frequencies of the original study (0.3373, 1.0112, 1.6831 … Hz) to four decimal places. Because of eccentricity, the fundamental X mode couples with the first Y and torsional modes into three modes at 0.2714, 0.3373 and 0.3953 Hz.

## 2.2 Rotating semi-active TLCD

The RS-TLCD is a U-shaped liquid column mounted on a turntable on the roof. Its natural frequency depends only on the effective liquid length L:

$$
\omega_d = \sqrt{2g / L}, \qquad L = 2H_v + \lambda B \tag{2 [9]}
$$

so that pumping water between reservoirs changes the vertical water height H_v and therefore ω_d. Following the original design, the tunable range is ±5% of the fundamental frequency, [0.3204, 0.3542] Hz (L = 4.83–3.96 m), and a frequency change takes Δt_f = 2.6 s. The participating liquid mass is m_d = 694,767 kg (1.5 times the passive TLCD mass, 3% of the first modal mass) and the area ratio is λ = 0.237.

The head loss of the horizontal section with an orifice of opening ratio κ is

$$
\delta(\kappa) = (1-\lambda)^2 + 0.5|1-\lambda| + \lambda^2\left[(1-\kappa) + 0.707(1-\kappa)^{0.375}\right]^2 \kappa^{-2} \tag{3 [5–7]}
$$

and enters the equivalent linearised damper as

$$
c_d(t) = \tfrac{1}{2}\,\rho\,\frac{A_v^2}{A_h}\,\delta(\kappa)\,|\dot u_d - \dot u_{n}| \tag{4 [24]}
$$

The turntable rotates the column axis by θ(t), so the equivalent liquid mass in the two horizontal directions is m_dx = m_d cos θ and m_dy = m_d sin θ, and the stiffness is k_dx = m_dx ω_d² cos θ and k_dy = m_dy ω_d² sin θ (Eq. 5, Section 3.2). The damper frequency projected on each axis is therefore ω_d√(cos θ) and ω_d√(sin θ), and the directional masses sum to m_d(cos θ + sin θ), up to √2 m_d. The rotation speed is 30°/s.

**Table 1.** Parameters of the building and the RS-TLCD (Fu et al. 2025; damping calibration of Section 2.4).

| Item | Value |
|---|---|
| Storeys / degrees of freedom | 30 / 92 (with the damper) |
| Floor mass m, mass moment of inertia J | 9.216 × 10⁵ kg, 2.797 × 10⁸ kg·m² |
| Lateral stiffness (1st storey / others) | 1.021 × 10⁹ / 1.6213 × 10⁹ N/m |
| Torsional stiffness (1st storey / others) | 3.1651 × 10¹¹ / 5.0261 × 10¹¹ N·m/rad |
| Eccentricity e_x, e_y | 6 m, 2 m |
| Inherent damping | Rayleigh, 2% in the first two modes |
| Fundamental frequency (X) | 0.3373 Hz |
| Liquid mass m_d, area ratio λ | 694,767 kg, 0.237 |
| Tunable frequency range | 0.3204–0.3542 Hz (±5%), L = 4.83–3.96 m |
| Frequency change time Δt_f | 2.6 s |
| Rotation speed | 30°/s |
| Orifice opening κ (c_min / c_opt / c_max) | 0.8 / 0.4 / 0.1, updated every 1 s |
| Damping calibration factor | 30 (Section 2.4) |

## 2.3 Original control law (wavelet identification)

In the original RS-TLCD the three actuators are driven by feedback from the roof response:

1. **Frequency (every 2.6 s).** The instantaneous frequency of the roof displacement in each direction is identified by a Morlet wavelet transform, clipped to the tunable range, and combined by displacement weighting, ω_d = (|D_y|ω_dy + |D_x|ω_dx)/(|D_x| + |D_y|) [Eqs. 10–11]. The pump then moves the water level over the next 2.6 s.
2. **Damping (every 1 s).** The orifice switches between κ = 0.8, 0.4 and 0.1 according to the signs of the relative velocity and the floor acceleration in the two directions [Eq. 12].
3. **Angle (every 2.6 s).** The turntable is driven towards θ = arctan(D_y,max / D_x,max) over the last t_R seconds [Eq. 13].

Because the frequency is identified *after* the building responds and the pump needs another 2.6 s, the device can only react to motion that has already occurred. The present study keeps all three actuators and the damping law (item 2) unchanged and replaces only how the target frequency and angle (items 1 and 3) are chosen.

## 2.4 Numerical solution and modelling assumptions

Equation (1) is integrated with the Newmark average-acceleration method at Δt = 0.01 s; **M**, **C** and **K** are reassembled at every step because m_dx, m_dy, k_dx, k_dy and c_d vary in time. The wavelet transform is implemented directly (a causal half-Morlet kernel using only past samples, 0.1–2 Hz, 80 scales) so that it is realisable on-line; no toolbox routine is used.

The original paper leaves some quantities unspecified. The following choices were made and are applied identically to every controller compared in this study:

- **Cross-sections.** A_v is obtained from m_d = ρA_vL at the nominal length, and A_h = A_v/λ.
- **Damping velocity.** Eq. (4) uses the damper velocity relative to the roof, consistent with the mass–spring–dashpot form of the damper.
- **Damping calibration.** With the sections above, Eq. (4) gives an equivalent damping ratio of only 0.05–0.5%, and the passive TLCD amplifies the response for some records. Eq. (4) is therefore multiplied by a constant factor of 30, chosen so that the mean reduction of the passive TLCD over the six indices matches the original Table 7 (15.56% vs 16.00%; X-RMS 33.19% vs 33.54%). The κ-dependence of δ (a factor of 0.7–10) is retained, so the semi-active damping law remains active (Section 3).
- **Rotation in stiffness.** The original expression is applied literally (cos θ twice in k_dx). Applying it once, or conserving the damper mass (cos² θ, sin² θ), are treated as sensitivity cases in Section 3.2.
- **Angle window.** t_R = 2.6 s, equal to the angle update interval.
- **Damping levels.** c_min, c_opt and c_max correspond to κ = 0.8, 0.4 and 0.1.

---
*TODO: Table 1 (building and damper parameters, from plan v3 §1); device schematic (redrawn, not copied from the original); decide whether the ×30 calibration goes here or in Section 3.*
