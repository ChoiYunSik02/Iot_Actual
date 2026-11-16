"""비틀림 보호 변형 (dev 기록만: 원문 15쌍 + dev 18쌍, 4사건). test 세트는 쓰지 않는다.

문제: PEAK는 R보다 6지표 평균은 좋지만 비틀림 최대가 R보다 나빠지는 기록이 계속 나온다 (test 5/25, dev 15/33).
변형 (실행 전에 정함):
  G_R  : 옥상 비틀림각 |θ|가 지금까지 최대의 80% 이상이 되면 (5 s 이후) 2.6 s 동안 보호 모드.
         보호 모드에서는 피크 지령을 버리고, 진입 순간 R과 같은 방향(지난 2.6 s 최대 변위 방향)으로 지령한다.
  G_45 : 같은 진입 조건, 보호 모드 지령은 45°.
  PULL25: 보호 모드 없이 45° 쪽 당김을 0.5에서 0.75로 (θ* = 45° + 0.25(φ − 45°)). 회전판 움직임을 줄인다.
선택 기준 (실행 전에 정함): dev 사건 평균 ΔS(− R) ≥ +1.5%p인 변형 가운데 비틀림 최대 악화 기록 수가 가장 적은 것.
  동률이면 ΔS가 큰 것. 어느 것도 PEAK보다 악화 기록이 적지 않으면 "보호 변형 실패"로 쓴다.
"""
import os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak, Fix45
from sim_layer import IDX
from peak_v2 import PeakV2


class Guard(Peak):
    def __init__(s, dt, mode, frac_t=0.8, hold=2.6, warm=5.0):
        super().__init__(dt); s.mode, s.ft = mode, frac_t
        s.hold, s.warm, s.nw = int(round(hold / dt)), int(round(warm / dt)), int(round(2.6 / dt))
        s.tmax = 0.0; s.until = -1; s.n_guard = 0

    def decide(s, ob, hx, hy, th_act):
        k = ob.k; t = abs(ob.x[IDX['tt']])
        out = super().decide(ob, hx, hy, th_act)  # 피크 판정 상태는 계속 갱신
        if k >= s.warm and t >= s.ft * s.tmax and k > s.until:
            s.until = k + s.hold; s.n_guard += 1
            if s.mode == 'R':
                a = slice(max(0, k - s.nw + 1), k + 1)
                tht = np.arctan2(np.abs(hy[a]).max(), np.abs(hx[a]).max())
            else:
                tht = np.pi / 4
            out = [o for o in out if 'tht' not in o[1]] + [('slow', {'tht': tht}, (4, k, k * s.dt, 0, np.rad2deg(tht), 0, 0))]
        elif k <= s.until:
            out = [o for o in out if 'tht' not in o[1]]
        s.tmax = max(s.tmax, t)
        return out


POL = {'R': lambda dt: Tracked(dt), 'FIX45': lambda dt: Fix45(dt), 'PEAK': lambda dt: Peak(dt),
       'LP': lambda dt: PeakV2(dt, gap=0.0),
       'G_R': lambda dt: Guard(dt, 'R'), 'G_45': lambda dt: Guard(dt, '45'), 'PULL25': lambda dt: Peak(dt, pull=0.25)}
_plants = {}


def job(a):
    pol, rec, j = a
    ax, ay, dt = load(rec)
    if pol == 'U': return a, uncontrolled(ax, ay, dt).tolist(), 0
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    P = POL[pol](dt); y, _, _ = simulate(_plants[dt], ax, ay, P)
    return a, metrics(y).tolist(), getattr(P, 'n_guard', 0)


def compare(recs, res, U, pol, base='R'):
    ev = lambda r: r[1].replace(',', '').split()[0]; evs = sorted({ev(r) for r in recs})
    red = lambda q: np.array([(1 - np.array(res[(q, j)][0]) / U[j]) * 100 for j in range(len(recs))])  # 기록 × 6지표
    a, b = red(pol), red(base); d = a.mean(1) - b.mean(1)
    return dict(score=float(a.mean()), dS_rec=float(d.mean()),
                dS_evt=float(np.mean([d[[j for j, r in enumerate(recs) if ev(r) == e]].mean() for e in evs])),
                n_better=int((d > 0).sum()), thmax_worse=int((a[:, 4] < b[:, 4] - 1e-9).sum()),
                thmax_worst=float((a[:, 4] - b[:, 4]).min()), thrms_worse=int((a[:, 5] < b[:, 5] - 1e-9).sum()),
                per_metric=(a - b).mean(0).round(2).tolist(),
                n_guard=float(np.mean([res[(pol, j)][1] for j in range(len(recs))])))


if __name__ == '__main__':
    t0 = time.time()
    recs = rs.record_list('paper15') + rs.record_list('dev')
    jobs = [(p, rec, j) for p in ['U'] + list(POL) for j, rec in enumerate(recs)]
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = {(a[0], a[2]): (m, g) for a, m, g in ex.map(job, jobs, chunksize=2)}
    U = [np.array(res[('U', j)][0]) for j in range(len(recs))]
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s')
    out = {p: compare(recs, res, U, p) for p in POL if p != 'R'}
    assert abs(compare(recs[:15], res, U[:15], 'PEAK')['dS_rec'] - 3.00) < 0.005  # 회귀 (v19)
    print(f"{'pol':7s} {'score':>6s} {'dS_evt':>7s} better thmax_worse worst  thrms_worse guards  per-metric(Xmax,Xrms,Ymax,Yrms,θmax,θrms)")
    for p, o in out.items():
        print(f"{p:7s} {o['score']:6.2f} {o['dS_evt']:+7.2f} {o['n_better']:4d}/33 {o['thmax_worse']:5d}/33 {o['thmax_worst']:+6.2f}"
              f" {o['thrms_worse']:5d}/33 {o['n_guard']:6.1f}  {o['per_metric']}")
    ok = [p for p in ('G_R', 'G_45', 'PULL25') if out[p]['dS_evt'] >= 1.5 and out[p]['thmax_worse'] < out['PEAK']['thmax_worse']]
    pick = min(ok, key=lambda p: (out[p]['thmax_worse'], -out[p]['dS_evt'])) if ok else None
    print('선택:', pick or '없음 (보호 변형 실패)')
    out['pick'] = pick
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_guard.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
