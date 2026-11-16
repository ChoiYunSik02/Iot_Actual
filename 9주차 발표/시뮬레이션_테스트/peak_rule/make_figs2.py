"""9주차 추가 그림 4장 (PPT용 PNG). test2는 저장된 결과 JSON만 읽고 다시 돌리지 않는다.
시간 응답 그림은 개발 33쌍(원문 15 + dev 18)에서 LP_V − R 이득이 중앙값인 기록을 골라, 잘 나온 기록만 고르지 않게 한다.
출력: 9주차 발표/그림/fig5~fig8, 고른 기록 정보: result_fig_timehist.json
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
import run_set as rs
from run_set import Plant, simulate, metrics, load, uncontrolled
from run_test2 import POL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', '그림')
BLUE, ORANGE, GRAY = '#2a78d6', '#eb6834', '#8a8984'
INK, INK2, SURF = '#0b0b0b', '#52514e', '#fcfcfb'
J = lambda f: json.load(open(os.path.join(HERE, f), encoding='utf-8'))


def style():
    plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 12,
                         'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                         'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
                         'axes.grid': True, 'axes.axisbelow': True, 'grid.color': '#e6e5e0', 'grid.linewidth': 0.8})


NAME = {'San': 'San Fernando', 'Imperial': 'Imperial Valley', 'Loma': 'Loma Prieta', 'Cape': 'Cape Mendocino', 'Hector': 'Hector Mine',
        'N.': 'N. Palm Springs', 'Big': 'Big Bear', 'Morgan': 'Morgan Hill', 'Superstition': 'Superstition H.'}


def label(e):
    return NAME.get(e, e.replace('-01', '').replace('-02', ''))


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, name), dpi=200); plt.close(fig); print(name)


def gain(a):
    j, rec = a; ax, ay, dt = load(rec); U = uncontrolled(ax, ay, dt)
    m = {p: metrics(simulate(Plant(dt), ax, ay, POL[p](dt))[0]) for p in ('R', 'LP_V')}
    return j, float(((m['R'] - m['LP_V']) / U).mean() * 100)


def uncontrolled_roof(ax, ay, dt):
    """무제어 옥상 시계열. run_set.uncontrolled와 같은 행렬로 응답을 뽑는다."""
    from scipy.linalg import expm
    from run_set import build, N
    M, K = build('lit'); n = 3 * N
    w = np.sqrt(np.sort(np.linalg.eigvals(np.linalg.solve(M, K)).real)[:2])
    a0, a1 = np.linalg.solve([[1 / (2 * w[0]), w[0] / 2], [1 / (2 * w[1]), w[1] / 2]], [0.02, 0.02])
    C = a0 * M + a1 * K; Mi = np.linalg.inv(M)
    A = np.block([[np.zeros((n, n)), np.eye(n)], [-Mi @ K, -Mi @ C]])
    E = np.zeros((n, 2)); E[:N, 0] = 1; E[N:2 * N, 1] = 1
    B = np.vstack([np.zeros((n, 2)), -E])
    Z = np.zeros((2 * n + 2, 2 * n + 2)); Z[:2 * n, :2 * n] = A * dt; Z[:2 * n, 2 * n:] = B * dt; Ez = expm(Z)
    Ad, Bd = Ez[:2 * n, :2 * n], Ez[:2 * n, 2 * n:]
    x = np.zeros(2 * n); y = np.empty((len(ax), 2))
    for k in range(len(ax)):
        y[k] = x[[N - 1, 2 * N - 1]]; x = Ad @ x + Bd @ np.r_[ax[k], ay[k]]
    return y


def fig_timehist():
    recs = rs.record_list('paper15') + rs.record_list('dev'); assert len(recs) == 33
    with ProcessPoolExecutor(max_workers=12) as ex:
        g = dict(ex.map(gain, list(enumerate(recs))))
    order = sorted(g, key=g.get); j = order[len(order) // 2]; rec = recs[j]
    ax, ay, dt = load(rec); p = Plant(dt); t = np.arange(len(ax)) * dt
    yU = uncontrolled_roof(ax, ay, dt); assert abs(100 * np.abs(yU[:, 0]).max() / uncontrolled(ax, ay, dt)[0] - 1) < 1e-6
    yR, decR, _ = simulate(p, ax, ay, POL['R'](dt)); yL, dec, stL = simulate(p, ax, ay, POL['LP_V'](dt))
    # R의 기록(st)은 1 s 간격이라 실제 회전을 못 보여 준다. 지령(2.6 s)과 30°/s 제한으로 매 스텝 각도를 다시 계산한다.
    tgt = {d[1]: d[4] for d in decR if d[0] == 1}; thR = np.zeros(len(ax)); a_, g_ = 0.0, 0.0
    for k in range(len(ax)):
        g_ = tgt.get(k, g_); a_ += float(np.clip(g_ - a_, -30 * dt, 30 * dt)); thR[k] = a_
    c = int(np.abs(yU).max(0).argmax()); name = 'XY'[c]
    tmax = min(t[-1], 60.0); peaks = [(d[2], d[4]) for d in dec if d[0] == 3 and d[2] <= tmax]
    fig, (a, b) = plt.subplots(2, 1, figsize=(12.1, 3.75), sharex=True, gridspec_kw=dict(height_ratios=[1.5, 1]))
    a.plot(t, yU[:, c] * 100, color=GRAY, lw=1.2, label='무제어')
    a.plot(t, yR[:, c] * 100, color=BLUE, lw=1.4, label='원문 규칙 R')
    a.plot(t, yL[:, c] * 100, color=ORANGE, lw=1.6, label='최종본 LP_V')
    a.set_ylabel(f'옥상 {name} 변위 (cm)', fontsize=11); a.legend(loc='upper right', ncol=3, frameon=False, fontsize=10.5)
    sL = np.array(stL)
    b.plot(t, thR, color=BLUE, lw=1.6, label='R')
    b.plot(sL[:, 1], sL[:, 2], color=ORANGE, lw=1.6, label='LP_V')
    b.plot([q[0] for q in peaks], [q[1] for q in peaks], 'o', ms=6, color=INK, mec=SURF, mew=1, label='피크 판정 (목표각)', zorder=5)
    b.axhline(45, color=INK2, lw=0.8, ls=':'); b.set_ylabel('회전판 각도 (°)', fontsize=11); b.set_xlabel('시간 (s)', fontsize=11)
    b.set_ylim(0, 90); b.set_yticks([0, 45, 90]); b.set_xlim(0, tmax); b.legend(loc='upper right', ncol=3, frameon=False, fontsize=10.5)
    save(fig, 'fig5_시간응답.png')
    json.dump(dict(id=rec[0], event=rec[1], gain=g[j], n=len(recs), dir=name, n_peaks=len([d for d in dec if d[0] == 3])),
              open(os.path.join(HERE, 'result_fig_timehist.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(rec[0], rec[1], round(g[j], 2), 'range', round(min(g.values()), 2), round(max(g.values()), 2))


def fig_ai_valve():
    o = J('result_valve_oracle.json')['per_event']; nn = J('result_valve_nn.json')['per_event']; assert set(o) == set(nn) and len(o) == 19
    # 표기가 다른 사건 이름은 valve_oracle의 첫 단어 규칙을 따른다
    ev = sorted(o, key=lambda e: -o[e]); x = np.arange(len(ev)); w = 0.4
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.bar(x - w / 2, [o[e] for e in ev], w - 0.04, color=GRAY, label='밸브 상한 (지진 전체를 미리 앎)')
    ax.bar(x + w / 2, [nn[e] for e in ev], w - 0.04, color=ORANGE, label='신경망 NN_V')
    ax.axhline(0, color=INK2, lw=1); ax.set_xticks(x); ax.set_xticklabels([label(e) for e in ev], rotation=55, ha='right', fontsize=9.5)
    ax.grid(axis='x', visible=False); ax.set_ylabel('LP_V 대비 (%p)', fontsize=11); ax.legend(frameon=False, fontsize=10.5, loc='upper right')
    save(fig, 'fig6_AI밸브_사건별.png')


def fig_test2_events():
    m = J('result_test2.json')['main']; a, b = m['PEAK-R']['per_event'], m['LP_V-R']['per_event']; assert set(a) == set(b) and len(a) == 10
    ev = sorted(a, key=lambda e: -b[e]); x = np.arange(len(ev)); w = 0.4
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - w / 2, [a[e] for e in ev], w - 0.04, color=GRAY, label='PEAK - R')
    ax.bar(x + w / 2, [b[e] for e in ev], w - 0.04, color=ORANGE, label='최종본 LP_V - R')
    ax.axhline(0, color=INK2, lw=1); ax.set_xticks(x); ax.set_xticklabels([label(e) for e in ev], rotation=35, ha='right', fontsize=11.5)
    ax.grid(axis='x', visible=False); ax.set_ylabel('R 대비 이득 (%p, 사건 평균)'); ax.legend(frameon=False, fontsize=12, loc='upper right')
    ax.set_title('test2 사건별 (10사건)', loc='left', color=INK, fontsize=13)
    save(fig, 'fig7_test2_사건별.png')


def fig_noise():
    v = J('result_v2.json'); nz = [0, 1, 5, 10]; ns = ['0.0', '0.01', '0.05', '0.1']
    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    for key, c, lab in [('PEAK', GRAY, 'v1 (필터 없음)'), ('LP', ORANGE, '1 Hz 필터 (LP)')]:
        m = [v[f'd0.0_n{n}_{key}']['dS_evt'] for n in ns]; rg = [v[f'd0.0_n{n}_{key}']['dS_evt_range'] for n in ns]
        ax.fill_between(nz, [r[0] for r in rg], [r[1] for r in rg], color=c, alpha=0.18, lw=0)
        ax.plot(nz, m, '-o', color=c, lw=2, ms=8, mec=SURF, mew=2)
        ax.text(10.3, m[-1], f'{lab}\n{m[-1]:+.2f}', va='center', color=INK, fontsize=10.5)
    ax.set_xticks(nz); ax.set_xlim(-0.5, 15.2); ax.set_ylim(0, 2.6)
    ax.set_xlabel('변위 잡음 (%)', fontsize=11); ax.set_ylabel('R 대비 이득 (%p)', fontsize=11)
    save(fig, 'fig8_필터_잡음.png')


if __name__ == '__main__':
    style(); fig_timehist(); fig_ai_valve(); fig_test2_events(); fig_noise()
