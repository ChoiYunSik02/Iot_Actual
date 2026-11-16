"""밸브 매 스텝 판단 + 피크 규칙 (개발 실험). test2 전에 결과를 고정하고, 독립 평가는 test2에서 한 번만 한다.

8주차 상한 시험: R의 밸브를 1 s 대신 매 스텝 판단하면 원문 15쌍에서 +0.79%p였다. 미래 정보는 쓰지 않으므로 실현 가능한 규칙이다.
(밸브 응답이 밀리초 수준이라는 가정. 연구 브리프의 액추에이터 표와 같음)
이 이득이 피크 규칙과 더해지는지 본다. 개발 자료: 원문 15 + dev 18 + test 25 + 8주차 사건 4 = 62쌍, 19사건.
test는 이미 PEAK 평가에 썼으므로 이 실험은 개발 결과다.
"""
import os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled, Tracked, Peak
from peak_v2 import PeakV2
from guard import compare


def every_step(P):
    P.nc = 1; return P


POL = {'R': lambda dt: Tracked(dt), 'R_V': lambda dt: every_step(Tracked(dt)),
       'PEAK': lambda dt: Peak(dt), 'PEAK_V': lambda dt: every_step(Peak(dt)),
       'LP_V': lambda dt: every_step(PeakV2(dt, gap=0.0))}
_plants = {}


def job(a):
    pol, rec, j = a
    ax, ay, dt = load(rec)
    if pol == 'U': return a, uncontrolled(ax, ay, dt).tolist(), 0
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    y, _, _ = simulate(_plants[dt], ax, ay, POL[pol](dt))
    return a, metrics(y).tolist(), 0


if __name__ == '__main__':
    t0 = time.time()
    sets = {s: rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')}
    recs = sum(sets.values(), [])
    jobs = [(p, rec, j) for p in ['U'] + list(POL) for j, rec in enumerate(recs)]
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = {(a[0], a[2]): (m, g) for a, m, g in ex.map(job, jobs, chunksize=2)}
    U = [np.array(res[('U', j)][0]) for j in range(len(recs))]
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s')
    # 회귀: 원문 15쌍 R_V − R = +0.79 (8주차 상한 표), PEAK − R = +3.00
    p15 = compare(recs[:15], res, U[:15], 'R_V'); print('paper15 R_V - R', round(p15['dS_rec'], 2))
    assert abs(compare(recs[:15], res, U[:15], 'PEAK')['dS_rec'] - 3.00) < 0.005
    out = {}
    for name, sl in [('paper15', slice(0, 15)), ('all62', slice(0, len(recs))), ('test25', slice(33, 58))]:
        R = recs[sl]; Us = U[sl]; rr = {(k[0], k[1] - sl.start): v for k, v in res.items() if sl.start <= k[1] < (sl.stop or 10 ** 9)}
        out[name] = {p: compare(R, rr, Us, p) for p in POL if p != 'R'}
        out[name]['PEAK_V_vs_PEAK'] = compare(R, rr, Us, 'PEAK_V', base='PEAK')
        print(f'--- {name} ({len(R)}쌍), R 대비')
        for p, o in out[name].items():
            print(f"{p:15s} score {o['score']:6.2f} dS_evt {o['dS_evt']:+6.2f} dS_rec {o['dS_rec']:+6.2f} better {o['n_better']}/{len(R)}"
                  f" thmax_worse {o['thmax_worse']} per-metric {o['per_metric']}")
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_valve.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
