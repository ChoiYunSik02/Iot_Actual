"""제안 시스템 최종본(LP_V) 지연 확인 (개발 62쌍). test2는 쓰지 않는다.
회전판 지령(느린 지령)과 밸브 지령(빠른 지령)에 같은 지연을 준다. R과 LP_V에 같게 준다.
지연 0, 0.05, 0.1, 0.2, 0.5, 1.0 s. 연구 브리프 연구축 ②(제어 지연)에 대응한다.
"""
import os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled
from run_test2 import POL, effect

D = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]
_plants = {}


def job(a):
    pol, rec, j, d = a
    ax, ay, dt = load(rec)
    if pol == 'U': return (pol, j, d), uncontrolled(ax, ay, dt).tolist()
    if dt not in _plants: _plants[dt] = Plant(dt)
    if len(_plants[dt].cache) > 200: _plants[dt].cache.clear()
    n = int(round(d / dt))
    y, _, _ = simulate(_plants[dt], ax, ay, POL[pol](dt), delay_slow=n, delay_fast=n)
    return (pol, j, d), metrics(y).tolist()


if __name__ == '__main__':
    t0 = time.time(); recs = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    jobs = [('U', r, j, 0.0) for j, r in enumerate(recs)] + [(p, r, j, d) for d in D for p in ('R', 'LP_V') for j, r in enumerate(recs)]
    with ProcessPoolExecutor(max_workers=12) as ex:
        res = {k: np.array(m) for k, m in ex.map(job, jobs, chunksize=2)}
    U = [res[('U', j, 0.0)] for j in range(len(recs))]
    red = lambda p, d: np.array([(1 - res[(p, j, d)] / U[j]) * 100 for j in range(len(recs))])
    out = {}
    for d in D:
        e = effect(recs, {'LP_V': red('LP_V', d), 'R': red('R', d)}, 'LP_V', 'R')
        out[str(d)] = dict(R=float(red('R', d).mean()), LP_V=float(red('LP_V', d).mean()), dS_evt=e['dS_evt'], ci95=e['ci95'],
                           n_rec_better=e['n_rec_better'])
        print(f"delay {d:4.2f} s  R {out[str(d)]['R']:6.2f}  LP_V {out[str(d)]['LP_V']:6.2f}  dS_evt {e['dS_evt']:+.2f}"
              f" [{e['ci95'][0]:+.2f}, {e['ci95'][1]:+.2f}]  better {e['n_rec_better']}/{len(recs)}")
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s')
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_delay_final.json'), 'w'), indent=1)
