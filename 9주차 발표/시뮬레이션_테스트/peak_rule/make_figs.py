"""9주차 그림 4장 (PPT·논문용 PNG). 결과 JSON만 읽는다. 출력: 9주차 발표/그림/"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', '그림'); os.makedirs(OUT, exist_ok=True)
J = lambda f: json.load(open(os.path.join(HERE, f), encoding='utf-8'))
BLUE, ORANGE, AQUA, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984'
INK, INK2, SURF = '#0b0b0b', '#52514e', '#fcfcfb'
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 12,
                     'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                     'axes.grid': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.8})


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=200); plt.close(fig); print(name)


# 1. 독립 시험 효과량 (점 + 95% 구간)
t1 = J('result_test.json')['main']['variants']['PEAK']; t2 = J('result_test2.json')
rows = [('PEAK - R', (t1['dS_evt'], t1['dS_evt_ci95']), (t2['main']['PEAK-R']['dS_evt'], t2['main']['PEAK-R']['ci95'])),
        ('PEAK - 45° 고정', (t1['dS_vs_FIX45_evt'], t1['dS_vs_FIX45_ci95']), (t2['main']['PEAK-FIX45']['dS_evt'], t2['main']['PEAK-FIX45']['ci95'])),
        ('최종본 LP_V - R', None, (t2['main']['LP_V-R']['dS_evt'], t2['main']['LP_V-R']['ci95']))]
pool = t2['pooled_PEAK-FIX45']
fig, ax = plt.subplots(figsize=(8, 4.2))
for i, (lab, a, b) in enumerate(rows):
    y = len(rows) - 1 - i
    for v, dy, c, name in [(a, 0.15, BLUE, 'test (12사건)'), (b, -0.15, ORANGE, 'test2 (10사건)')]:
        if v is None: continue
        m, (lo, hi) = v
        ax.plot([lo, hi], [y + dy] * 2, color=c, lw=2, solid_capstyle='round')
        ax.plot(m, y + dy, 'o', ms=9, color=c, mec=SURF, mew=2, label=name if i == 0 else None)
        ax.text(hi + 0.08, y + dy, f'{m:+.2f}', va='center', color=INK, fontsize=11)
y = 1 - 0.45
ax.plot([pool['ci95'][0], pool['ci95'][1]], [y] * 2, color=GRAY, lw=2)
ax.plot(pool['dS_evt'], y, 'D', ms=8, color=GRAY, mec=SURF, mew=2, label='합친 22사건')
ax.text(pool['ci95'][1] + 0.08, y, f"{pool['dS_evt']:+.2f}", va='center', color=INK, fontsize=11)
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1]); ax.grid(axis='y', visible=False)
ax.set_xlabel('6지표 저감률 차이, 사건 평균 (%p) · 선 = 95% 구간'); ax.set_xlim(-0.6, 4.6)
ax.legend(loc='lower left', frameon=True, facecolor=SURF, edgecolor=SURF, framealpha=1, fontsize=10)
ax.set_title('독립 시험 두 세트에서 원문 규칙·45° 고정 대비 이득', loc='left', color=INK, fontsize=13)
save(fig, 'fig1_독립시험.png')

# 2. 잡음 강건성 (개발 62쌍)
d = J('result_dev_final.json'); nz = [0, 5, 10]
fig, ax = plt.subplots(figsize=(6.4, 4))
for key, c, lab in [('PEAK-R', GRAY, '피크 규칙 (v1)'), ('PEAK_V-R', BLUE, '피크 + 밸브 매 스텝'), ('LP_V-R', ORANGE, '최종본 LP_V')]:
    m = [d[f'noise{n}_{key}']['mean'] for n in (0.0, 0.05, 0.1)]
    lo = [min(d[f'noise{n}_{key}']['seeds']) for n in (0.0, 0.05, 0.1)]; hi = [max(d[f'noise{n}_{key}']['seeds']) for n in (0.0, 0.05, 0.1)]
    ax.fill_between(nz, lo, hi, color=c, alpha=0.15, lw=0)
    ax.plot(nz, m, '-o', color=c, lw=2, ms=8, mec=SURF, mew=2)
    ax.text(10.4, m[-1], f'{lab} {m[-1]:+.2f}', va='center', color=INK, fontsize=10)
ax.set_xticks(nz); ax.set_xlabel('변위 측정 잡음 (무제어 RMS 대비 %)'); ax.set_ylabel('원문 규칙 대비 이득 (%p)')
ax.set_ylim(0, 3.6); ax.set_xlim(-0.5, 17)
ax.set_title('센서 잡음: 최종본은 이득이 줄지 않음 (개발 62쌍, 시드 5개)', loc='left', color=INK, fontsize=12)
save(fig, 'fig2_잡음.png')

# 3. 지연 (개발 62쌍)
d = J('result_delay_final.json'); D = sorted(d, key=float); x = [float(k) for k in D]
m = [d[k]['dS_evt'] for k in D]; lo = [d[k]['ci95'][0] for k in D]; hi = [d[k]['ci95'][1] for k in D]
fig, ax = plt.subplots(figsize=(6.4, 4))
ax.fill_between(x, lo, hi, color=ORANGE, alpha=0.15, lw=0)
ax.plot(x, m, '-o', color=ORANGE, lw=2, ms=8, mec=SURF, mew=2)
for xi, mi in zip(x, m):
    if xi in (0.0, 0.1, 0.5, 1.0): ax.text(xi, mi + 0.18, f'{mi:+.2f}', ha='center', color=INK, fontsize=10)
ax.axhline(0, color=INK2, lw=1)
ax.set_xlabel('제어 지연 (s) · 회전판·밸브 지령 모두'); ax.set_ylabel('LP_V - 원문 규칙 (%p)'); ax.set_ylim(-0.2, 4.2)
ax.set_title('제어 지연: 1초에서도 +2%p 유지 (개발 62쌍, 띠 = 95% 구간)', loc='left', color=INK, fontsize=12)
save(fig, 'fig3_지연.png')

# 4. AI 상한 대비 실제
a1 = J('result_ai_select.json')['rows']['unrotated (원래 방향)']; a2 = J('result_ai_select2.json')['rows']['unrotated']
labs = ['AI 선택기 v1\n(4사건 학습)', 'AI 선택기 v2\n(19사건 학습)']
vals = {'정답 선택 (상한)': [a1['oracle'], a2['oracle']], '최선 고정값': [a1['const'], a2['const']], 'AI': [a1['AI'], a2['AI']]}
fig, ax = plt.subplots(figsize=(6.4, 4)); w = 0.26
for k, (name, v) in enumerate(vals.items()):
    c = [GRAY, BLUE, ORANGE][k]
    for i, vi in enumerate(v):
        xb = i + (k - 1) * w
        ax.bar(xb, vi, w - 0.03, color=c, label=name if i == 0 else None)
        ax.text(xb, vi + (0.05 if vi >= 0 else -0.15), f'{vi:+.2f}', ha='center', color=INK, fontsize=10)
ax.axhline(0, color=INK2, lw=1); ax.set_xticks([0, 1]); ax.set_xticklabels(labs); ax.grid(axis='x', visible=False)
ax.set_ylabel('피크 규칙 대비 (%p, 사건 평균)'); ax.set_ylim(-0.4, 2.2); ax.legend(frameon=False, fontsize=10)
ax.set_title('AI는 상한을 거의 얻지 못함 (사건 빼기 검증)', loc='left', color=INK, fontsize=12)
save(fig, 'fig4_AI상한.png')
