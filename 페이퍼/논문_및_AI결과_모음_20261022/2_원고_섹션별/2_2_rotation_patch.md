# Patch for Section 2.2 (replace the sentence on mass and stiffness splitting)

Old (Draft v0): "...so the liquid mass and stiffness are split into the two horizontal directions as m_dx = m_d cos θ and m_dy = m_d sin θ, with k_dx = m_dx ω_d² and k_dy = m_dy ω_d²."

New (v1, follows Eqs. 16, 17, 20 of Fu et al. 2025): "...so the equivalent liquid mass in the two horizontal directions is m_dx = m_d cos θ and m_dy = m_d sin θ, and the stiffness is k_dx = m_dx ω_d² cos θ and k_dy = m_dy ω_d² sin θ (Eq. 5, Section 3.2). The damper frequency projected on each axis is therefore ω_d√(cos θ) and ω_d√(sin θ)."

Code: `rstlcd_cos2.simulate` (cos_twice=True by default). Note in 3.2 that the directional masses do not sum to m_d.
