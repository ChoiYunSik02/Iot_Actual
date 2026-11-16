# -*- coding: utf-8 -*-
# (2026-10-22) rstlcd.py와 같되 방향별 질량을 m_d cos²θ, m_d sin²θ로 (질량 보존) — 회전 법칙 민감도 시험용 (paper_tests.py)
"""Fu et al. (2025) JOBE 103:112205 재현 모델 — 30층 양방향 편심 건물 + (RS-)TLCD.

식 번호는 원문 기준. 원문이 정하지 않은 부분은 `페이퍼/01_타깃논문_정리.md` 4절의 처리를 따름.
자유도 순서 (식 23): [x_1..x_n, x_d, y_1..y_n, y_d, th_1..th_n]  (n = 30 → 92개)
변위는 지반 기준 상대변위, 적분은 Newmark 평균가속도.
"""
import numpy as np

G, RHO = 9.81, 1000.0

# ── 건물 (원문 3.2절) ─────────────────────────────────────────
N = 30
M_ST, J_ST = 9.216e5, 2.797e8
K_XY = (1.021e9, 1.6213e9)        # 1층, 나머지 층 [N/m]
K_TH = (3.1651e11, 5.0261e11)     # 1층, 나머지 층 [N·m/rad]
EX, EY = 6.0, 2.0
ZETA = 0.02
F_TABLE1 = [0.3373, 1.0112, 1.6831, 2.3517, 3.0155, 3.6729, 4.3221, 4.9615, 5.5892, 6.2034]

# ── 장치 (원문 3.2절 · 표 3) ─────────────────────────────────
M_P = 463178.0                    # 수동 · S-TLCD 한 방향 질량 (1차 모드 질량의 2%)
M_RS = 694767.0                   # RS-TLCD 참여 질량 (1.5 × M_P)
F0 = 0.3373
F_RANGE = (0.3204, 0.3542)        # ±5%
KAPPA0, KAPPA_MIN, KAPPA_MAX = 0.4, 0.1, 0.8
LAM_P, LAM_RS = 0.231, 0.237
DT_F, DT_C, DT_TH = 2.6, 1.0, 2.6 # 진동수 · 감쇠 · 각도 갱신 간격 [s]
ROT_SPEED = np.deg2rad(30.0)      # 회전 속도 [rad/s]

IX = np.arange(N); IDX = N
IY = np.arange(N + 1, 2 * N + 1); IDY = 2 * N + 1
ITH = np.arange(2 * N + 2, 3 * N + 2)
NDOF = 3 * N + 2


def shear_K(k):
    n = len(k); K = np.zeros((n, n))
    for i in range(n):
        K[i, i] += k[i]
        if i + 1 < n:
            K[i, i] += k[i + 1]; K[i, i + 1] = K[i + 1, i] = -k[i + 1]
    return K


def story(k1, k):
    return np.r_[k1, np.full(N - 1, k)]


def structure(k_scale=1.0):
    """구조물만 (3n 자유도): 질량 · 강성. 식 (15)~(22)에서 TLCD 행 · 열을 뺀 것.
    k_scale: 강성 배율 (손상 · 하중 변화로 고유진동수가 √k_scale배로 바뀐 건물)."""
    Kx = shear_K(story(*K_XY)); Ky = Kx.copy(); Kt = shear_K(story(*K_TH))
    Z = np.zeros((N, N))
    K = np.block([[Kx, Z, Kx * EY], [Z, Ky, Ky * EX], [Kx * EY, Ky * EX, Kt]])   # 식 (19)·(21)·(22), 처리 #1
    M = np.r_[np.full(2 * N, M_ST), np.full(N, J_ST)]
    return M, K * k_scale


def modal(M, K):
    """일반 고유치 문제 (M 대각). 반환: 진동수[Hz], 질량 정규화 모드."""
    s = 1 / np.sqrt(M)
    w2, phi = np.linalg.eigh(K * s[:, None] * s[None, :])
    return np.sqrt(np.abs(w2)) / 2 / np.pi, phi * s[:, None]


def rayleigh(M, K, f1=F_TABLE1[0], f2=F_TABLE1[1], z=ZETA):
    """처리 #6: 표 1의 1 · 2차 진동수에서 감쇠비 2%."""
    w1, w2 = 2 * np.pi * f1, 2 * np.pi * f2
    a, b = np.linalg.solve([[1 / (2 * w1), w1 / 2], [1 / (2 * w2), w2 / 2]], [z, z])
    return a * np.diag(M) + b * K


def embed(A3):
    """3n×3n 구조물 행렬을 3n+2 전체 자유도에 넣기."""
    idx = np.r_[IX, IY, ITH]; A = np.zeros((NDOF, NDOF)); A[np.ix_(idx, idx)] = A3
    return A


def delta(kappa, lam):
    """식 (5)~(7): 전체 손실계수 δ = δ1 + λ²δ2."""
    d1 = (1 - lam) ** 2 + 0.5 * abs(1 - lam)
    d2 = ((1 - kappa) + 0.707 * (1 - kappa) ** 0.375) ** 2 / kappa ** 2
    return d1 + lam ** 2 * d2


# ── 웨이블릿 순간 진동수 (원문 2.3절, 처리: 툴박스 없이 과거 데이터만 쓰는 반쪽 Morlet) ──
class WaveletID:
    def __init__(self, dt, fmin=0.1, fmax=2.0, nf=80, w0=6.0):
        self.f = np.geomspace(fmin, fmax, nf)
        sig = w0 / (2 * np.pi * self.f)
        self.n = int(np.ceil(3 * sig.max() / dt))
        tau = np.arange(self.n) * dt                       # 0 = 현재, 과거 방향
        g = np.exp(-tau[None, :] ** 2 / (2 * sig[:, None] ** 2))
        g[tau[None, :] > 3 * sig[:, None]] = 0.0
        self.W = g * np.exp(1j * 2 * np.pi * self.f[:, None] * tau[None, :]) / g.sum(1, keepdims=True)

    def __call__(self, hist):
        """hist: 지금까지의 신호 (마지막이 현재). 가장 큰 진폭 성분의 진동수 [Hz]."""
        seg = np.zeros(self.n); m = min(self.n, len(hist))
        if m: seg[:m] = hist[::-1][:m]
        return self.f[np.argmax(np.abs(self.W @ seg))]


# ── 장치 상태 ────────────────────────────────────────────────
class Device:
    """한 방향 등가 질량-스프링-감쇠 (TMD 형태). DOF는 IDX 또는 IDY, 설치층 = 최상층."""
    def __init__(self, m, f, kappa, lam, L0=None):
        self.m, self.f, self.kappa, self.lam = m, f, kappa, lam
        self.L0 = L0 or 2 * G / (2 * np.pi * F0) ** 2      # 기준 유효 길이 (식 9)
        self.Av = m / (RHO * self.L0)                       # 처리 #5: m = ρ·Av·L
        self.Ah = self.Av / lam

    def k(self):
        return self.m * (2 * np.pi * self.f) ** 2           # = 2·m·g/L (식 9 · 20)

    def c(self, vrel, zeta_override=None, c_scale=1.0):
        """zeta_override: 고정 감쇠비 (κ 무시 → 가변 감쇠 꺼짐).
        c_scale: 식 (24)에 곱하는 보정 배율. κ에 따른 δ 변화(0.7~10배)는 그대로 살아 있음."""
        if zeta_override is not None:
            return 2 * zeta_override * self.m * 2 * np.pi * self.f
        return c_scale * 0.5 * RHO * self.Av ** 2 / self.Ah * delta(self.kappa, self.lam) * abs(vrel)   # 식 (24)


def simulate(agx, agy, dt, case='none', zeta_override=None, cos_twice=False, rs_freq=None, rs_kappa=None, rs_theta=None,
             f0=F0, theta0=0.0, k_scale=1.0, c_scale=1.0, f_range=F_RANGE, cmd=None):
    """case: 'none' | 'passive' | 'stlcd' | 'rstlcd'
    rs_freq / rs_kappa / rs_theta: 외부 제어기(예: AI)가 정하는 함수 f(t, state) → 값. None이면 원문 알고리즘.
    f0 / theta0: 장치 초기 진동수 · 회전각 (실험 0 Oracle: 지진 전에 미리 맞춰 둔 값)
    c_scale: 식 (24) 감쇠 보정 배율 (zeta_override가 없을 때)
    f_range: 장치 진동수 조절 범위 (원문 ±5%, 민감도: 범위 확대)
    cmd: (t_cmd, f, θ) — 주기 갱신 없이 t_cmd에 한 번만 진동수 · 각도 명령 (조기경보 실험). 감쇠 법칙은 그대로
    k_scale: 건물 강성 배율 (실험 1: 건물 진동수 변화). 레일리 감쇠도 바뀐 진동수 기준으로 2%
    반환: dict(t, ux, uy, th, f_dev, kappa, theta)  (최상층 응답, 장치 이력)
    """
    nt = len(agx)
    Ms3, Ks3 = structure(k_scale)
    M0 = np.r_[Ms3[:N], 0.0, Ms3[N:2 * N], 0.0, Ms3[2 * N:]]
    K0 = embed(Ks3); C0 = embed(rayleigh(Ms3, Ks3, F_TABLE1[0] * np.sqrt(k_scale), F_TABLE1[1] * np.sqrt(k_scale)))
    E = np.zeros((NDOF, 2)); E[np.r_[IX, IDX], 0] = 1; E[np.r_[IY, IDY], 1] = 1    # 처리 #3
    top_x, top_y = IX[-1], IY[-1]

    rs = case == 'rstlcd'
    if case == 'none':
        devs = []
    elif rs:
        dev = Device(M_RS, f0, KAPPA0, LAM_RS); theta = theta_tgt = theta0
    else:
        dx_, dy_ = Device(M_P, f0, KAPPA0, LAM_P), Device(M_P, f0, KAPPA0, LAM_P)
    wid = WaveletID(dt) if case in ('stlcd', 'rstlcd') else None

    u = np.zeros(NDOF); v = np.zeros(NDOF); a = np.zeros(NDOF)
    # 장치는 최상층·장치 4자유도에만 붙음 → 기준 행렬 A0의 역행렬을 한 번 구하고 매 단계 4×4 보정(Woodbury)
    Mb = M0.copy(); Mb[IDX] = Mb[IDY] = 1.0; Kb = K0.copy(); Kb[IDX, IDX] = Kb[IDY, IDY] = 1.0
    A0inv = np.linalg.inv(np.diag(Mb) + 0.5 * dt * C0 + 0.25 * dt * dt * Kb)
    SD = np.array([top_x, IDX, top_y, IDY]); Z = A0inv[:, SD]; G = Z[SD]; I4 = np.eye(4)
    out = {k: np.zeros(nt) for k in ('ux', 'uy', 'th', 'f_dev', 'kappa', 'theta')}
    ramp = {}                                              # 진동수 변경 중: 키 → (t0, f0, f1)
    nF, nC, nTH = (int(round(x / dt)) for x in (DT_F, DT_C, DT_TH))

    def dir_params():
        """방향별 (질량, 강성, 장치객체) — RS는 θ로 분해 (식 16·17·20)."""
        if rs:
            c_, s_ = abs(np.cos(theta)), abs(np.sin(theta))
            eps = 1e-6
            mx, my = M_RS * max(c_**2, eps), M_RS * max(s_**2, eps)
            w2 = (2 * np.pi * dev.f) ** 2
            kx = mx * w2 * (c_ if cos_twice else 1.0); ky = my * w2 * (s_ if cos_twice else 1.0)
            return (mx, kx, dev), (my, ky, dev)
        return (dx_.m, dx_.k(), dx_), (dy_.m, dy_.k(), dy_)

    def start_ramp(key, obj, f_new, t):
        ramp[key] = (t, obj.f, f_new)

    for i in range(nt - 1):
        t = i * dt
        # ── 제어기 갱신 (원문 2.3절) ──
        if cmd is not None and t >= cmd[0] and 'done' not in ramp:
            start_ramp('rs', dev, float(np.clip(cmd[1], *f_range)), t); theta_tgt = cmd[2]; ramp['done'] = None
        if case in ('stlcd', 'rstlcd') and i > 0:
            if i % nF == 0 and cmd is None:
                if rs:
                    if rs_freq is not None:
                        ft = rs_freq(t, locals())
                    else:
                        fx = np.clip(wid(out['ux'][:i]), *f_range); fy = np.clip(wid(out['uy'][:i]), *f_range)   # 식 (10)
                        Dx, Dy = abs(out['ux'][i - 1]), abs(out['uy'][i - 1])
                        ft = (Dy * fy + Dx * fx) / (Dx + Dy) if Dx + Dy > 0 else F0                           # 식 (11)
                    start_ramp('rs', dev, float(np.clip(ft, *f_range)), t)
                else:
                    start_ramp('x', dx_, float(np.clip(wid(out['ux'][:i]), *f_range)), t)
                    start_ramp('y', dy_, float(np.clip(wid(out['uy'][:i]), *f_range)), t)
            if rs and i % nTH == 0 and cmd is None:
                if rs_theta is not None:
                    theta_tgt = rs_theta(t, locals())
                else:
                    j0 = max(0, i - int(round(DT_TH / dt)))                                                  # 처리 #9: t_R = 2.6 s
                    theta_tgt = np.arctan2(np.abs(out['uy'][j0:i]).max(), np.abs(out['ux'][j0:i]).max())    # 식 (13)
            if i % nC == 0:
                acc_x = a[top_x] + agx[i]; acc_y = a[top_y] + agy[i]
                sx = (v[IDX] - v[top_x]) * acc_x > 0; sy = (v[IDY] - v[top_y]) * acc_y > 0
                if rs:
                    if rs_kappa is not None:
                        dev.kappa = rs_kappa(t, locals())
                    else:
                        dev.kappa = KAPPA_MAX if not (sx or sy) else KAPPA_MIN if (sx and sy) else KAPPA0    # 식 (12), 처리 #9
                else:
                    dx_.kappa = KAPPA_MIN if sx else KAPPA_MAX
                    dy_.kappa = KAPPA_MIN if sy else KAPPA_MAX
        # 진동수: 펌프 지연 → 갱신 간격 동안 선형으로 이동
        for key, (t0, f0_, f1_) in [(k_, v_) for k_, v_ in ramp.items() if k_ != 'done']:
            obj = dev if key == 'rs' else (dx_ if key == 'x' else dy_)
            r = min(1.0, (t - t0) / DT_F); obj.f = f0_ + (f1_ - f0_) * r
            if r >= 1.0: del ramp[key]
        # 각도: 30°/s로 목표까지 회전
        if rs:
            dth = np.clip(theta_tgt - theta, -ROT_SPEED * dt, ROT_SPEED * dt); theta += dth

        # ── 행렬 조립 (기준 + 4×4 보정) ──
        Mv = Mb.copy(); dM = np.zeros((4, 4)); dK = np.zeros((4, 4)); dC = np.zeros((4, 4))
        if case != 'none':
            for j, ((m_, k_, obj), idof, itop) in enumerate(zip(dir_params(), (IDX, IDY), (top_x, top_y))):
                c_ = obj.c(v[idof] - v[itop], zeta_override, c_scale)                                               # 처리 #4: 상대속도
                if rs and zeta_override is not None:
                    c_ *= m_ / M_RS
                Mv[idof] = m_; o = 2 * j
                dM[o + 1, o + 1] = m_ - 1.0
                dK[o:o + 2, o:o + 2] = [[k_, -k_], [-k_, k_ - 1.0]]                                                # 기준 Kb의 장치 대각 1 제거
                dC[o:o + 2, o:o + 2] = [[c_, -c_], [-c_, c_]]
        f = -Mv * (E @ np.array([agx[i + 1], agy[i + 1]]))
        wc = v + 0.5 * dt * a; wk = u + dt * v + 0.25 * dt * dt * a
        rhs = f - C0 @ wc - Kb @ wk
        rhs[SD] -= dC @ wc[SD] + dK @ wk[SD]
        a1 = A0inv @ rhs
        if case != 'none':
            D = dM + 0.5 * dt * dC + 0.25 * dt * dt * dK
            a1 -= Z @ np.linalg.solve(I4 + D @ G, D @ a1[SD])
        u = u + dt * v + 0.25 * dt * dt * (a + a1); v = v + 0.5 * dt * (a + a1); a = a1

        out['ux'][i + 1], out['uy'][i + 1], out['th'][i + 1] = u[top_x], u[top_y], u[ITH[-1]]
        if case != 'none':
            out['f_dev'][i + 1] = dev.f if rs else dx_.f
            out['kappa'][i + 1] = dev.kappa if rs else dx_.kappa
            out['theta'][i + 1] = theta if rs else 0.0
    out['t'] = np.arange(nt) * dt
    return out


def metrics(o):
    """원문 4장 지표 6개: 최상층 X · Y 변위, 비틀림각의 최대 · RMS."""
    r = {}
    for k in ('ux', 'uy', 'th'):
        r[k + '_max'] = float(np.abs(o[k]).max()); r[k + '_rms'] = float(np.sqrt(np.mean(o[k] ** 2)))
    return r


def reduction(m_ctrl, m_none):
    return {k: 100 * (1 - m_ctrl[k] / m_none[k]) for k in m_none}
