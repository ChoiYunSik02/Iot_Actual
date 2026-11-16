"""제안 시스템 최종본(LP_V) 잡음 확인 (개발 62쌍). 잡음 0·5·10 %, 시드 0~4, sens.py와 같은 잡음 생성."""
import os, json, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_test2 import job, effect

if __name__ == '__main__':
    t0 = time.time(); recs = sum((rs.record_list(s) for s in ('paper15', 'dev', 'test', 'week8')), [])
    with ProcessPoolExecutor(max_workers=12) as ex:
        U = {a[2]: np.array(m) for a, m in ex.map(job, [('U', r, j, 0, 0, None) for j, r in enumerate(recs)])}
        U = [U[j] for j in range(len(recs))]; urms = [(u[1] / 100, u[3] / 100) for u in U]
        C = [(0.0, 0)] + [(p, s) for p in (0.05, 0.10) for s in range(5)]
        jobs = [(p, r, j, n, s, urms[j]) for n, s in C for p in ('R', 'PEAK', 'PEAK_V', 'LP_V') for j, r in enumerate(recs)]
        res = {(a[0], a[2], a[3], a[4]): np.array(m) for a, m in ex.map(job, jobs, chunksize=2)}
    red = lambda p, n, s: np.array([(1 - res[(p, j, n, s)] / U[j]) * 100 for j in range(len(recs))])
    out = {}
    for n in (0.0, 0.05, 0.10):
        S = [0] if n == 0 else range(5)
        for p in ('PEAK', 'PEAK_V', 'LP_V'):
            v = [effect(recs, {p: red(p, n, s), 'R': red('R', n, s)}, p, 'R')['dS_evt'] for s in S]
            out[f'noise{n}_{p}-R'] = dict(mean=float(np.mean(v)), seeds=v)
            print(f'noise {n:.2f} {p:7s}-R {np.mean(v):+.2f}  [{min(v):+.2f}, {max(v):+.2f}]')
    print(f'{len(jobs)} runs {time.time() - t0:.0f}s')
    json.dump(out, open(os.path.join(rs.pr.HERE, 'result_dev_final.json'), 'w'), indent=1)
