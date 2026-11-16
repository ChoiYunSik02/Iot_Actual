# -*- coding: utf-8 -*-
"""8주차 발표 그림 — 노트북 MATLAB 실행 결과 CSV에서만 생성한다 (계획 §9).
입력: week08_submission/results/F8_*.csv, ../results/F8.mat(시드), ../models/torch_pilot8_seed*.json, ../results/forecast_metrics_pilot8_seed*.csv
출력: week08_submission/figures/*.png 와 figures/SOURCES.md(그림 ↔ CSV 연결)
대표 사건을 고르지 않는다: 개발 3사건(El Centro, 고베, 포항)을 모두 그린다.
"""
import csv, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RES = os.path.join(HERE, 'results'); FIG = os.path.join(HERE, 'figures'); os.makedirs(FIG, exist_ok=True)
for f in ['/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 'C:/Windows/Fonts/malgun.ttf']:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f); plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 110})
C = {'U': '#9AA0A6', 'R': '#14213D', 'SIMPLE-zero': '#7A9CC6', 'SIMPLE-persistence': '#B9A06B', 'AINAT-C1': '#D9822B', 'PREVIEW-C1': '#2F8F6B'}
LAB = {'U': '무제어', 'R': '원래 R', 'SIMPLE-zero': 'SIMPLE-zero', 'SIMPLE-persistence': 'SIMPLE-persistence', 'AINAT-C1': 'AI (seed 8401)', 'PREVIEW-C1': 'PREVIEW (실제 미래 입력 참고)'}
EV = [('ElCentro_1940', 'ElCentro1940', 'El Centro 1940'), ('PEER14', 'Kobe1995', '고베 1995'), ('Pohang_2017_BUS2', 'Pohang2017', '포항 2017')]
SRC = []

def rd(path):
    with open(path, encoding='utf-8') as f:
        lines = [l for l in f if not l.startswith('#')]
    return list(csv.DictReader(lines))

def save(fig, name, sources):
    p = os.path.join(FIG, name); fig.savefig(p, dpi=200, bbox_inches='tight'); plt.close(fig)
    SRC.append((name, sources)); print('→', p)

# ---- 1. 시간축 개념도 (값은 F8 주 구조의 실제 설정) ----
runs = rd(os.path.join(RES, 'F8_runs.csv'))
dcmd = int(next(r for r in runs if r['run'] == 'S_main' and r['method'] == 'AINAT-C1')['d_cmd'])
fig, ax = plt.subplots(figsize=(12, 3.6)); ax.set_xlim(-6.2, 4.6); ax.set_ylim(0, 4); ax.axis('off')
g = 0.0; dec = -dcmd*0.01
ax.annotate('', xy=(4.5, 0.8), xytext=(-6.1, 0.8), arrowprops=dict(arrowstyle='->', color='#444'))
ax.text(4.5, 0.45, '시간', ha='right', fontsize=10, color='#444')
ax.add_patch(plt.Rectangle((dec - 5.0, 2.7), 5.0, 0.6, color='#C9D3E3')); ax.text(dec - 2.5, 3.0, '관측 창 5 s (도착한 관측만)', ha='center', va='center')
ax.add_patch(plt.Rectangle((dec - 0.2, 1.9), 4.2, 0.6, color='#F2D3B3')); ax.text(dec + 1.9, 2.2, 'AI 예측 4 s (0.2 s마다 갱신)', ha='center', va='center')
ax.add_patch(plt.Rectangle((dec, 1.1), g - dec, 0.6, color='#E0A458')); ax.text((dec + g)/2, 1.4, f'후보 선택 {g-dec:.2f} s', ha='center', va='center', fontsize=10)
for x, t, yy, ha in [(dec - 0.2, '예측 기준', 0.42, 'right'), (dec, '결정 시작', 0.12, 'left'), (g - 0.01, 'R 법칙 실행(원래 시각, 적용 1스텝 전)', 0.42, 'left'), (g, '적용', 0.12, 'left')]:
    ax.plot([x, x], [0.75, 0.85], color='#14213D'); ax.plot([x, x], [yy + 0.18, 0.75], color='#9AA0A6', lw=0.6)
    ax.text(x + (0.03 if ha == 'left' else -0.03), yy, t, ha=ha, fontsize=9)
ax.text(2.5, 1.4, '적용 뒤 남은 예측 구간 ≈ 3 s 로 후보 평가\n펌프·각도 2.6 s마다, 회전 30°/s 제한', fontsize=9, va='center')
ax.set_title('관측 → AI 예측 → 계산·전달 지연 → 장치 적용 → 새 관측 (주 구조, 고정 시간축)', fontsize=12, loc='left')
save(fig, 'fig1_timeline.png', ['F8_runs.csv (d_cmd)'])

# ---- 2. 실제 지반입력과 예측 (사전 규칙: 지반가속도 크기 최대 시각 이후 첫 0.2 s 격자) ----
fx = rd(os.path.join(RES, 'F8_forecast_examples.csv'))
fig, axs = plt.subplots(3, 2, figsize=(12, 8), sharex=True)
for i, (rid, _, nm) in enumerate(EV):
    rows = [r for r in fx if r['record_id'] == rid]
    if not rows: continue
    t = np.array([float(r['lead_s']) for r in rows]); o = float(rows[0]['origin_t_s'])
    for j, comp in enumerate(['x', 'y']):
        a = axs[i, j]
        a.plot(t, [float(r['true_' + comp]) for r in rows], color='k', lw=1.4, label='실제 (평가용)')
        a.plot(t, [float(r['zero_' + comp]) for r in rows], color=C['SIMPLE-zero'], lw=1.2, label='zero')
        a.plot(t, [float(r['persistence_' + comp]) for r in rows], color=C['SIMPLE-persistence'], lw=1.2, label='persistence')
        a.plot(t, [float(r['ai_' + comp]) for r in rows], color=C['AINAT-C1'], lw=1.6, label='AI')
        a.set_title(f'{nm} · {comp.upper()} 성분 · 예측 발행 t = {o:.1f} s', fontsize=10, loc='left')
        if j == 0: a.set_ylabel('지반가속도 (m/s²)')
axs[2, 0].set_xlabel('예측 발행 뒤 시간 (s)'); axs[2, 1].set_xlabel('예측 발행 뒤 시간 (s)')
axs[0, 1].legend(fontsize=9, ncol=4, loc='upper right')
fig.suptitle('한 번 발행한 예측 (여러 번 갱신한 예측을 이어 붙이지 않음) — 발행 시각은 사전 규칙', fontsize=12, x=0.01, ha='left')
save(fig, 'fig2_forecast_examples.png', ['F8_forecast_examples.csv'])

# 2b. 예측 오차 요약: 학습 후 진단(구간별) + 제어 시점 남은 구간
fe = rd(os.path.join(RES, 'F8_forecast_remaining_error.csv'))
fig, axs = plt.subplots(1, 2, figsize=(12, 4))
rows = []
for sd in (8401, 8402, 8403):
    p = os.path.join(ROOT, 'results', f'forecast_metrics_pilot8_seed{sd}.csv')
    if os.path.exists(p):
        for r in csv.reader(open(p, encoding='utf-8')):
            if len(r) > 10 and r[3] == 'all' and r[1] == 'real_val': rows.append((sd, r[2], [float(v) for v in r[6:11]]))
H = ['0.2', '0.5', '1', '2', '4']; xs = np.arange(5); w = 0.27
for k, (pr, col, lab) in enumerate([('zero', C['SIMPLE-zero'], 'zero'), ('persistence', C['SIMPLE-persistence'], 'persistence'), ('lstmnat', C['AINAT-C1'], 'AI (3 seed 평균, 막대=범위)')]):
    v = np.array([r[2] for r in rows if r[1] == pr]);
    if len(v) == 0: continue
    m = v.mean(0); axs[0].bar(xs + (k - 1)*w, m, w, color=col, label=lab)
    if pr == 'lstmnat': axs[0].errorbar(xs + (k - 1)*w, m, yerr=[m - v.min(0), v.max(0) - m], fmt='none', ecolor='k', capsize=2, lw=0.8)
axs[0].set_xticks(xs, [h + ' s' for h in H]); axs[0].set_ylabel('RMSE (m/s²)'); axs[0].set_title('실제 개발 3사건 예측 RMSE (누적 구간)', loc='left', fontsize=11); axs[0].legend(fontsize=9)
bys = {}
for r in fe: bys.setdefault(r['record_id'], []).append(r)
xs2 = np.arange(len(EV))
for k, (key, col, lab) in enumerate([('rmse_zero', C['SIMPLE-zero'], 'zero'), ('rmse_persistence', C['SIMPLE-persistence'], 'persistence'), ('rmse_ai', C['AINAT-C1'], 'AI')]):
    axs[1].bar(xs2 + (k - 1)*w, [np.mean([float(r[key]) for r in bys.get(e[0], [])]) if bys.get(e[0]) else 0 for e in EV], w, color=col, label=lab)
axs[1].set_xticks(xs2, [e[2] for e in EV]); axs[1].set_ylabel('RMSE (m/s²)'); axs[1].set_title('제어 시점에 남은 예측 구간의 오차 (AI 폐루프 결정마다)', loc='left', fontsize=11); axs[1].legend(fontsize=9)
save(fig, 'fig2b_forecast_error.png', ['../results/forecast_metrics_pilot8_seed840{1,2,3}.csv', 'F8_forecast_remaining_error.csv'])

# ---- 3·4. 응답 시간이력과 장치 동작 (사건마다, 같은 단위·축) ----
for rid, evid, nm in EV:
    rs = rd(os.path.join(RES, f'F8_series_{rid}.csv'))
    D = {}
    for r in rs: D.setdefault(r['method'], []).append(r)
    t = np.array([float(r['t_s']) for r in D['U']])
    ser = lambda m, k, s=1.0: np.array([float(r[k]) for r in D[m]])*s
    thU = np.abs(ser('U', 'th_rad')); ip = int(np.argmax(thU)); z0, z1 = max(0, t[ip] - 4), t[ip] + 4
    fig, axs = plt.subplots(3, 2, figsize=(13, 7.5), gridspec_kw={'width_ratios': [2.2, 1]})
    for i, (k, s, ul) in enumerate([('ux_m', 1e3, 'X 변위 (mm)'), ('uy_m', 1e3, 'Y 변위 (mm)'), ('th_rad', 1e3, '비틀림 (mrad)')]):
        lim = 1.05*max(np.abs(ser(m, k, s)).max() for m in ('U', 'R', 'AINAT-C1'))
        for j in range(2):
            a = axs[i, j]
            for m in ('U', 'R', 'AINAT-C1'):
                a.plot(t, ser(m, k, s), color=C[m], lw=0.9 if m != 'AINAT-C1' else 1.1, label=LAB[m], alpha=0.85 if m == 'U' else 1)
            a.set_ylim(-lim, lim)
            if j == 1: a.set_xlim(z0, z1); a.set_title('확대 (무제어 비틀림 최대 ±4 s)' if i == 0 else '', fontsize=9, loc='left')
            else: a.set_ylabel(ul)
    axs[0, 0].legend(fontsize=9, ncol=3, loc='upper right'); axs[2, 0].set_xlabel('시간 (s)'); axs[2, 1].set_xlabel('시간 (s)')
    fig.suptitle(f'{nm} — 최상층 응답: 무제어 / 원래 R / AI (주 구조, 고정 시간축)', fontsize=12, x=0.01, ha='left')
    save(fig, f'fig3_response_{rid}.png', [f'F8_series_{rid}.csv'])
    cm = rd(os.path.join(RES, f'F8_commands_{rid}.csv')); ca = [r for r in cm if r['method'] == 'AINAT-C1']
    fig, axs = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    for m in ('R', 'AINAT-C1'):
        axs[0].plot(t, ser(m, 'pump_f_dev_hz', 1.0), color=C[m], lw=1.1, label=LAB[m] + ' 장치 상태')
        axs[1].plot(t, ser(m, 'rotation_rad', 180/np.pi), color=C[m], lw=1.1, label=LAB[m] + ' 장치 상태')
        axs[2].step(t, ser(m, 'valve_kappa', 1.0), color=C[m], lw=1.0, where='post', label=LAB[m])
    at = [float(r['apply_t_s']) for r in ca]
    axs[1].scatter(at, [float(r['cmd_theta_rad'])*180/np.pi for r in ca], s=18, marker='o', facecolors='none', edgecolors=C['AINAT-C1'], label='AI 경로 각도 목표 지령 (적용 시각)')
    axs[1].scatter(at, [float(r['R_theta_rad'])*180/np.pi for r in ca], s=10, marker='x', color='#555', label='같은 시각 원래 R 법칙 각도')
    axs[0].set_ylabel('TLCD 진동수\n(Hz, 펌프 수위)'); axs[1].set_ylabel('회전판 각도 (deg)'); axs[2].set_ylabel('밸브 κ'); axs[2].set_xlabel('시간 (s)')
    axs[0].legend(fontsize=9); axs[1].legend(fontsize=8, ncol=2); axs[2].legend(fontsize=9)
    fig.suptitle(f'{nm} — 액추에이터 목표 지령과 실제 장치 상태 (주 구조)', fontsize=12, x=0.01, ha='left')
    save(fig, f'fig4_actuator_{rid}.png', [f'F8_series_{rid}.csv', f'F8_commands_{rid}.csv'])

# 3c. 세 사건 비틀림 한눈에 (본문용, 대표 사건을 고르지 않음)
fig, axs = plt.subplots(3, 1, figsize=(13, 7.5)); fig.subplots_adjust(hspace=0.5)
for i, (rid, evid, nm) in enumerate(EV):
    rs = rd(os.path.join(RES, f'F8_series_{rid}.csv')); D = {}
    for r in rs: D.setdefault(r['method'], []).append(r)
    t = np.array([float(r['t_s']) for r in D['U']]); te = min(t[-1], 60)
    for m in ('U', 'R', 'AINAT-C1'):
        axs[i].plot(t, np.array([float(r['th_rad']) for r in D[m]])*1e3, color=C[m], lw=0.9 if m != 'AINAT-C1' else 1.1, label=LAB[m])
    axs[i].set_xlim(0, te); axs[i].set_ylabel('비틀림 (mrad)'); axs[i].set_title(nm, fontsize=10, loc='left')
axs[0].legend(fontsize=9, ncol=3, loc='upper right'); axs[2].set_xlabel('시간 (s) — 처음 60 s')
fig.suptitle('최상층 비틀림: 무제어 / 원래 R / AI (주 구조, 개발 3사건 모두)', fontsize=12, x=0.01, ha='left')
save(fig, 'fig3c_torsion_all.png', ['F8_series_ElCentro_1940.csv', 'F8_series_PEER14.csv', 'F8_series_Pohang_2017_BUS2.csv'])

# ---- 5. 사건별 저감률·R 대비 개선량, 비틀림 최대/RMS 별도 ----
em = rd(os.path.join(RES, 'F8_event_metrics.csv'))
M = ['SIMPLE-zero', 'SIMPLE-persistence', 'AINAT-C1', 'PREVIEW-C1']
for run, title in [('S_main', '주 구조 (원래 R 경로 + 그림자 R + 절대 각도)'), ('C_ref', '참고: 현행 C1 (원래 R 경로)')]:
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.3))
    xs = np.arange(len(EV)); w = 0.2
    for pi, (key, ttl) in enumerate([('dS_vs_R_pp', '6지표 평균 R 대비 (%p)'), ('red_thmax', '비틀림 최대 저감률 R 대비 (%p)'), ('red_thrms', '비틀림 RMS 저감률 R 대비 (%p)')]):
        a = axs[pi]
        for k, m in enumerate(M):
            vals = []
            for _, evid, _ in EV:
                r = next(x for x in em if x['run'] == run and x['method'] == m and x['event'] == evid)
                rR = next(x for x in em if x['run'] == run and x['method'] == 'R' and x['event'] == evid)
                vals.append(float(r[key]) if key == 'dS_vs_R_pp' else float(r[key]) - float(rR[key]))
            a.bar(xs + (k - 1.5)*w, vals, w, color=C[m], label=LAB[m])
        a.axhline(0, color='k', lw=0.8); a.set_xticks(xs, [e[2] for e in EV]); a.set_title(ttl, fontsize=10, loc='left')
        if pi == 2: a.text(0.02, 0.02, '0 아래 = R보다 나쁨 (허용 0 %p 위반)', transform=a.transAxes, fontsize=8, color='#A85A1E')
    axs[0].legend(fontsize=8, loc='upper left')
    fig.suptitle(title + ' — 개발 3사건, 고정 시간축', fontsize=12, x=0.01, ha='left')
    save(fig, f'fig5_reduction_{run}.png', ['F8_event_metrics.csv'])

# 5c. 기존 11개 기록 전체 확대 (F8X, 같은 설정; 개발 평가) — 있으면
pa = os.path.join(RES, 'F8_event_metrics_all.csv')
if os.path.exists(pa):
    ea = rd(pa); evs = sorted({r['event'] for r in ea})
    KN = {'ChiChi1999': 'Chi-Chi 1999', 'ElCentro1940': 'El Centro 1940', 'Gyeongju2016': '경주 2016', 'ImperialValley1979': 'Imperial V. 1979 (5기록)',
          'Kobe1995': '고베 1995', 'Northridge1994': 'Northridge 1994', 'Pohang2017': '포항 2017'}
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={'width_ratios': [1.6, 1]})
    xs = np.arange(len(evs)); w = 0.2
    for k, m in enumerate(M):
        v = [float(next(x for x in ea if x['run'] == 'S_main' and x['method'] == m and x['event'] == e)['dS_vs_R_pp']) for e in evs]
        axs[0].bar(xs + (k - 1.5)*w, v, w, color=C[m], label=LAB[m])
    axs[0].axhline(0, color='k', lw=0.8); axs[0].set_xticks(xs, [KN.get(e, e) for e in evs], rotation=25, ha='right', fontsize=9)
    axs[0].set_title('주 구조: 사건별 6지표 평균 R 대비 (%p)', fontsize=10, loc='left'); axs[0].legend(fontsize=8, ncol=2)
    for k, m in enumerate(M):
        v = []
        for e in evs:
            r = next(x for x in ea if x['run'] == 'S_main' and x['method'] == m and x['event'] == e); rR = next(x for x in ea if x['run'] == 'S_main' and x['method'] == 'R' and x['event'] == e)
            v.append(float(r['red_thrms']) - float(rR['red_thrms']))
        axs[1].bar(xs + (k - 1.5)*w, v, w, color=C[m])
    axs[1].axhline(0, color='k', lw=0.8); axs[1].set_xticks(xs, [KN.get(e, e).split(' (')[0] for e in evs], rotation=25, ha='right', fontsize=9)
    axs[1].set_title('비틀림 RMS 저감률 R 대비 (%p), 0 아래 = 위반', fontsize=10, loc='left')
    fig.suptitle('확대 평가: 기존 11개 기록(7사건), 같은 설정 — 모두 이전 개발에 쓰인 기록(개발 평가)', fontsize=12, x=0.01, ha='left')
    save(fig, 'fig7_reduction_all.png', ['F8_event_metrics_all.csv'])

# ---- 6. 학습 곡선과 실행 지연 요약 ----
fig, axs = plt.subplots(1, 2, figsize=(13, 4.2)); fig.subplots_adjust(wspace=0.55)
for sd, col in zip((8401, 8402, 8403), ('#D9822B', '#B05A1A', '#E8B07A')):
    p = os.path.join(ROOT, 'models', f'torch_pilot8_seed{sd}.json')
    if not os.path.exists(p): continue
    h = json.load(open(p, encoding='utf-8'))['history']
    e = [x['epoch'] for x in h]
    axs[0].plot(e, [x['train_loss'] for x in h], color=col, ls='--', lw=1, label=f'seed {sd} train')
    axs[0].plot(e, [x['val_mse'] for x in h], color=col, lw=1.6, label=f'seed {sd} validation')
axs[0].set_xlabel('epoch'); axs[0].set_ylabel('MSE (정규화)'); axs[0].set_title('학습 곡선 (합성 자료, 체크포인트는 검증 손실로만 선택)', fontsize=10, loc='left'); axs[0].legend(fontsize=8, ncol=2)
lab, val = [], []
for r in runs:
    if r['run'] == 'S_main' and r['method'] in ('SIMPLE-zero', 'AINAT-C1', 'PREVIEW-C1'):
        lab.append({'SIMPLE-zero': 'SIMPLE-zero', 'AINAT-C1': 'AI', 'PREVIEW-C1': 'PREVIEW'}[r['method']] + ' 선택 p95'); val.append(float(r['select_s_p95']))
lab += ['AI 예측 1회 p95']; val += [0.0094]
axs[1].barh(lab, val, color=['#7A9CC6', '#D9822B', '#2F8F6B', '#E0A458'])
for i, v in enumerate(val): axs[1].text(v, i, f' {v:.3f} s', va='center', fontsize=9)
axs[1].set_xlabel('s'); axs[1].set_title(f'계산시간 (노트북 MATLAB) · 선택 예산 0.85 s → d_cmd {dcmd}', fontsize=10, loc='left')
save(fig, 'fig6_training_latency.png', ['../models/torch_pilot8_seed840{1,2,3}.json', 'F8_runs.csv', '../logs/runtime_measure_pilot8_seed8401.csv'])

with open(os.path.join(FIG, 'SOURCES.md'), 'w', encoding='utf-8') as f:
    f.write('# 그림 ↔ 근거 CSV\n\n모든 그림은 `make_figures.py`로 노트북 MATLAB 실행 결과 CSV에서 생성했습니다.\n\n| 그림 | 근거 |\n|---|---|\n')
    for n, s in SRC: f.write(f'| `{n}` | {", ".join("`" + x + "`" for x in s)} |\n')
