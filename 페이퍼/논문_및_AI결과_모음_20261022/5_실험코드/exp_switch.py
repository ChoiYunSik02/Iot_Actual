# -*- coding: utf-8 -*-
"""시간 가변 전략의 상한 (2026-10-22): 장치가 평소값(F0, 0°)으로 대기하다가 트리거 + d초에 (f, θ)로 한 번 바꾸는 경우.
기존 Oracle(격자 49칸)은 t = 0부터 고정하는 전략의 상한일 뿐이다 (v2 결과에서 online이 Oracle을 넘는 기록이 있었음: PEER 3 등).
출력: d별(pre = 처음부터 고정, 이후 트리거 + d초) 최선 고정칸 평균 · 기록별 Oracle · 전체 (칸, d) Oracle 상한.
사용: python exp_switch.py [--kscale 1.0] [--d 0 1 2 3 5 8] [--workers 16] [--nrec 11]
결과: results/exp_switch_cos2.json
"""
import argparse, json, os, time
from multiprocessing import Pool
import numpy as np
import rstlcd_cos2 as R
import records
from gen_labels_v2 import DT, F_GRID, TH_GRID, F_RANGE

TRIG = 0.005                                     # train_ai와 같은 감지 문턱 (0.5 gal)
C_SCALE = 30.0


def test_records():
    return [(f'PEER {no} {st}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)


def trig_t(x, y):
    hit = np.flatnonzero(np.maximum(np.abs(x), np.abs(y)) > TRIG)
    return (int(hit[0]) if len(hit) else 0) * DT


def sim(job):
    key, x, y, kw = job
    return key, R.metrics(R.simulate(x, y, DT, c_scale=C_SCALE, f_range=F_RANGE, **kw))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kscale', type=float, default=1.0)
    ap.add_argument('--d', type=float, nargs='+', default=[0, 1, 2, 3, 5, 8])
    ap.add_argument('--nrec', type=int, default=11)
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    args = ap.parse_args()
    recs = test_records()[:args.nrec]; k = args.kscale; ds = ['pre'] + list(args.d); nF, nT = len(F_GRID), len(TH_GRID)
    jobs = []
    for r, (name, x, y) in enumerate(recs):
        tt = trig_t(x, y)
        jobs.append(((r, 'E0'), x, y, dict(case='none', k_scale=k)))
        for a, f in enumerate(F_GRID):
            for b, th in enumerate(TH_GRID):
                f, th = float(f), float(th)
                jobs.append(((r, 'pre', a, b), x, y, dict(case='rstlcd', k_scale=k, f0=f, theta0=th, cmd=(1e9, f, th))))
                for d in args.d:
                    jobs.append(((r, d, a, b), x, y, dict(case='rstlcd', k_scale=k, cmd=(tt + d, f, th))))
    t0 = time.time()
    with Pool(args.workers) as pool:
        res = dict(pool.map(sim, jobs, chunksize=4))
    print(f'{len(jobs)}회 {time.time() - t0:.0f}s')
    S = np.zeros((len(recs), len(ds), nF, nT))
    for r in range(len(recs)):
        b0 = res[(r, 'E0')]
        for i, d in enumerate(ds):
            for a in range(nF):
                for b in range(nT):
                    S[r, i, a, b] = np.mean(list(R.reduction(res[(r, d, a, b)], b0).values()))
    print(f'건물 강성 ×{k:g} · 기록 {len(recs)}개 · 6개 지표 평균 저감률 [%]')
    print('d(트리거 후 전환)   최선 고정칸 평균   기록별 Oracle 평균')
    for i, d in enumerate(ds):
        m = S[:, i].mean(0); a, b = np.unravel_index(m.argmax(), m.shape)
        print(f'{str(d):>10s}   {m.max():8.2f} (f{a} θ{np.rad2deg(TH_GRID[b]):.0f}°)   {S[:, i].reshape(len(recs), -1).max(1).mean():8.2f}')
    pre_fixed = S[:, 0].mean(0).max()
    orc_all = S.reshape(len(recs), -1).max(1)
    print(f'\n처음부터 고정의 최선 {pre_fixed:.2f} · 기록별 (칸, d) 전체 Oracle {orc_all.mean():.2f} → 시간 가변 여지 {orc_all.mean() - pre_fixed:.2f}%p')
    best_i = S.reshape(len(recs), len(ds), -1).max(2).argmax(1)
    print('기록별 최선 전환 시점:', {recs[r][0][:18]: str(ds[best_i[r]]) for r in range(len(recs))})
    os.makedirs('results', exist_ok=True)
    json.dump(dict(k_scale=k, ds=[str(d) for d in ds], records=[r_[0] for r_ in recs], S=S.tolist()),
              open('results/exp_switch_cos2.json', 'w', encoding='utf-8'), ensure_ascii=False)
