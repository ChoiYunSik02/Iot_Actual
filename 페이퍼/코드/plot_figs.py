# -*- coding: utf-8 -*-
"""교수님 요청 그림 3종 (`페이퍼/02_AI_학습_계획.md` 6절). train_ai.py 결과를 먼저 만들어야 함.

  (그림 글자는 영문 — 투고 저널 Smart Structures and Systems)
  그림 1 감쇠 진동수 : 건물 응답의 순간 진동수(웨이블릿) + 장치 진동수 (원문 RS · AI · Oracle)
  그림 2 값 변화     : 장치 진동수 · 개구율 κ · 회전각 θ 시간이력 (원문 그림 10 · 11 형식)
  그림 3 상쇄량      : 무제어 vs 제어 최상층 X 변위 + 11쌍 평균 저감률 막대
AI 예측값은 results/ai_eval.json의 leave-one-out 예측 (그 기록을 학습에서 뺀 모델)을 씀 → 누설 없음.
사용: python plot_figs.py [--rec 0] [--tobs 3] [--out figs]
"""
import argparse, json, os
from multiprocessing import Pool
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rstlcd as R
from train_ai import DT, C_SCALE, F_GRID, TH_GRID, ai_kw, test_records, trigger_index

# 색은 대상에 고정 (dataviz 기본 팔레트, 밝은 배경 검증 통과). 노랑 · 청록은 대비가 낮아 범례 + 선 모양을 같이 씀
COL = {'E0': '#8a8985', 'E1b': '#eda100', 'E2': '#2a78d6', 'online': '#eb6834', 'preset': '#eb6834', 'E4': '#1baf7a'}
LS = {'E0': '-', 'E1b': '-', 'E2': '-', 'online': '-', 'preset': ':', 'E4': '--'}
SHORT = {'E1b': 'Detuned\npassive', 'E2': 'RS-TLCD\n(wavelet)', 'online': 'AI\non-line', 'preset': 'AI\npreset', 'E4': 'Oracle'}
NAME = {'E0': 'Uncontrolled', 'E1b': 'Detuned passive', 'E2': 'RS-TLCD (wavelet)', 'online': 'AI on-line',
        'preset': 'AI preset', 'E4': 'Oracle'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e3e2de'
plt.rcParams.update({'font.family': ['Arial', 'Malgun Gothic'], 'axes.unicode_minus': False, 'font.size': 9,
                     'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.spines.top': False,
                     'axes.spines.right': False, 'lines.linewidth': 1.5, 'legend.frameon': False, 'savefig.dpi': 200})


def run(job):
    key, x, y, kw = job
    return key, R.simulate(x, y, DT, c_scale=C_SCALE, **ai_kw(kw))


def inst_freq(u, step=20):
    """최상층 변위의 순간 진동수 (원문과 같은 과거 데이터 웨이블릿)."""
    wid = R.WaveletID(DT); idx = np.arange(step, len(u), step)
    return idx * DT, np.array([wid(u[:i]) for i in idx])


def mark_times(ax, t_trig, t_set):
    for t, s, dx, ha in ((t_trig, 'trigger', -3, 'right'), (t_set, 'command', 3, 'left')):   # 두 선이 가까워 글자를 양쪽으로
        ax.axvline(t, color=MUTED, lw=0.8, ls=(0, (2, 2)))
        ax.annotate(s, (t, 1), xycoords=('data', 'axes fraction'), xytext=(dx, -10), textcoords='offset points',
                    ha=ha, color=MUTED, fontsize=8)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rec', type=int, default=0, help='실제 기록 번호 (train_ai.test_records 순서)')
    ap.add_argument('--tobs', type=float, default=3.0)
    ap.add_argument('--eval', default='results/ai_eval.json')
    ap.add_argument('--base', default='results/ai_eval_baselines.json')
    ap.add_argument('--out', default='figs')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    ev = next(e for e in json.load(open(args.eval, encoding='utf-8')) if e['tobs'] == args.tobs)
    base = {tuple(json.loads(k)): v for k, v in json.load(open(args.base, encoding='utf-8')).items()}
    name, x, y = test_records()[args.rec]
    _, f_ai, th_ai_deg = ev['preds'][args.rec]
    th_ai = np.deg2rad(th_ai_deg)
    t_trig = trigger_index(x, y) * DT; t_set = t_trig + args.tobs

    # Oracle 칸: 이 기록의 49칸 중 6개 지표 평균 저감률 최대
    b0 = base[(args.rec, 'E0')]
    sc = lambda m: np.mean(list(R.reduction(m, b0).values()))
    ga, gb = max(((a, b) for a in range(len(F_GRID)) for b in range(len(TH_GRID))),
                 key=lambda ab: sc(base[(args.rec, 'E4', *ab)]))
    f_or, th_or = float(F_GRID[ga]), float(TH_GRID[gb])

    jobs = [('E0', x, y, dict(case='none')), ('E2', x, y, dict(case='rstlcd')),
            ('online', x, y, dict(case='rstlcd', ai_f=f_ai, ai_th=th_ai, t_set=t_set)),
            ('preset', x, y, dict(case='rstlcd', ai_f=f_ai, ai_th=th_ai)),
            ('E4', x, y, dict(case='rstlcd', ai_f=f_or, ai_th=th_or))]
    with Pool(len(jobs)) as pool:
        o = dict(pool.map(run, jobs))
    t = o['E0']['t']
    for k in o:                                          # 0번 칸은 기록 전이라 0 → 첫 값으로 채움
        for v in ('f_dev', 'kappa', 'theta'):
            o[k][v][0] = o[k][v][1]
    title = f'{name}, $T_{{obs}}$ = {args.tobs:g} s'

    # ── 그림 1: 감쇠 진동수 ──
    fig, ax = plt.subplots(figsize=(7, 3.4))
    tb, fb = inst_freq(o['E0']['ux'])
    ax.axhspan(*R.F_RANGE, color=GRID, alpha=0.6, lw=0)
    ax.annotate('damper tuning range ±5%', (t[-1], R.F_RANGE[1]), xytext=(-4, 3), textcoords='offset points',
                ha='right', color=MUTED, fontsize=8)
    ax.plot(tb, fb, color=COL['E0'], lw=1.0, label='Building instantaneous frequency (uncontrolled)')
    ax.axhline(R.F0, color=MUTED, lw=0.8, ls=(0, (1, 2)))
    for k in ('E2', 'online', 'E4'):
        ax.plot(t, o[k]['f_dev'], color=COL[k], ls=LS[k], label=NAME[k] + ': damper frequency')
    mark_times(ax, t_trig, t_set)
    ax.set(xlabel='Time (s)', ylabel='Frequency (Hz)', ylim=(0.25, 0.45), title=title)
    ax.legend(loc='lower right', fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(args.out, f'fig1_freq_rec{args.rec}.png')); plt.close(fig)

    # ── 그림 2: 값 변화 (진동수 · κ · θ, 같은 x축 세 칸) ──
    fig, axs = plt.subplots(3, 1, figsize=(7, 5.6), sharex=True)
    for k in ('E2', 'online', 'E4'):
        axs[0].plot(t, o[k]['f_dev'], color=COL[k], ls=LS[k], label=NAME[k])
        axs[1].step(t, o[k]['kappa'], where='post', color=COL[k], ls=LS[k], lw=1.0)
        axs[2].plot(t, np.rad2deg(o[k]['theta']), color=COL[k], ls=LS[k])
    axs[0].set(ylabel='Damper freq. (Hz)', ylim=(R.F_RANGE[0] - 0.003, R.F_RANGE[1] + 0.003))
    axs[1].set(ylabel='Orifice opening κ', ylim=(0, 0.9))
    axs[2].set(ylabel='Rotation θ (°)', ylim=(-5, 95), yticks=[0, 30, 60, 90], xlabel='Time (s)')
    for a in axs: mark_times(a, t_trig, t_set)
    axs[0].legend(loc='lower left', bbox_to_anchor=(0, 1.0), fontsize=8, ncol=3)
    fig.suptitle(title)
    fig.align_ylabels(axs); fig.tight_layout()
    fig.savefig(os.path.join(args.out, f'fig2_values_rec{args.rec}.png')); plt.close(fig)

    # ── 그림 3: 상쇄량 ──
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4), gridspec_kw={'width_ratios': [1.8, 1]})
    for k, lw in (('E0', 1.0), ('E2', 1.0), ('online', 1.2)):
        a1.plot(t, o[k]['ux'] * 100, color=COL[k], lw=lw, label=NAME[k])
    a1.set(xlabel='Time (s)', ylabel='Top-floor X displacement (cm)', title=f'(a) {name}')
    a1.legend(loc='upper right', fontsize=8)
    m = ev['mean']; ks = [k for k in ('E1b', 'E2', 'online', 'preset', 'E4') if k in m]
    bars = a2.bar(range(len(ks)), [m[k] for k in ks], color=[COL[k] for k in ks], width=0.6)
    if 'preset' in ks:
        bars[ks.index('preset')].set_hatch('///')        # 같은 AI 색이라 빗금으로 구분
    for i, k in enumerate(ks):
        a2.annotate(f'{m[k]:.1f}', (i, m[k]), xytext=(0, 2), textcoords='offset points', ha='center', fontsize=8, color=INK)
    a2.set_xticks(range(len(ks)), [SHORT[k] for k in ks], fontsize=8)
    a2.set(ylabel='Mean reduction of 6 indices (%)', title=f'(b) Mean of 11 records, $T_{{obs}}$ = {args.tobs:g} s')
    a2.grid(axis='x', visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(args.out, f'fig3_cancel_rec{args.rec}.png')); plt.close(fig)

    red = {k: sc(R.metrics(o[k])) for k in o if k != 'E0'}
    print(f'{name}: AI f={f_ai:.4f} θ={th_ai_deg:.0f}° · Oracle f={f_or:.4f} θ={np.rad2deg(th_or):.0f}° · 감지 {t_trig:.2f} s')
    print('이 기록 저감률 [%]: ' + ', '.join(f'{NAME[k]} {v:.2f}' for k, v in red.items()))
    print(f'저장: {args.out}/fig1_freq_rec{args.rec}.png, fig2_values_rec{args.rec}.png, fig3_cancel_rec{args.rec}.png')
