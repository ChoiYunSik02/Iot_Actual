# -*- coding: utf-8 -*-
"""고정값 기준선: AI 대신 RS-TLCD를 하나의 (f, θ)로 늘 미리 맞춰 두면? (AI가 지진마다 다르게 예측해서 얻는 몫을 분리)
사용: python const_baseline.py  (train_ai.py를 먼저 돌려 results/ai_eval_baselines.json이 있어야 함)
"""
import json, numpy as np
from multiprocessing import Pool
import rstlcd as R
from train_ai import sim, test_records, score
if __name__ == '__main__':
    recs = test_records()
    base = {tuple(json.loads(k)): v for k, v in json.load(open('results/ai_eval_baselines.json', encoding='utf-8')).items()}
    # E4 격자 중 11쌍 평균이 가장 좋은 고정 칸 (사후에 고른 최선의 고정값 — AI에게 불리한 기준)
    red = lambda r, m: score(R.reduction(m, base[(r, 'E0')]))
    cells = {(a, b): np.mean([red(r, base[(r, 'E4', a, b)]) for r in range(len(recs))]) for a in range(7) for b in range(7)}
    best = max(cells, key=cells.get)
    print('최선 고정 칸', best, f'{cells[best]:.2f}', '· (0.3204 Hz, 45°) =', f'{cells[(0, 3)]:.2f}')
    for k in sorted(cells, key=cells.get, reverse=True)[:5]: print(k, f'{cells[k]:.2f}')
    # 같은 칸을 online(감지 + 3 s)으로
    from train_ai import trigger_index, DT, F_GRID, TH_GRID
    jobs = [((r,), x, y, dict(case='rstlcd', ai_f=float(F_GRID[best[0]]), ai_th=float(TH_GRID[best[1]]), t_set=trigger_index(x, y) * DT + 3.0)) for r, (n, x, y) in enumerate(recs)]
    with Pool(11) as p: res = dict(p.map(sim, jobs))
    print('최선 고정 칸 online T3:', f'{np.mean([red(r, res[(r,)]) for r in range(len(recs))]):.2f}')
