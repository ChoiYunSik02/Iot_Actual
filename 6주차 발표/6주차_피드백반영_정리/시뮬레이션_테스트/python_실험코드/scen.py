"""경보 없는 즉시 충격 시나리오 생성기 (t=0 에 이미 충격 시작, 사전 정보 없음)"""
import numpy as np
from scipy.signal import lfilter
import sim
from sim import *

T = np.arange(NSTEP) * DT
MGEN = sim.MFLOOR * float(sim.PHI @ sim.PHI)   # 옥상정규화 일반화질량
OMEGA1 = sim.W1
PHI = sim.PHI

KINDS = ["pulse", "impact", "burst"]


def _kt_noise(rng, dur, wg, zg, dt=DT):
    n = NSTEP
    w = rng.standard_normal(n)
    # Kanai-Tajimi 필터 (이산 2차 근사, bilinear)
    from scipy.signal import bilinear
    b, a = [2 * zg * wg, wg ** 2], [1, 2 * zg * wg, wg ** 2]
    # 가속도 전달함수: (2 zg wg s + wg^2)/(s^2+2 zg wg s+wg^2)
    bd, ad = bilinear(b, a, fs=1 / dt)
    x = lfilter(bd, ad, w)
    return x / np.std(x)


def gen_scenario(rng, kind=None, aftershock=None, level=None):
    """level: 'train' 보통 / 'extreme' 더 극한"""
    if kind is None:
        kind = rng.choice(KINDS, p=[0.35, 0.30, 0.35])
    ext = (level == "extreme")
    ag = np.zeros(NSTEP)
    F = np.zeros(NSTEP)
    jf = 5
    pga_lo, pga_hi = (0.5, 1.2) if ext else (0.2, 0.8)
    info = {"kind": kind}

    def add_event(t0, scale, kind, rng):
        nonlocal ag, F, jf
        i0 = int(t0 / DT)
        if kind == "pulse":
            A = np.exp(rng.uniform(np.log(pga_lo), np.log(pga_hi))) * G * scale
            Tp = np.exp(rng.uniform(np.log(0.5), np.log(4.0)))
            ncyc = rng.choice([0.5, 1.0, 1.5])
            L = int(ncyc * Tp / DT)
            tt = np.arange(L) * DT
            w = np.sin(2 * np.pi * tt / Tp) if ncyc != 0.5 else np.sin(np.pi * tt / (0.5 * Tp * 2) )
            if ncyc != 0.5:
                w = np.sin(2 * np.pi * tt / Tp) * (0.5 * (1 - np.cos(np.pi * np.minimum(tt / (0.25 * Tp), 1.0))))
            # 고주파 꼬리
            tail = _kt_noise(rng, 4.0, 2 * np.pi * rng.uniform(2, 6), 0.5)
            env = np.exp(-np.maximum(T - t0 - ncyc * Tp, 0) / 1.5) * (T >= t0)
            pulse = np.zeros(NSTEP)
            n = min(L, NSTEP - i0)
            pulse[i0:i0 + n] = w[:n]
            sgn = rng.choice([-1, 1])
            ag += sgn * A * (pulse + 0.15 * tail * env * (T >= t0))
            return {"A_g": A / G, "Tp": Tp}
        if kind == "burst":
            A = np.exp(rng.uniform(np.log(pga_lo), np.log(pga_hi))) * G * scale
            wg = 2 * np.pi * rng.uniform(0.5, 4.0)
            zg = rng.uniform(0.3, 0.8)
            dur = rng.uniform(3.0, 9.0)
            x = _kt_noise(rng, dur, wg, zg)
            env = np.where(T < t0, 0.0, np.where(T < t0 + dur, 1.0, np.exp(-(T - t0 - dur) / 2.0)))
            sig = x * env
            sig *= A / max(np.max(np.abs(sig)), 1e-9)
            ag += sig
            return {"A_g": A / G, "fg": wg / 2 / np.pi, "dur": dur}
        if kind == "impact":
            j = rng.integers(0, 6)
            td = np.exp(rng.uniform(np.log(0.01), np.log(0.15)))
            amp_lo, amp_hi = (0.12, 0.45) if ext else (0.03, 0.30)
            At = np.exp(rng.uniform(np.log(amp_lo), np.log(amp_hi))) * scale  # 목표 옥상 진폭(m)
            imp = At * MGEN * OMEGA1 / PHI[j]
            Lq = int(td / DT) + 1
            tt = np.arange(Lq) * DT
            pulse = np.sin(np.pi * tt / td)
            pulse *= imp / (np.sum(pulse) * DT)
            n = min(Lq, NSTEP - i0)
            if j == jf or True:
                F_j = np.zeros(NSTEP)
                F_j[i0:i0 + n] = pulse[:n]
            # 단일 층 힘만 지원하므로 여러 이벤트는 같은 층 가정 -> 층 고정
            jf = j
            F += F_j
            return {"At": At, "td": td, "floor": int(j)}

    info["ev1"] = add_event(0.0, 1.0, kind, rng)
    if aftershock is None:
        aftershock = rng.random() < 0.35
    if aftershock:
        t0 = rng.uniform(4.0, 14.0)
        sc = rng.uniform(0.3, 1.0)
        # 충격(impact)은 층이 달라질 수 없으므로 같은 종류 재충격
        info["ev2"] = add_event(t0, sc, kind if kind == "impact" else rng.choice(["pulse", "burst"]), rng)
        info["t2"] = t0
    fscale = rng.uniform(0.92, 1.03)
    p_dmg, lo = (0.8, 0.65) if ext else (0.5, 0.85)
    if rng.random() < p_dmg:
        fscale2 = fscale * rng.uniform(lo, 0.98)
        t_sw = rng.uniform(0.3, 2.5)
    else:
        fscale2 = fscale; t_sw = 1.0
    zeta = rng.uniform(0.01, 0.03)
    info["damage"] = float(fscale2 / fscale)
    return dict(ag=ag, F=F, jf=jf, fscale=fscale, fscale2=fscale2, t_sw=t_sw, zeta=zeta, info=info)


def noise_arrays(rng, sig_a=0.02, sig_y=0.002):
    return rng.standard_normal(NSTEP) * sig_a, rng.standard_normal(NSTEP) * sig_y


_SYS_CACHE = {}


def get_sys(fscale, zeta, has_tlcd=True, gamma=GAMMA0):
    return sim.make_system(fscale, zeta, has_tlcd, gamma)


def run(sc, mode, param=1.0, theta=None, xi_opt=1.0, rng=None, record=False, gamma=GAMMA0, noise=None):
    has = mode != 0
    K, C, Minv, mf, kf, cnl, Rg = get_sys(sc["fscale"], sc["zeta"], has, gamma)
    if noise is None:
        noise = noise_arrays(np.random.default_rng(0) if rng is None else rng)
    hist = np.zeros((NSTEP, 6)) if record else np.zeros((1, 6))
    th = theta if theta is not None else np.zeros(sim.NTHETA)
    m = sim.rollout(sc["ag"], sc["F"], sc["jf"], K, C, Minv, mf, kf, cnl, Rg, xi_opt,
                    mode, param, th, noise[0], noise[1], record, hist)
    return (m, hist) if record else m
