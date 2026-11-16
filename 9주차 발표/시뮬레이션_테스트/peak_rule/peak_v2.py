"""피크 규칙 v2: 잡음에 강한 피크 판정 (9주차 계획 5절의 '새 버전'). dev 기록만 쓴다. test 세트로는 평가하지 않는다.

v1(peak_rule.Peak, 동결)은 바로 앞 샘플과 비교해 피크를 정한다. 변위 잡음 1%만 넣어도 피크 판정이
기록당 31회에서 1,206회로 늘었다 (sens.py). v2는 피크 판정에만 두 가지를 더한다.
  LP : 피크 판정용 변위에 인과 2차 Butterworth 저역통과 (차단 1 Hz, 건물 0.33 Hz의 3배). 펌프·밸브 입력은 원래 값.
  GAP: 앞 피크 뒤 최소 1.0 s 안의 피크는 버린다 (r = |변위|의 피크 간격은 반주기 약 1.5 s).
나머지(30% 문턱, 45° 쪽 0.5 당김, 회전 30°/s)는 v1과 같다.
잡음·시드·기록은 sens.py와 같아서 R, PEAK 값이 sens 결과와 일치해야 한다 (회귀 확인).
"""
import os, json, time
import numpy as np
from scipy.signal import butter
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak, RPolicy
from sens import Noisy


class PeakV2(Tracked):
    def __init__(s, dt, fc=1.0, gap=1.0, frac=0.3, pull=0.5):
        super().__init__(dt); s.frac, s.pull = frac, pull
        s.b, s.a = butter(2, fc, fs=1 / dt) if fc else (np.array([1., 0, 0]), np.array([1., 0, 0]))
        s.zx = np.zeros(2); s.zy = np.zeros(2); s.gap = int(round(gap / dt))
        s.r1 = s.r2 = s.rmax = 0.0; s.p1 = (0.0, 0.0); s.last = -10 ** 9; s.n_peak = 0

    def lp(s, u, z):  # direct form II transposed, 1스텝
        b, a = s.b, s.a; y = b[0] * u + z[0]
        z[0] = b[1] * u - a[1] * y + z[1]; z[1] = b[2] * u - a[2] * y
        return y

    def decide(s, ob, hx, hy, th_act):
        s.track(th_act); k = ob.k
        out = [(kind, {'f': cmd['f']}, rec) for kind, cmd, rec in RPolicy.decide(s, ob, hx, hy, th_act)]
        x, y = s.lp(hx[k], s.zx), s.lp(hy[k], s.zy); r = np.hypot(x, y)
        if k >= 2 and s.r1 > s.r2 and r < s.r1 and s.r1 >= s.frac * s.rmax and k - 1 - s.last >= s.gap:
            phi = np.arctan2(abs(s.p1[1]), abs(s.p1[0]))
            tht = np.pi / 4 + s.pull * (phi - np.pi / 4)
            out.append(('slow', {'tht': tht}, (3, k, k * s.dt, np.rad2deg(phi), np.rad2deg(tht), 0, 0)))
            s.n_peak += 1; s.last = k - 1
        s.rmax = max(s.rmax, r); s.r2, s.r1 = s.r1, r; s.p1 = (x, y)
        return out


POL = {'R': lambda dt: Tracked(dt), 'PEAK': lambda dt: Peak(dt),
       'LP': lambda dt: PeakV2(dt, gap=0.0), 'GAP': lambda dt: PeakV2(dt, fc=0), 'LPGAP': lambda dt: PeakV2(dt)}
NOISE = [0.0, 0.01, 0.05, 0.10]
SEEDS = range(5)
_plants = {}


def job(a):
    kind, pol, rec, j, d, p, seed, urms = a
    ax, ay, dt = load(rec)
    if kind == 'U': return a[:7], uncontrolled(ax, ay, dt).tolist(), 0
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()  # sens.py와 같은 메모리 제한
    P = POL[pol](dt); ctrl = P
    if p > 0:
        g = np.random.default_rng([seed, j, 8600])  # sens.py와 같은 잡음
        ctrl = Noisy(P, g.normal(0, p * urms[0], len(ax)), g.normal(0, p * urms[1], len(ax)))
    y, _, _ = simulate(_plants[dt], ax, ay, ctrl, delay_slow=int(round(d / dt)))
    return a[:7], metrics(y).tolist(), getattr(P, 'n_peak', 0)


def gains(recs, U, res, pol, d, p, seed):
    ev = lambda r: r[1].replace(',', '').split()[0]
    red = lambda q: np.array([(1 - np.array(res[(q, j, d, p, seed)][0]) / U[j]).mean() * 100 for j in range(len(recs))])
    dr = red(pol) - red('R'); evs = sorted({ev(r) for r in recs})
    m = np.array([res[(pol, j, d, p, seed)][0] for j in range(len(recs))]) / np.array(U)
    mr = np.array([res[('R', j, d, p, seed)][0] for j in range(len(recs))]) / np.array(U)
    return dict(dS_rec=float(dr.mean()), dS_evt=float(np.mean([dr[[j for j, r in enumerate(recs) if ev(r) == e]].mean() for e in evs])),
                n_better=int((dr > 0).sum()), score=float(red(pol).mean()),
                n_thmax_worse=int((m[:, 4] > mr[:, 4] + 1e-12).sum()),
                n_peak=float(np.mean([res[(pol, j, d, p, seed)][1] for j in range(len(recs))])))


if __name__ == '__main__':
    t0 = time.time()
    recs = rs.record_list('paper15') + rs.record_list('dev')
    with ProcessPoolExecutor(max_workers=12) as ex:
        U = {a[3]: np.array(m) for a, m, _ in ex.map(job, [('U', None, rec, j, 0, 0, 0, None) for j, rec in enumerate(recs)])}
        U = [U[j] for j in range(len(recs))]
        urms = [(u[1] / 100, u[3] / 100) for u in U]
        conds = [(0.0, p, s) for p in NOISE for s in (SEEDS if p else [0])] + [(0.5, 0.0, 0)]
        jobs = [('C', pol, rec, j, d, p, s, urms[j]) for d, p, s in conds for pol in POL for j, rec in enumerate(recs)]
        res = {}
        for a, m, npk in ex.map(job, jobs, chunksize=4):
            _, pol, _, j, d, p, s = a; res[(pol, j, d, p, s)] = (m, npk)
            if len(res) % 200 == 0: print(f'{len(res)}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    print(f'{len(jobs) + len(recs)} runs, {time.time() - t0:.0f}s')
    out = {}
    print(f"{'cond':12s} {'pol':6s} {'score':>6s} {'dS_rec':>7s} {'dS_evt':>7s} better thmax_worse peaks/rec")
    for d, p in [(0.0, q) for q in NOISE] + [(0.5, 0.0)]:
        for pol in POL:
            if pol == 'R': continue
            G = [gains(recs, U, res, pol, d, p, s) for s in (SEEDS if p else [0])]
            A = {k: float(np.mean([g[k] for g in G])) for k in G[0]}
            A['dS_evt_range'] = [min(g['dS_evt'] for g in G), max(g['dS_evt'] for g in G)]
            out[f'd{d}_n{p}_{pol}'] = A
            print(f"d{d} n{p * 100:3.0f}%  {pol:6s} {A['score']:6.2f} {A['dS_rec']:+7.2f} {A['dS_evt']:+7.2f} {A['n_better']:5.1f}"
                  f" {A['n_thmax_worse']:5.1f} {A['n_peak']:8.1f}  [{A['dS_evt_range'][0]:+.2f}, {A['dS_evt_range'][1]:+.2f}]")
    # 회귀: v1 PEAK는 sens.py 결과와 같아야 한다
    assert abs(out['d0.0_n0.0_PEAK']['dS_evt'] - 2.18) < 0.01 and abs(out['d0.0_n0.01_PEAK']['dS_evt'] - 1.41) < 0.01
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_v2.json'), 'w'), indent=1)
