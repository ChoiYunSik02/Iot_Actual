# -*- coding: utf-8 -*-
"""범위 확대 사전 점검: 장치 진동수 조절 범위를 ±5% → ±10 · 20%로 넓히면 AI가 노릴 여지가 생기나?
여지 = Oracle(기록마다 정답 칸) − 최선 고정값(11쌍 평균이 가장 좋은 한 칸). ±5%에서는 0.7~1.3%p뿐이었음.
라벨을 다시 만들기(약 2.5시간) 전에 실제 11쌍으로만 Oracle 격자를 돌려 확인.
사용: python exp_range.py [--ranges 0.05 0.1 0.2] [--kscale 0.81 1.0 1.21]
결과: results/exp_range.json, .log
"""
import argparse, json, time
from multiprocessing import Pool
import numpy as np
import rstlcd as R
from train_ai import sim, score, test_records

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ranges', type=float, nargs='+', default=[0.05, 0.1, 0.2])
    ap.add_argument('--kscale', type=float, nargs='+', default=[0.81, 1.0, 1.21])
    ap.add_argument('--df', type=float, default=0.0057, help='진동수 격자 간격 [Hz] (±5%에서 7칸과 같음)')
    args = ap.parse_args()
    recs = test_records(); TH = np.deg2rad(np.linspace(0, 90, 7)); out = []
    for p in args.ranges:
        fr = (R.F0 * (1 - p), R.F0 * (1 + p)); F = np.linspace(*fr, int(round((fr[1] - fr[0]) / args.df)) + 1)
        for k in args.kscale:
            jobs = []
            for r, (name, x, y) in enumerate(recs):
                kw = dict(k_scale=k, f_range=fr)
                jobs += [((r, 'E0'), x, y, dict(case='none', **kw)), ((r, 'E2'), x, y, dict(case='rstlcd', **kw))]
                jobs += [((r, a, b), x, y, dict(case='rstlcd', ai_f=float(f), ai_th=float(th), **kw))
                         for a, f in enumerate(F) for b, th in enumerate(TH)]
            t0 = time.time()
            with Pool() as pool:
                res = dict(pool.map(sim, jobs, chunksize=2))
            red = lambda r, key: score(R.reduction(res[(r,) + key if isinstance(key, tuple) else (r, key)], res[(r, 'E0')]))
            cells = [(a, b) for a in range(len(F)) for b in range(len(TH))]
            grid = np.array([[red(r, c) for c in cells] for r in range(len(recs))])      # 기록 × 칸
            best_fixed = int(np.argmax(grid.mean(0)))
            row = dict(range=p, k_scale=k, n_f=len(F), E2=float(np.mean([red(r, 'E2') for r in range(len(recs))])),
                       fixed=float(grid.mean(0)[best_fixed]),
                       fixed_cell=[float(F[cells[best_fixed][0]]), float(np.rad2deg(TH[cells[best_fixed][1]]))],
                       oracle=float(grid.max(1).mean()),
                       oracle_f=[float(F[cells[i][0]]) for i in grid.argmax(1)])
            row['headroom'] = row['oracle'] - row['fixed']
            out.append(row)
            print(f'±{p * 100:.0f}% · 강성 ×{k:g} ({len(jobs)}회 {time.time() - t0:.0f}s): 원문 RS {row["E2"]:.2f} · '
                  f'최선 고정 {row["fixed"]:.2f} ({row["fixed_cell"][0]:.4f} Hz, {row["fixed_cell"][1]:.0f}°) · '
                  f'Oracle {row["oracle"]:.2f} · 여지 {row["headroom"]:.2f}%p · '
                  f'Oracle f 분포 {np.round(sorted(row["oracle_f"]), 3).tolist()}', flush=True)
    json.dump(out, open('results/exp_range.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
