# -*- coding: utf-8 -*-
"""그림 4 — 관측 시간 T_obs(= 진원 거리)별 성능. train_ai.py 결과만 읽음 (시뮬레이션 없음).
  (a) 6개 지표 평균 저감률: AI preset · online vs 원문 RS · 고정값 (0.3204 Hz, 45°) · Oracle
  (b) 진동수 예측 오차 [mHz]
사용: python plot_fig4.py [--out figs]
"""
import argparse, json, os
import numpy as np
import matplotlib.pyplot as plt
import rstlcd as R
from train_ai import F_GRID, TH_GRID, FIXED, score
from plot_figs import COL, NAME, INK, MUTED   # 같은 색 · 이름 · 글꼴 설정

COL = {**COL, 'fixed': '#e87ba4'}
NAME = {**NAME, 'fixed': 'Fixed preset (0.3204 Hz, 45°)'}



if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--eval', default='results/ai_eval.json')
    ap.add_argument('--base', default='results/ai_eval_baselines.json')
    ap.add_argument('--out', default='figs')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    ev = sorted(json.load(open(args.eval, encoding='utf-8')), key=lambda e: e['tobs'])
    base = {tuple(json.loads(k)): v for k, v in json.load(open(args.base, encoding='utf-8')).items()}
    nrec = len(ev[0]['preds'])
    a = int(np.argmin(np.abs(F_GRID - FIXED[0]))); b = int(np.argmin(np.abs(np.rad2deg(TH_GRID) - FIXED[1])))
    fixed = np.mean([score(R.reduction(base[(r, 'E4', a, b)], base[(r, 'E0')])) for r in range(nrec)])

    t = [e['tobs'] for e in ev]
    ref = {'E2': ev[0]['mean']['E2'], 'fixed': fixed, 'E4': ev[0]['mean']['E4']}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4), gridspec_kw={'width_ratios': [1.6, 1]})

    # (a) 기준선은 T_obs와 무관 → 가로선, AI는 점 + 선
    for k, ls in (('E2', '-'), ('fixed', (0, (4, 2))), ('E4', '--')):
        a1.axhline(ref[k], color=COL[k], ls=ls, lw=1.2)
        a1.annotate(f'{NAME[k]} {ref[k]:.2f}', (1, ref[k]), xycoords=('axes fraction', 'data'), xytext=(-2, 3),
                    textcoords='offset points', ha='right', fontsize=8, color=INK)
    for k, mk in (('preset', 'o'), ('online', 's')):
        y = [e['mean'][k] for e in ev]
        a1.plot(t, y, color=COL[k], marker=mk, ms=6, mfc=COL[k] if k == 'online' else 'white', label=NAME[k])
    a1.set(xlabel='Observation time $T_{obs}$ (s)', ylabel='Mean reduction of 6 indices (%)', xticks=t,
           title='(a) Response reduction, mean of 11 records')
    a1.legend(loc='lower right', bbox_to_anchor=(1, 0.12), fontsize=8)

    # (b) 진동수 오차
    err = [e['f_err_mean_hz'] * 1000 for e in ev]
    a2.plot(t, err, color=COL['online'], marker='o', ms=6)
    for x, y in zip(t, err):
        a2.annotate(f'{y:.1f}', (x, y), xytext=(0, 5), textcoords='offset points', ha='center', fontsize=8, color=INK)
    a2.set(xlabel='Observation time $T_{obs}$ (s)', ylabel='Frequency error (mHz)', xticks=t, ylim=(0, max(err) * 1.25),
           title='(b) |$f_{AI}$ − $f_{Oracle}$|')
    fig.tight_layout()
    path = os.path.join(args.out, 'fig4_tobs.png'); fig.savefig(path); plt.close(fig)
    print(f'고정값 {FIXED} 평균 {fixed:.2f}% · 저장: {path}')
