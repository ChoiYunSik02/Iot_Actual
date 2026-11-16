"""
6주차: 경보 없는 즉시 충격(no-warning impact) 시나리오용 6층 건물 + 밀폐형 TLCD 시뮬레이터 (1축)
- 건물/장치 모델은 4~5주차와 같은 지배방정식(README §2)을 Python/numba로 재구현
- 제어기: 0 무제어, 1 고정 xi, 2 Delta-DBG(논문②), 3 NN 정책(AI)
- 센서 가정: 상대가속도(옥상-지반) + 수위계, 잡음/지연/밸브 1차 지연 포함
"""
import os
import numpy as np
from numba import njit

G = 9.81
N = 6
F1 = 0.872            # Hz, 1차 고유진동수
MEFF = 1382.1e3       # kg, 1차 모드질량(옥상 정규화)
MU = 0.005            # 질량비(한 축)
ALPHA = 0.6           # B/L
LTUBE = 4.0           # m (밀폐형, 문서의 C모델 L)
YMAX = 0.8            # m, 물기둥 한계
GAMMA0 = float(os.environ.get('W6_GAMMA0', 0.95))         # 공칭 튜닝비
TAU_V = 0.05          # s, 밸브 지연
DT = 0.0025
TC = 0.01             # s, 제어 주기
NSUB = int(round(TC / DT))
TEND = 24.0
NSTEP = int(TEND / DT)

NF = 9                # 정책 입력 수
H1 = 16
NTHETA = NF * H1 + H1 + H1 * H1 + H1 + 2 * (H1 + 1) + 1   # 출력 2개(밸브, 공압힘) + standby
TAU_P = 0.1           # s, 공압 힘 지연(가정)
FP_MAX = 0.15 * MU * MEFF * G   # N, 공압 힘 한계(가정: 물기둥 중량의 15%)


def build_building():
    """균등 질량/강성 6층 전단건물. 1차 고유진동수와 모드질량을 문서값에 맞춘다."""
    k1 = np.ones(N)
    K0 = np.zeros((N, N))
    for i in range(N):
        K0[i, i] += k1[i]
        if i > 0:
            K0[i, i - 1] -= k1[i]; K0[i - 1, i] -= k1[i]
            K0[i - 1, i - 1] += k1[i]
    # 단위 m=1, k=1로 고유치 -> 스케일
    w2, ph = np.linalg.eigh(K0)
    phi = ph[:, 0] / ph[-1, 0]            # 옥상 정규화
    mgen_unit = phi @ phi                 # M=I
    m = MEFF * mgen_unit / (phi.sum() ** 2)   # 1차 유효(참여)모드질량 = 1382.1 t 가 되도록 층질량 결정
    w1 = 2 * np.pi * F1
    k = w1 ** 2 * m / w2[0]
    M = m * np.eye(N)
    K = k * K0
    return M, K, phi, w2, m, k


M0, K0_, PHI, _, MFLOOR, KFLOOR = build_building()
W1 = 2 * np.pi * F1


def rayleigh(M, K, zeta):
    w, _ = np.linalg.eigh(np.linalg.solve(M, K))
    w = np.sqrt(w)
    a = 2 * zeta * w[0] * w[1] / (w[0] + w[1])
    b = 2 * zeta / (w[0] + w[1])
    return a * M + b * K


def make_system(fscale, zeta, has_tlcd=True, gamma=GAMMA0):
    K = K0_ * fscale ** 2
    C = rayleigh(M0, K, zeta)
    mf = MU * MEFF if has_tlcd else 1e-3
    e = np.zeros(N); e[-1] = 1.0
    Mc = np.zeros((N + 1, N + 1))
    Mc[:N, :N] = M0 + mf * np.outer(e, e)
    Mc[:N, N] = ALPHA * mf * e
    Mc[N, :N] = ALPHA * mf * e
    Mc[N, N] = mf
    Minv = np.linalg.inv(Mc)
    kf = mf * (gamma * W1) ** 2
    cnl_unit = 0.5 * (mf / LTUBE)         # 0.5*rho*A ; xi를 곱해서 사용
    Rg = (M0 + mf * np.outer(e, e)) @ np.ones(N)
    return K, C, Minv, mf, kf, cnl_unit, Rg


@njit(cache=True)
def _deriv(x, ag, Fv, u_xi, fp, K, C, Minv, kf, cnl_unit, Rg, mf, out):
    # x: [q(6), qd(6), y, yd]
    n = 6
    rhs = np.zeros(7)
    for i in range(n):
        s = 0.0
        for j in range(n):
            s += C[i, j] * x[n + j] + K[i, j] * x[j]
        rhs[i] = -s - Rg[i] * ag + Fv[i]
    y = x[12]; yd = x[13]
    stop = 0.0
    if y > YMAX:
        stop = 100.0 * kf * (y - YMAX) + 0.0
    elif y < -YMAX:
        stop = 100.0 * kf * (y + YMAX)
    rhs[6] = -u_xi * cnl_unit * abs(yd) * yd - kf * y - stop - ALPHA * mf * ag + fp
    for i in range(n):
        out[i] = x[n + i]
    for i in range(7):
        s = 0.0
        for j in range(7):
            s += Minv[i, j] * rhs[j]
        if i < 6:
            out[n + i] = s
        else:
            out[13] = s
    out[12] = x[13]


@njit(cache=True)
def policy_forward(theta, f):
    """f(NF) -> (u_scale in [0.6, 2.0], fp_norm in [-1, 1])"""
    p = 0
    h1 = np.empty(H1)
    for j in range(H1):
        s = theta[p + NF * H1 + j]
        for i in range(NF):
            s += theta[p + i * H1 + j] * f[i]
        h1[j] = np.tanh(s)
    p += NF * H1 + H1
    h2 = np.empty(H1)
    for j in range(H1):
        s = theta[p + H1 * H1 + j]
        for i in range(H1):
            s += theta[p + i * H1 + j] * h1[i]
        h2[j] = np.tanh(s)
    p += H1 * H1 + H1
    z1 = theta[p + H1]
    z2 = theta[p + 2 * H1 + 1]
    for i in range(H1):
        z1 += theta[p + i] * h2[i]
        z2 += theta[p + H1 + 1 + i] * h2[i]
    return 0.6 + 1.4 / (1.0 + np.exp(-z1)), np.tanh(z2)



@njit(cache=True)
def _energy_parts(x, K, kf, mf):
    eb = 0.0
    for i in range(6):
        eb += 0.5 * MFLOOR * x[6 + i] ** 2
        for j in range(6):
            eb += 0.5 * x[i] * K[i, j] * x[j]
    el = 0.5 * mf * x[13] ** 2 + 0.5 * kf * x[12] ** 2
    return eb, el


@njit(cache=True)
def _look(x0, u_cur, fp_cur, u_try, fp_try, K, C, Minv, kf, cnl_unit, Rg, mf, xi_opt, H, wl):
    """자유진동(미래 지반입력 0 가정) 예측으로 후보 (u, fp) 평가 -> 비용"""
    dtl = 0.005
    x = x0.copy()
    xt = np.zeros(14); k1 = np.zeros(14); k2 = np.zeros(14); k3 = np.zeros(14); k4 = np.zeros(14)
    Fv = np.zeros(6)
    eb0, el0 = _energy_parts(x0, K, kf, mf)
    eref = eb0 + el0 + 1e-6
    ypk = 0.0
    for s in range(H):
        t = s * dtl
        u = u_try + (u_cur - u_try) * np.exp(-t / TAU_V)
        fp = fp_try + (fp_cur - fp_try) * np.exp(-t / TAU_P)
        xi = u * xi_opt
        _deriv(x, 0.0, Fv, xi, fp, K, C, Minv, kf, cnl_unit, Rg, mf, k1)
        for i in range(14): xt[i] = x[i] + 0.5 * dtl * k1[i]
        _deriv(xt, 0.0, Fv, xi, fp, K, C, Minv, kf, cnl_unit, Rg, mf, k2)
        for i in range(14): xt[i] = x[i] + 0.5 * dtl * k2[i]
        _deriv(xt, 0.0, Fv, xi, fp, K, C, Minv, kf, cnl_unit, Rg, mf, k3)
        for i in range(14): xt[i] = x[i] + dtl * k3[i]
        _deriv(xt, 0.0, Fv, xi, fp, K, C, Minv, kf, cnl_unit, Rg, mf, k4)
        for i in range(14):
            x[i] += dtl / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
        if abs(x[12]) > ypk: ypk = abs(x[12])
    eb, el = _energy_parts(x, K, kf, mf)
    pen = 0.0
    if ypk > 0.85 * YMAX:
        pen = ((ypk - 0.85 * YMAX) / (0.15 * YMAX)) ** 2
    return (eb + wl * el) / eref + 0.3 * pen + 0.02 * (fp_try / FP_MAX) ** 2


UCAND = np.array([0.6, 1.0, 1.5, 2.0])


NWIN = 40
NEST_H = 24
NEST = (NWIN + 1) * NEST_H + NEST_H + NEST_H + 1
TRIG = float(os.environ.get('W6_TRIG', 0.3))
VMIN = float(os.environ.get('W6_VMIN', 0.6))
VMAX = float(os.environ.get('W6_VMAX', 2.0))
TAU_G = float(os.environ.get('W6_TAUG', 3.0))           # s, 공기압(튜닝비 γ) 변경 지연 (5주차 가정과 동일)


@njit(cache=True)
def est_forward(est, win, rms):
    """최근 NWIN개 상대가속도(10Hz, 평균) -> 강성비 f/f0 추정 (MLP 41-24-1)"""
    h = np.empty(NEST_H)
    for j in range(NEST_H):
        s = est[(NWIN + 1) * NEST_H + j]
        for i in range(NWIN):
            s += est[i * NEST_H + j] * (win[i] / rms)
        s += est[NWIN * NEST_H + j] * np.log10(rms)
        h[j] = np.tanh(s)
    p = (NWIN + 1) * NEST_H + NEST_H
    z = est[p + NEST_H]
    for j in range(NEST_H):
        z += est[p + j] * h[j]
    return 0.5 + 0.6 / (1.0 + np.exp(-z))


@njit(cache=True)
def dft_peak(win):
    """고전 추정기: 10Hz 윈도의 DFT 피크(0.4~1.1Hz, 0.01Hz 격자) -> f/f0"""
    best = -1.0; bf = F1
    for k in range(70):
        fr = 0.40 + 0.01 * k
        re = 0.0; im = 0.0
        for i in range(NWIN):
            w = 0.5 - 0.5 * np.cos(2 * np.pi * i / (NWIN - 1))
            ph = 2 * np.pi * fr * i * 0.1
            re += w * win[i] * np.cos(ph); im += w * win[i] * np.sin(ph)
        pw = re * re + im * im
        if pw > best:
            best = pw; bf = fr
    return bf / F1


@njit(cache=True)
def rollout(ag, Fext, jf, K, C, Minv, mf, kf, cnl_unit, Rg, xi_opt,
            mode, param, theta, noise_a, noise_y, record,
            hist, fdata, adata, cnt, pneu_on,
            K2, C2, s_sw, est, gmode, fs_final, fs_init, wdata, wlab, wcnt):
    """
    mode 0 무제어 / 1 고정 scale=param / 2 Delta-DBG / 3 NN정책 / 5 MPC교사 / 6 DAgger(학생 조종+교사 라벨)
    gmode 0 γ재튜닝 없음 / 1 오라클(손상 후 참값) / 2 AI 추정기 / 3 추정기 학습용 데이터 수집(재튜닝 없음)
    """
    x = np.zeros(14)
    k1 = np.zeros(14); k2 = np.zeros(14); k3 = np.zeros(14); k4 = np.zeros(14)
    xt = np.zeros(14)
    Fv = np.zeros(6)
    Kc = K; Cc = C
    u_act = 1.0
    if mode == 1:
        u_act = param
    if mode == 8:
        u_act = theta[2]
    u_cmd = u_act
    fp_cmd = 0.0; fp_act = 0.0
    v_hat = 0.0; d_hat = 0.0; env = 0.0
    y_prev = 0.0; yd_hat = 0.0
    d_hat_prev = 0.0
    triggered = False; t_trig = 0.0
    a_meas_delayed = 0.0
    standby = theta[NTHETA - 1] if (mode == 3 or mode == 6) else 1.0
    f = np.zeros(NF)
    sum_fp2 = 0.0
    sum_d2 = 0.0; sum_d2_late = 0.0; n_late = 0
    peak_d = 0.0; peak_idr = 0.0; peak_acc = 0.0; max_y = 0.0; hs = 0
    t_late = TEND - 10.0
    acc_rel = 0.0
    tau_int = 4.0
    gam_cur = GAMMA0; gam_tgt = GAMMA0
    kfc = kf
    win = np.zeros(NWIN); nw = 0; acc_sum = 0.0; acc_n = 0
    f_est_last = 1.0
    for s in range(NSTEP):
        t = s * DT
        if s == s_sw:
            Kc = K2; Cc = C2
        if s % NSUB == 0:
            a_meas = a_meas_delayed + noise_a[s]
            y_meas = x[12] + noise_y[s]
            a_meas_delayed = acc_rel
            v_hat += (a_meas - v_hat / tau_int) * TC
            d_hat += (v_hat - d_hat / tau_int) * TC
            yd_raw = (y_meas - y_prev) / TC
            yd_hat = 0.7 * yd_hat + 0.3 * yd_raw
            y_prev = y_meas
            env = max(abs(d_hat), env * np.exp(-TC / 3.0))
            if (not triggered) and abs(a_meas) > TRIG:
                triggered = True; t_trig = t
            # --- 가속도 윈도(10 Hz) 및 γ 재튜닝 ---
            acc_sum += a_meas; acc_n += 1
            if acc_n == 10:
                for q in range(NWIN - 1): win[q] = win[q + 1]
                win[NWIN - 1] = acc_sum / 10.0
                acc_sum = 0.0; acc_n = 0; nw += 1
                if gmode == 1:
                    if t > s_sw * DT + 0.5:
                        gam_tgt = GAMMA0 * min(fs_final, 1.0)
                elif gmode == 2 or gmode == 3 or gmode == 4:
                    if nw >= NWIN and (nw % 5 == 0):
                        rms = 0.0
                        for q in range(NWIN): rms += win[q] ** 2
                        rms = np.sqrt(rms / NWIN)
                        if rms > 0.15:
                            if gmode == 4:
                                fe = dft_peak(win)
                            else:
                                fe = est_forward(est, win, rms)
                            f_est_last = fe
                            if gmode == 3 and wcnt[0] < wdata.shape[0]:
                                for q in range(NWIN): wdata[wcnt[0], q] = win[q] / rms
                                wdata[wcnt[0], NWIN] = np.log10(rms)
                                wlab[wcnt[0]] = fs_final if s >= s_sw else fs_init
                                wcnt[0] += 1
                            if gmode == 2 or gmode == 4:
                                tgt = GAMMA0 * min(fe, 1.0)
                                gam_tgt = 0.6 * gam_tgt + 0.4 * max(tgt, GAMMA0 * 0.55)
            if mode == 1:
                u_cmd = param
            elif mode == 2:
                dd = d_hat - d_hat_prev
                if triggered:
                    if dd * yd_hat <= 0.0:
                        u_cmd = VMAX
                    else:
                        u_cmd = VMIN
                else:
                    u_cmd = 1.0
            elif mode == 7:
                u_cmd = 1.0
                if triggered and abs(y_meas) > param * YMAX:
                    u_cmd = 2.0
            elif mode == 8:
                if triggered:
                    if t - t_trig < theta[1]:
                        u_cmd = param
                    else:
                        u_cmd = theta[0]
                else:
                    u_cmd = theta[2]
            elif mode == 3:
                if triggered:
                    f[0] = d_hat / 0.15; f[1] = v_hat / 0.8; f[2] = a_meas / 6.0
                    f[3] = y_meas / YMAX; f[4] = yd_hat / 2.5; f[5] = env / 0.15
                    f[6] = min((t - t_trig) / 10.0, 2.0); f[7] = (u_act - 1.3) / 0.7; f[8] = 1.0
                    u_cmd, fpn = policy_forward(theta, f)
                    fp_cmd = fpn * FP_MAX * pneu_on
                    if x[12] * fp_cmd > 0.0 and abs(x[12]) > 0.9 * YMAX:
                        fp_cmd = 0.0
                else:
                    u_cmd = standby; fp_cmd = 0.0
            if mode == 5 or mode == 6:
                f[0] = d_hat / 0.15; f[1] = v_hat / 0.8; f[2] = a_meas / 6.0
                f[3] = y_meas / YMAX; f[4] = yd_hat / 2.5; f[5] = env / 0.15
                f[6] = min((t - t_trig) / 10.0, 2.0); f[7] = (u_act - 1.3) / 0.7; f[8] = 1.0
                if triggered and ((s // NSUB) % 10 == 0):
                    best = 1e18; bu = 1.0; bf = 0.0
                    nf_c = 3 if pneu_on > 0.5 else 1
                    for iu in range(4):
                        for ifp in range(nf_c):
                            fpt = 0.0
                            if nf_c == 3:
                                fpt = (ifp - 1) * FP_MAX
                            c = _look(x, u_act, fp_act, UCAND[iu], fpt, Kc, Cc, Minv, kfc, cnl_unit, Rg, mf, xi_opt, 240, 0.3)
                            if c < best:
                                best = c; bu = UCAND[iu]; bf = fpt
                    if cnt[0] < fdata.shape[0]:
                        for q in range(NF): fdata[cnt[0], q] = f[q]
                        adata[cnt[0], 0] = (bu - 0.6) / 1.4
                        adata[cnt[0], 1] = bf / FP_MAX
                        cnt[0] += 1
                    if mode == 5:
                        u_cmd = bu; fp_cmd = bf
                if mode == 6 and triggered:
                    u_cmd, fpn = policy_forward(theta, f)
                    fp_cmd = fpn * FP_MAX * pneu_on
                    if x[12] * fp_cmd > 0.0 and abs(x[12]) > 0.9 * YMAX:
                        fp_cmd = 0.0
                if not triggered:
                    u_cmd = 1.0; fp_cmd = 0.0
            d_hat_prev = d_hat
        if mode == 1:
            u_act = param
        else:
            u_act += (u_cmd - u_act) * (DT / TAU_V)
        fp_act += (fp_cmd - fp_act) * (DT / TAU_P)
        gam_cur += (gam_tgt - gam_cur) * (DT / TAU_G)
        kfc = mf * (gam_cur * W1) ** 2
        xi = u_act * xi_opt
        a0 = ag[s]
        a1 = 0.5 * (ag[s] + ag[min(s + 1, NSTEP - 1)])
        a2 = ag[min(s + 1, NSTEP - 1)]
        for i in range(6):
            Fv[i] = 0.0
        Fv[jf] = Fext[s]
        f_mid = 0.5 * (Fext[s] + Fext[min(s + 1, NSTEP - 1)])
        f_end = Fext[min(s + 1, NSTEP - 1)]
        _deriv(x, a0, Fv, xi, fp_act, Kc, Cc, Minv, kfc, cnl_unit, Rg, mf, k1)
        for i in range(14): xt[i] = x[i] + 0.5 * DT * k1[i]
        Fv[jf] = f_mid
        _deriv(xt, a1, Fv, xi, fp_act, Kc, Cc, Minv, kfc, cnl_unit, Rg, mf, k2)
        for i in range(14): xt[i] = x[i] + 0.5 * DT * k2[i]
        _deriv(xt, a1, Fv, xi, fp_act, Kc, Cc, Minv, kfc, cnl_unit, Rg, mf, k3)
        for i in range(14): xt[i] = x[i] + DT * k3[i]
        Fv[jf] = f_end
        _deriv(xt, a2, Fv, xi, fp_act, Kc, Cc, Minv, kfc, cnl_unit, Rg, mf, k4)
        for i in range(14):
            x[i] += DT / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
        acc_rel = k1[11]
        sum_fp2 += (fp_act / FP_MAX) ** 2
        d = x[5]
        sum_d2 += d * d
        if t >= t_late:
            sum_d2_late += d * d; n_late += 1
        ad = abs(d)
        if ad > peak_d: peak_d = ad
        idr = abs(x[0])
        for i in range(1, 6):
            v = abs(x[i] - x[i - 1])
            if v > idr: idr = v
        if idr > peak_idr: peak_idr = idr
        aa = abs(acc_rel + ag[s])
        if aa > peak_acc: peak_acc = aa
        yy = abs(x[12])
        if yy > max_y: max_y = yy
        if yy > YMAX: hs += 1
        if record:
            hist[s, 0] = d; hist[s, 1] = x[12]; hist[s, 2] = u_act
            hist[s, 3] = acc_rel + ag[s]; hist[s, 4] = gam_cur; hist[s, 5] = ag[s]
    m = np.zeros(10)
    m[8] = sum_fp2 / NSTEP
    m[0] = np.sqrt(sum_d2 / NSTEP)
    m[1] = np.sqrt(sum_d2_late / max(n_late, 1))
    m[2] = peak_d
    m[3] = peak_idr
    m[4] = peak_acc
    m[5] = max_y
    m[6] = hs * DT
    m[7] = 1.0 if triggered else 0.0
    m[9] = gam_cur
    return m
