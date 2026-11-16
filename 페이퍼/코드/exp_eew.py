# -*- coding: utf-8 -*-
"""조기경보 리드타임 효과: 장치는 평소 바람용(건물 진동수 F0, 0°)으로 대기 → 언제 지진용 값으로 바꾸나?
명령 시점 = 트리거(건물 가속도 0.5 gal 도달) + d [s]. d < 0 = 조기경보로 미리 명령, d ≥ 0 = 건물에서 감지한 뒤.
지진용 값 = 고정값 (0.3204 Hz, 45°) (±5% 라벨 평균 점수 최대 칸). AI 없음.
비교: preset(처음부터 지진용) · stay(끝까지 바람용) · 원문 RS
사용: python exp_eew.py [--kscale 0.81 0.9025 1.0 1.1025 1.21] [--delays -5 -2.6 -1 0 0.5 1 2 3]
결과: results/exp_eew.json, .log
"""
import argparse, json, time
from multiprocessing import Pool
import numpy as np
import rstlcd as R
from train_ai import DT, sim, score, test_records, trigger_index, baselines

EQ = (0.3204, np.deg2rad(45.0))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kscale', type=float, nargs='+', default=[0.81, 0.9025, 1.0, 1.1025, 1.21])
    ap.add_argument('--delays', type=float, nargs='+', default=[-5, -2.6, -1, 0, 0.5, 1, 2, 3])
    ap.add_argument('--workers', type=int, default=15)
    args = ap.parse_args()
    recs = test_records(); out = []
    cols = ['E2', 'stay', *[f'd{d:g}' for d in args.delays], 'preset']
    for k in args.kscale:
        base = baselines(recs, k, args.workers)
        jobs = []
        for r, (name, x, y) in enumerate(recs):
            t_trig = trigger_index(x, y) * DT
            jobs.append(((r, 'stay'), x, y, dict(case='rstlcd', k_scale=k, cmd=(1e9, R.F0, 0.0))))
            jobs.append(((r, 'preset'), x, y, dict(case='rstlcd', k_scale=k, f0=EQ[0], theta0=EQ[1], cmd=(1e9, *EQ))))
            jobs += [((r, f'd{d:g}'), x, y, dict(case='rstlcd', k_scale=k, cmd=(max(0.0, t_trig + d), *EQ))) for d in args.delays]
        t0 = time.time()
        with Pool(args.workers) as pool:
            res = dict(pool.map(sim, jobs, chunksize=2))
        tab = {c: [] for c in cols}
        for r in range(len(recs)):
            b0 = base[(r, 'E0')]
            for c in cols:
                tab[c].append(score(R.reduction(base[(r, 'E2')] if c == 'E2' else res[(r, c)], b0)))
        m = {c: float(np.mean(v)) for c, v in tab.items()}
        out.append(dict(k_scale=k, mean=m, per_record=tab))
        print(f'강성 ×{k:g} ({R.F0 * np.sqrt(k):.4f} Hz, {len(jobs)}회 {time.time() - t0:.0f}s): ' +
              ' · '.join(f'{c} {m[c]:.2f}' for c in cols), flush=True)
    avg = {c: float(np.mean([o['mean'][c] for o in out])) for c in cols}
    print('평균: ' + ' · '.join(f'{c} {avg[c]:.2f}' for c in cols), flush=True)
    json.dump(dict(cols=cols, eq=[EQ[0], 45.0], standby=[R.F0, 0.0], rows=out, mean=avg),
              open('results/exp_eew.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
