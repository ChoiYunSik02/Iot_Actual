# -*- coding: utf-8 -*-
"""v3 그림 — 이미 실행된 결과 CSV에서만 만든다 (새 계산 없음). 출력: figures/*.png, figures/SOURCES.md
 fig_v3_1  원문 표 4-6 대 현재: 무제어 최대 응답 비율, 기록별 R 저감률 (원문 RS-TLCD 대 현재 R)
 fig_v3_2  같은 기록의 R·J-AI 저감률 차이(%p)와 비틀림 여유 (원문 공통 8쌍 + 개발 3기록)
 fig_v3_3  응답 시간이력 + 장치 작동: 대표 기록 선택 규칙은 실행 전 고정 — 원문 공통 8쌍 중 무제어 비틀림 최대 기록, 그리고 비틀림 위반이 있는 고베(공개 사유). 둘 다 그림.
"""
import csv, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, '..', 'results'); FIG = os.path.join(HERE, 'figures'); os.makedirs(FIG, exist_ok=True)
for f in ['/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 'C:/Windows/Fonts/malgun.ttf']:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f); plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
def rd(p):
    with open(p, encoding='utf-8-sig') as f: return list(csv.DictReader(l for l in f if not l.startswith('#')))
SRC = []
def save(fig, name, src):
    fig.savefig(os.path.join(FIG, name), dpi=200, bbox_inches='tight'); plt.close(fig); SRC.append((name, src)); print('→', name)
NAMES = ['X max', 'X RMS', 'Y max', 'Y RMS', 'θ max', 'θ RMS']
rep = rd(os.path.join(HERE, 'reproduction_metrics.csv')); src_note = rep[0]['R_repro_source']
recs8 = ['PEER01', 'PEER02', 'PEER03', 'PEER04', 'PEER11', 'PEER13', 'PEER14', 'PEER15']
EVN = {'PEER01': 'IV #11', 'PEER02': 'IV Mexicali', 'PEER03': 'IV Diff', 'PEER04': 'IV Brawley', 'PEER11': 'IV #3', 'PEER13': 'Pacoima', 'PEER14': 'Kobe', 'PEER15': 'Chi-Chi',
       'ElCentro_1940': 'El Centro 1940', 'Pohang_2017_BUS2': 'Pohang', 'Gyeongju_2016_CHJ2': 'Gyeongju'}

# ---- fig 1 ----
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4))
w = 0.12
for k, nm in enumerate(['X max', 'Y max', 'θ max', 'X RMS', 'Y RMS', 'θ RMS']):
    v = [float(r['U_ratio_ours_over_paper']) for r in rep if r['index'] == nm]
    ax[0].bar(np.arange(8) + (k - 2.5) * w, v, w, label=nm, color=plt.cm.tab10(k))
ax[0].axhline(1, color='k', lw=0.8); ax[0].set_xticks(range(8)); ax[0].set_xticklabels([EVN[r] for r in recs8], rotation=30, ha='right')
ax[0].set_ylabel('무제어 응답 (현재 / 원문 표 4-6)'); ax[0].set_title('(a) 무제어 응답 비율: 최대값은 대체로 맞고 RMS는 낮음'); ax[0].legend(ncol=3, fontsize=8, frameon=False)
xs, ys, cl = [], [], []
for r in rep:
    xs.append(float(r['paper_reduction_rs_pct'])); ys.append(float(r['ours_reduction_R_operational_pct'])); cl.append(NAMES.index(r['index']))
sc = ax[1].scatter(xs, ys, c=cl, cmap='tab10', vmin=0, vmax=9, s=30)
ax[1].plot([-5, 60], [-5, 60], 'k--', lw=0.8); ax[1].set_xlabel('원문 RS-TLCD 저감률 (%) — 표 4-6'); ax[1].set_ylabel('현재 원래 R 저감률 (%) — 운영 시간축')
ax[1].set_title('(b) 기록·지표별 저감률 (8쌍×6지표 = 48점)'); ax[1].grid(alpha=0.25)
fig.tight_layout(); save(fig, 'fig_v3_1_reproduction.png', 'paper_tables_4_6.csv, reproduction_metrics.csv (현재 R = JC 고정 시간축, ../results/control_metrics_record_JC_fixed_all.csv)')

# ---- fig 2 ----
mt = rd(os.path.join(HERE, 'matched_R_AI_metrics.csv'))
order = recs8 + ['ElCentro_1940', 'Pohang_2017_BUS2', 'Gyeongju_2016_CHJ2']
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
d = {}
for r in mt:
    if r['timing'].startswith('고정') and r['method'] == 'J-AI': d[r['record_id']] = r
v = [float(d[x]['delta_vs_R_mean6_pp']) for x in order]
cols = ['#D9822B' if d[x]['torsion_violation'] == '예' else '#2F8F6B' for x in order]
ax[0].bar(range(len(order)), v, color=cols); ax[0].axhline(0, color='k', lw=0.8); ax[0].axvline(7.5, color='#999', ls=':')
ax[0].set_xticks(range(len(order))); ax[0].set_xticklabels([EVN[x] for x in order], rotation=35, ha='right')
ax[0].set_ylabel('J-AI 빼기 R (%p, 6지표 평균 저감률)'); ax[0].set_title('(a) 같은 기록·같은 시간축의 R 대비 (주황 = 비틀림 위반 기록)')
ax[0].text(3.5, ax[0].get_ylim()[1] * 0.92, '원문 공통 8쌍', ha='center', color='#555'); ax[0].text(9, ax[0].get_ylim()[1] * 0.92, '개발 추가', ha='center', color='#555')
tm = [float(d[x]['torsion_max_margin_pp']) for x in order]; tr = [float(d[x]['torsion_rms_margin_pp']) for x in order]
ax[1].barh(np.arange(len(order)) - 0.2, tm, 0.38, label='θ 최대 여유', color='#14213D'); ax[1].barh(np.arange(len(order)) + 0.2, tr, 0.38, label='θ RMS 여유', color='#7A9CC6')
ax[1].axvline(0, color='k', lw=0.8); ax[1].set_yticks(range(len(order))); ax[1].set_yticklabels([EVN[x] for x in order]); ax[1].invert_yaxis()
ax[1].set_xlabel('R 대비 저감률 차이 (%p), 음수 = R보다 비틀림 악화'); ax[1].set_title('(b) 비틀림 최대·RMS 각각'); ax[1].legend(frameon=False, fontsize=8)
fig.tight_layout(); save(fig, 'fig_v3_2_matched_R_AI.png', 'matched_R_AI_metrics.csv (J-AI, 고정 시간축)')

# ---- fig 3: 응답 시간이력과 장치 ----
man = {r['record_id']: r for r in rd(os.path.join(HERE, '..', '..', 'data', 'record_manifest.csv'))}
uth = {x: float(next(r for r in mt if r['record_id'] == x and r['method'] == 'U')['abs_θ max_1e-4 rad']) for x in recs8}
rule_rec = max(uth, key=uth.get)          # 규칙: 원문 공통 8쌍 중 무제어 비틀림 최대 기록 (원문 그림 8이 '비틀림 최대 기록'을 쓴 것과 같은 규칙)
for rid, why in ((rule_rec, '규칙 기록: 원문 공통 8쌍 중 무제어 비틀림 최대'), ('PEER14', '비틀림 위반이 있는 기록(공개 사유)')):
    S = rd(os.path.join(RES, f'JC_series_{rid}_all.csv'))
    by = {}
    for r in S: by.setdefault(r['method'], []).append(r)
    A = {m: {k: np.array([float(x[k]) for x in v]) for k in ('t_s', 'ux_m', 'uy_m', 'th_rad', 'pump_f_dev_hz', 'rotation_rad', 'valve_kappa')} for m, v in by.items()}
    plt.rcParams['font.size'] = 12.5
    fig, ax = plt.subplots(3, 2, figsize=(11.5, 7.2), sharex=True)
    tend = (int(man[rid]['n_samples_dt001']) - 1001) * 0.01
    for (m, c, lab) in (('U', '#9AA0A6', '무제어'), ('R', '#14213D', '원래 R'), ('J-AI', '#D9822B', 'J-AI')):
        a = A[m]
        ax[0, 0].plot(a['t_s'], a['ux_m'] * 100, color=c, lw=0.9, label=lab); ax[1, 0].plot(a['t_s'], a['uy_m'] * 100, color=c, lw=0.9); ax[2, 0].plot(a['t_s'], a['th_rad'] * 1e4, color=c, lw=0.9)
        if m != 'U':
            ax[0, 1].plot(a['t_s'], a['pump_f_dev_hz'], color=c, lw=0.9); ax[0, 1].set_ylim(0.318, 0.356); ax[1, 1].plot(a['t_s'], np.degrees(a['rotation_rad']), color=c, lw=0.9); ax[2, 1].plot(a['t_s'], a['valve_kappa'], color=c, lw=0.9, drawstyle='steps-post')
    for a_, t in zip(ax[:, 0], ['X 변위 (cm)', 'Y 변위 (cm)', '비틀림각 (1e-4 rad)']): a_.set_ylabel(t)
    for a_, t in zip(ax[:, 1], ['펌프 진동수 (Hz)', '회전판 각도 (°)', '밸브 개구율 κ']): a_.set_ylabel(t)
    ax[0, 0].legend(frameon=False, ncol=3); ax[2, 0].set_xlabel('시간 (s)'); ax[2, 1].set_xlabel('시간 (s)')
    for a_ in ax.ravel(): a_.set_xlim(0, tend); a_.grid(alpha=0.2)
    fig.suptitle(f'{EVN[rid]} ({rid}) — {why}', fontsize=12.5)
    fig.tight_layout(); save(fig, f'fig_v3_3_response_{rid}.png', f'../results/JC_series_{rid}_all.csv (U, R, J-AI 열)')
# ---- fig 4: 세 액추에이터 실제 동작 (R 대 J-AI) — 규칙 기록과 고베 ----
fig, ax = plt.subplots(3, 2, figsize=(11.5, 6.8), sharex='col')
for col, rid in enumerate((rule_rec, 'PEER14')):
    S = rd(os.path.join(RES, f'JC_series_{rid}_all.csv')); by = {}
    for r in S: by.setdefault(r['method'], []).append(r)
    tend = (int(man[rid]['n_samples_dt001']) - 1001) * 0.01
    for m, c, lab in (('R', '#14213D', '원래 R'), ('J-AI', '#D9822B', 'J-AI')):
        t = np.array([float(x['t_s']) for x in by[m]])
        ax[0, col].plot(t, [float(x['pump_f_dev_hz']) for x in by[m]], color=c, lw=1.0, label=lab)
        ax[1, col].plot(t, np.degrees([float(x['rotation_rad']) for x in by[m]]), color=c, lw=1.0)
        ax[2, col].plot(t, [float(x['valve_kappa']) for x in by[m]], color=c, lw=1.0, drawstyle='steps-post')
    ax[0, col].set_ylim(0.318, 0.356); ax[0, col].set_title(f'{EVN[rid]} ({rid})'); ax[2, col].set_xlabel('시간 (s)')
    for r_ in range(3): ax[r_, col].set_xlim(0, tend); ax[r_, col].grid(alpha=0.2)
ax[0, 0].set_ylabel('펌프 진동수 (Hz)'); ax[1, 0].set_ylabel('회전판 각도 (°)'); ax[2, 0].set_ylabel('밸브 개구율 κ'); ax[0, 0].legend(frameon=False)
fig.tight_layout(); save(fig, 'fig_v3_4_actuators.png', '../results/JC_series_PEER11_all.csv, JC_series_PEER14_all.csv (R, J-AI 열: pump_f_dev_hz, rotation_rad, valve_kappa)')

plt.rcParams['font.size'] = 10.5
# ---- fig 5: 실측 지연 — 같은 개발 3사건의 고정/1차/2차, 확대 평가는 따로 ----
sm = rd(os.path.join(HERE, 'matched_R_AI_metrics.csv'))
def dm(timing, rid):
    return float(next(r for r in sm if r['method'] == 'J-AI' and r['timing'] == timing and r['record_id'] == rid)['delta_vs_R_mean6_pp'])
dev3 = [('PEER14', '고베'), ('ElCentro_1940', 'El Centro'), ('Pohang_2017_BUS2', '포항')]
TIM = [('고정 시간축(JC)', '고정 시간축', '#9AA0A6'), ('실측 지연 1차(JC, 개발 3기록)', '실측 1차', '#14213D'), ('실측 지연 2차(JCA, 11기록)', '실측 2차', '#D9822B')]
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4), gridspec_kw=dict(width_ratios=[1.3, 1]))
for k, (tm, lab, c) in enumerate(TIM):
    v = [dm(tm, r) for r, _ in dev3] + [float(np.mean([dm(tm, r) for r, _ in dev3]))]
    ax[0].bar(np.arange(4) + (k - 1) * 0.26, v, 0.26, label=lab, color=c)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels([n for _, n in dev3] + ['3사건 평균']); ax[0].axhline(0, color='k', lw=0.8)
ax[0].set_ylabel('J-AI 빼기 R (%p, 6지표 평균 저감률)'); ax[0].set_title('(a) 같은 개발 3사건: 고정 시간축과 실측 지연 1차·2차'); ax[0].legend(frameon=False)
ss = {(r['subset'], r['timing'], r['method']): r for r in rd(os.path.join(HERE, 'matched_R_AI_summary.csv'))}
labs, vals = [], []
for sub, tag in (('A 원문 공통 8쌍 (4사건)', '8쌍'), ('A+B 개발 11기록 (7사건, 확대 평가)', '7사건')):
    for tm, lab in (('고정 시간축(JC)', '고정'), ('실측 지연 2차(JCA, 11기록)', '실측 2차')):
        labs.append(f'{tag}\n{lab}'); vals.append(float(ss[(sub, tm, 'J-AI')]['event_equal_delta_pp']))
ax[1].bar(range(4), vals, color=['#9AA0A6', '#D9822B'] * 2); ax[1].set_xticks(range(4)); ax[1].set_xticklabels(labs); ax[1].axhline(0, color='k', lw=0.8)
ax[1].set_ylabel('사건 동일 가중 (%p)'); ax[1].set_title('(b) 별도 확대 평가 (개발 3사건과 다른 범위)')
fig.tight_layout(); save(fig, 'fig_v3_5_delay.png', 'matched_R_AI_metrics.csv, matched_R_AI_summary.csv (J-AI, 고정 시간축·실측 1차·실측 2차)')

with open(os.path.join(FIG, 'SOURCES.md'), 'w', encoding='utf-8') as f:
    f.write('# v3 그림 ↔ 원자료\n\n새 계산 없이 이미 실행된 CSV에서만 만들었다. R 재현(지연 0)의 출처: ' + src_note + '\n\n| 그림 | 자료 |\n|---|---|\n')
    for n, s in SRC: f.write(f'| `{n}` | {s} |\n')
print('규칙 기록:', rule_rec)
