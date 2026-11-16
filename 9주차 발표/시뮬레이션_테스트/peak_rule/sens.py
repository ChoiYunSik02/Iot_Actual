"""9주차 계획 5절: 잡음·지연 민감도. dev 기록만 쓴다 (원문 15쌍 + dev_paper_event 18쌍, 4사건). test 세트는 쓰지 않는다.

- 지연: 느린 지령(펌프 진동수·회전판 목표각)을 결정 후 d초 뒤 적용. d = 0, 0.1, 0.2, 0.5, 1.0 s. R과 PEAK에 같게 준다.
- 잡음: 제어기가 읽는 옥상 X·Y 변위에 백색 잡음. 표준편차 = p × (그 기록 무제어 옥상 변위 RMS), p = 1, 5, 10 %, 시드 5개.
  R의 웨이블릿 진동수 식별·각도 창과 PEAK의 피크 판정이 모두 잡음 섞인 값을 읽는다.
  밸브(속도·가속도 부호)는 잡음 없이 둔다. 응답 평가는 실제 응답으로 한다.
PEAK는 peak_rule.Peak 동결본 그대로다. 잡음 때문에 고친 규칙은 여기서 만들지 않는다.
"""
import os, sys, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak

DELAYS = [0.0, 0.1, 0.2, 0.5, 1.0]
NOISE = [0.01, 0.05, 0.10]
SEEDS = range(5)
POL = {'R': lambda dt: Tracked(dt), 'PEAK': lambda dt: Peak(dt)}


class Noisy:
    """정책이 읽는 변위 이력에만 잡음을 더한다."""
    def __init__(s, pol, nx, ny):
        s.p, s.nx, s.ny, s.nc = pol, nx, ny, pol.nc
        s.hx = np.empty(len(nx)); s.hy = np.empty(len(ny))

    def decide(s, ob, hx, hy, th):
        k = ob.k; s.hx[k] = hx[k] + s.nx[k]; s.hy[k] = hy[k] + s.ny[k]
        return s.p.decide(ob, s.hx, s.hy, th)

    def decide_fast(s, ob, th):
        return s.p.decide_fast(ob, th)


_plants = {}


def job(a):
    kind, pol, rec, j, d, p, seed, urms = a
    ax, ay, dt = load(rec)
    if kind == 'U': return a[:7], uncontrolled(ax, ay, dt).tolist(), 0
    if dt not in _plants: _plants[dt] = Plant(dt)
    # ponytail: 이산 행렬 캐시(rs_ref 기본 상한 2000개, 개당 약 0.5 MB)가 작업자 15개에서 메모리를 다 씀 -> 200개로 제한. 결과는 같다
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    P = POL[pol](dt); ctrl = P
    if p > 0:
        g = np.random.default_rng([seed, j, 8600])
        ctrl = Noisy(P, g.normal(0, p * urms[0], len(ax)), g.normal(0, p * urms[1], len(ax)))
    y, _, _ = simulate(_plants[dt], ax, ay, ctrl, delay_slow=int(round(d / dt)))
    return a[:7], metrics(y).tolist(), getattr(P, 'n_peak', 0)


def gains(recs, U, res, d, p, seed):
    ev = lambda r: r[1].replace(',', '').split()[0]
    red = {pol: np.array([(1 - np.array(res[(pol, j, d, p, seed)][0]) / U[j]).mean() * 100 for j in range(len(recs))])
           for pol in POL}
    dr = red['PEAK'] - red['R']; evs = sorted({ev(r) for r in recs})
    de = [dr[[j for j, r in enumerate(recs) if ev(r) == e]].mean() for e in evs]
    return dict(dS_rec=float(dr.mean()), dS_evt=float(np.mean(de)), n_better=int((dr > 0).sum()),
                R_rec=float(red['R'].mean()), PEAK_rec=float(red['PEAK'].mean()),
                n_peak_per_rec=float(np.mean([res[('PEAK', j, d, p, seed)][1] for j in range(len(recs))])))


if __name__ == '__main__':
    t0 = time.time()
    recs = rs.record_list('paper15') + rs.record_list('dev')
    with ProcessPoolExecutor(max_workers=12) as ex:
        U = {a[3]: np.array(m) for a, m, _ in ex.map(job, [('U', None, rec, j, 0, 0, 0, None) for j, rec in enumerate(recs)])}
        U = [U[j] for j in range(len(recs))]
        urms = [(u[1] / 100, u[3] / 100) for u in U]  # metrics의 cm 단위 → m
        conds = [(d, 0.0, 0) for d in DELAYS] + [(0.0, p, s) for p in NOISE for s in SEEDS]
        jobs = [('C', pol, rec, j, d, p, s, urms[j]) for d, p, s in conds for pol in POL for j, rec in enumerate(recs)]
        res = {}
        for a, m, npk in ex.map(job, [(k, pol, rec, j, d, p, s, u) for k, pol, rec, j, d, p, s, u in jobs], chunksize=4):
            _, pol, _, j, d, p, s = a; res[(pol, j, d, p, s)] = (m, npk)
            if len(res) % 100 == 0: print(f'{len(res)}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    print(f'{len(jobs) + len(recs)} runs, {time.time() - t0:.0f}s')
    out = dict(records=[r[0] for r in recs], delay={}, noise={})
    print(f"{'condition':16s} {'R%':>6s} {'PEAK%':>6s} {'dS_rec':>7s} {'dS_evt':>7s} better peaks/rec")
    for d in DELAYS:
        g = gains(recs, U, res, d, 0.0, 0); out['delay'][str(d)] = g
        print(f"delay {d:4.1f} s     {g['R_rec']:6.2f} {g['PEAK_rec']:6.2f} {g['dS_rec']:+7.2f} {g['dS_evt']:+7.2f} {g['n_better']:3d}/{len(recs)} {g['n_peak_per_rec']:7.1f}")
    for p in NOISE:
        G = [gains(recs, U, res, 0.0, p, s) for s in SEEDS]; out['noise'][str(p)] = G
        a = lambda k: np.array([g[k] for g in G])
        print(f"noise {p * 100:4.0f} %      {a('R_rec').mean():6.2f} {a('PEAK_rec').mean():6.2f} {a('dS_rec').mean():+7.2f}"
              f" {a('dS_evt').mean():+7.2f} {a('n_better').mean():5.1f} {a('n_peak_per_rec').mean():7.1f}"
              f"   seed range dS_evt [{a('dS_evt').min():+.2f}, {a('dS_evt').max():+.2f}]")
    # 회귀: 잡음 0·지연 0에서 원문 15쌍 부분은 PEAK - R = +3.00 %p (v19, run_set paper15)
    assert abs(gains(recs[:15], U[:15], res, 0.0, 0.0, 0)['dS_rec'] - 3.00) < 0.005
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_sens.json'), 'w'), indent=1)
