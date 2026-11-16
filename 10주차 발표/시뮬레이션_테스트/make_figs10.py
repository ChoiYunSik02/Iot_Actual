"""10주차 발표 그림 5장 (PPT용 PNG). 저장된 결과 JSON만 읽고 시뮬레이션은 돌리지 않는다. 9주차 make_figs2.py와 같은 양식.
출력: 10주차 발표/그림/fig1~fig5
"""
import os, json, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '그림')
B2 = os.path.join(HERE, 'results_b2')
BLUE, ORANGE, GRAY = '#2a78d6', '#eb6834', '#8a8984'
INK, INK2, SURF = '#0b0b0b', '#52514e', '#fcfcfb'
J = lambda *p: json.load(open(os.path.join(HERE, *p), encoding='utf-8'))
NAME = {'San': 'San Fernando', 'Imperial': 'Imperial Valley', 'Loma': 'Loma Prieta', 'Cape': 'Cape Mendocino', 'Hector': 'Hector Mine',
        'Superstition': 'Superstition H.', 'Northridge-01': 'Northridge'}
label = lambda e: NAME.get(e, e)


def style():
    plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 12,
                         'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                         'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                         'axes.grid': True, 'axes.axisbelow': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.8})


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=200); plt.close(fig); print(name)


def ci_rows(ax, rows, colors):
    """rows: [(이름, 평균, [하한, 상한])]. 점 + 95% 구간, 위에서 아래로."""
    for i, ((nm, m, ci), c) in enumerate(zip(rows, colors)):
        y = len(rows) - 1 - i
        ax.plot(ci, [y, y], color=c, lw=2.5, solid_capstyle='round')
        ax.plot(m, y, 'o', color=c, ms=9, mec=SURF, mew=2)
        ax.text(ci[1] + 0.06, y, f'{m:+.2f}  [{ci[0]:+.2f}, {ci[1]:+.2f}]', va='center', fontsize=10.5, color=INK)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1]); ax.grid(axis='y', visible=False)
    ax.axvline(0, color=INK2, lw=1)


def fig1_upper():
    """1절 A0b: 1 s 뒤 지진 파형을 완벽히 알 때의 규칙 제어 (LP_V 대비)."""
    S = J('results_a0b', 'result_a0b.json')['summary']
    ms = [('DIR_FUT', '회전판 방향 = 1 s 뒤 지반'), ('DIR_PAST', '회전판 방향 = 지금 지반'), ('VUP_FUT', '밸브: 1 s 뒤 세지면 감쇠↑'),
          ('VUP_PAST', '밸브: 지난 1 s 세기 변화'), ('BOTH_FUT', '둘 다 (미래)')]
    fig, ax = plt.subplots(figsize=(9, 4.2)); off = {'0.0': 0.22, '0.5': 0.0, '1.0': -0.22}
    for d, c in zip(('0.0', '0.5', '1.0'), (BLUE, ORANGE, GRAY)):
        for i, (k, _) in enumerate(ms):
            y = len(ms) - 1 - i + off[d]; r = S[d][k]
            ax.plot(r['ci95'], [y, y], color=c, lw=2, alpha=0.8); ax.plot(r['dS_evt'], y, 'o', color=c, ms=7, mec=SURF, mew=1.5, label=f'지령 지연 {d} s' if i == 0 else None)
    ax.set_yticks(range(len(ms))); ax.set_yticklabels([m[1] for m in ms][::-1]); ax.grid(axis='y', visible=False)
    ax.axvline(0, color=INK2, lw=1); ax.set_xlabel('LP_V 대비 사건 평균 %p (점) · 95% 구간 (선)')
    ax.legend(frameon=False, fontsize=10.5, loc='center left', bbox_to_anchor=(0.02, 0.4)); ax.set_title('1 s 뒤를 완벽히 알아도 LP_V를 넘지 못함 (62쌍 19사건)', loc='left', color=INK, fontsize=13)
    save(fig, 'fig1_미래정보_상한.png')


def fig2_seeds():
    """9절: 사건별 3시드 평균 막대 + 시드 범위."""
    R = J('results_b2', 'b3lin', 'result.json'); pe = {m: R[m]['per_event'] for m in ('B3_13', 'B3_13_s1', 'B3_13_s2', 'B3_13_mean3')}
    ev = sorted(pe['B3_13_mean3'], key=lambda e: -pe['B3_13_mean3'][e]); x = np.arange(len(ev))
    m3 = np.array([pe['B3_13_mean3'][e] for e in ev]); sd = np.array([[pe[m][e] for m in ('B3_13', 'B3_13_s1', 'B3_13_s2')] for e in ev])
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(x, m3, 0.7, color=[BLUE if v > 0 else ORANGE for v in m3])
    ax.vlines(x, sd.min(1), sd.max(1), color=INK2, lw=1.2); ax.plot(x, sd.min(1), '_', color=INK2, ms=6); ax.plot(x, sd.max(1), '_', color=INK2, ms=6)
    ax.set_ylim(-1.5, 2.5)
    i0 = ev.index('San'); ax.annotate(f'San Fernando (1쌍)\n평균 {m3[i0]:+.1f}, 시드 {sd[i0].min():+.1f}~{sd[i0].max():+.1f}', (x[i0], 2.4), (x[i0] + 1.2, 1.6),
                                      fontsize=10, color=INK, arrowprops=dict(arrowstyle='->', color=INK2))
    ax.axhline(0, color=INK2, lw=1); ax.set_xticks(x); ax.set_xticklabels([label(e) for e in ev], rotation=40, ha='right', fontsize=10.5)
    ax.grid(axis='x', visible=False); ax.set_ylabel('LP_V 대비 %p')
    ax.set_title('AI 밸브(B3_13) 사건별: 막대 = 3시드 평균, 선 = 시드 최소~최대 (나아진 13 / 나빠진 6)', loc='left', color=INK, fontsize=12.5)
    save(fig, 'fig2_AI밸브_3시드_사건별.png')


def val_rel(fp):
    v = json.load(open(fp, encoding='utf-8'))['info']['val_curve']; return (np.array(v) / v[0] - 1) * 100


def fig3_val():
    """9·10절: 고정 검증 손실 (처음 대비 상대 변화)."""
    nn_ = [val_rel(f) for f in glob.glob(os.path.join(B2, 'b3s', 'fold_13_s*_*.json'))]
    ln = [val_rel(f) for f in glob.glob(os.path.join(B2, 'b3lin', 'fold_13_*.json'))]
    u = list(range(0, 1000, 50)) + [1000]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for arr, c, nm in ((nn_, BLUE, '신경망 (시드 1·2, 38겹)'), (ln, ORANGE, '선형 (시드 0, 19겹)')):
        for a in arr: ax.plot(u, a, color=c, lw=0.6, alpha=0.18)
        m = np.mean(arr, 0); ax.plot(u, m, color=c, lw=2.5, label=nm)
        ax.text(1015, m[-1], f'{m[-1]:+.2f}%\n({sum(a[-1] < 0 for a in arr)}/{len(arr)}겹 감소)', va='center', fontsize=10, color=INK)
    ax.axhline(0, color=INK2, lw=1); ax.set_xlim(0, 1180); ax.set_xlabel('갱신 횟수'); ax.set_ylabel('고정 검증 손실, 처음 대비 %')
    ax.legend(frameon=False, fontsize=10.5, loc='lower left'); ax.set_title('고정 검증 구간 손실: 신경망은 내려가고, 선형은 거의 그대로', loc='left', color=INK, fontsize=13)
    save(fig, 'fig3_고정검증손실.png')


def fig4_ground():
    """8절: 지진 세기 예측 입력 기여 B3_15 - B3_13 (시드 0, 사건별)."""
    a = J('results_b2', 'b3l15', 'result.json')['B3_15']['per_event']; b = J('results_b2', 'b3lin', 'result.json')['B3_13']['per_event']
    ev = sorted(a, key=lambda e: -(a[e] - b[e])); d = np.array([a[e] - b[e] for e in ev]); x = np.arange(len(ev))
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(x, np.clip(d, -1.2, None), 0.7, color=[BLUE if v > 0 else ORANGE for v in d])
    i0 = ev.index('San'); ax.text(x[i0], -1.25, f'{d[i0]:+.1f}', ha='center', va='top', fontsize=10, color=INK)
    ax.axhline(0, color=INK2, lw=1); ax.set_ylim(-1.6, 0.6); ax.set_xticks(x); ax.set_xticklabels([label(e) for e in ev], rotation=40, ha='right', fontsize=10.5)
    ax.grid(axis='x', visible=False); ax.set_ylabel('입력 15 - 입력 13 (%p)')
    ax.set_title('지진 세기 예측 입력의 기여: -0.15 [-0.52, +0.08], 나아진 9 / 나빠진 10사건, San 빼면 +0.02', loc='left', color=INK, fontsize=12.5)
    save(fig, 'fig4_지진입력_기여.png')


def fig5_linear():
    """10절: 선형 정책 대조."""
    R = J('results_b2', 'b3lin', 'result.json'); D = R['nn_minus_lin']
    rows = [('선형 (시드 0)', R['B3LIN_13']), ('신경망 시드 0', R['B3_13']), ('신경망 시드 1', R['B3_13_s1']), ('신경망 시드 2', R['B3_13_s2']), ('신경망 3시드 평균', R['B3_13_mean3'])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ci_rows(a1, [(n, r['dS_evt'], r['ci95']) for n, r in rows], [ORANGE, BLUE, BLUE, BLUE, BLUE]); a1.set_xlim(-0.3, 2.6)
    a1.set_xlabel('LP_V 대비 사건 평균 %p'); a1.set_title('같은 학습법, 정책만 다름', loc='left', color=INK, fontsize=12.5)
    ci_rows(a2, [('시드 0 - 선형 (판정)', D['B3_13']['mean'], D['B3_13']['ci95']), ('3시드 평균 - 선형 (참고)', D['B3_13_mean3']['mean'], D['B3_13_mean3']['ci95'])], [INK2, GRAY])
    a2.set_xlim(-0.3, 2.6); a2.set_xlabel('신경망 - 선형, 사건 평균 %p'); a2.set_title('차이: 구간이 0을 포함 (판정)', loc='left', color=INK, fontsize=12.5)
    save(fig, 'fig5_선형대조.png')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True); style(); fig1_upper(); fig2_seeds(); fig3_val(); fig4_ground(); fig5_linear()
