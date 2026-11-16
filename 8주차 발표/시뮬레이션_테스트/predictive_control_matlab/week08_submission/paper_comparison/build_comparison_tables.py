# -*- coding: utf-8 -*-
"""v3 §5-7: 원문 표 4-6 대 현재 재현 비교(reproduction_metrics.csv, reproduction_summary.csv)와
같은 기록·같은 조건의 R·AI 비교(matched_R_AI_metrics.csv, matched_R_AI_summary.csv)를 만든다.
입력은 모두 이미 실행된 결과 파일이다(원문 표 전사, MATLAB 폐루프 결과 CSV). 이 스크립트는 폐루프를 실행하지 않는다.
  paper_tables_4_6.csv                   원문 표 4-6 (extract_paper_tables.py)
  PR_records.csv / PR_records_octave.csv  원문 재현 조건(지연 0) 무제어·R (run_paper_repro.m; MATLAB 결과가 있으면 그것을 씀)
  ../../results/control_metrics_record_JC_fixed_all.csv  JC 고정 시간축(U, R, J-zero, J-persistence, J-AIF, J-AI, C1J-AI, J-PREVIEW) 11개 기록
  ../../results/control_metrics_record_JC_actual*.csv     J-AI 실측 지연
평균 단위 표기: 'paper_mean' = 지표별 기록 평균(원문 표 7 방식), 'event_equal' = 기록→사건 내 평균→사건 동일 가중.
"""
import csv, glob, os, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, '..', '..', 'results'))
IDX = [('X', 'max', 'ux_max', 100.0, 'cm'), ('X', 'rms', 'ux_rms', 100.0, 'cm'), ('Y', 'max', 'uy_max', 100.0, 'cm'),
       ('Y', 'rms', 'uy_rms', 100.0, 'cm'), ('TH', 'max', 'th_max', 1e4, '1e-4 rad'), ('TH', 'rms', 'th_rms', 1e4, '1e-4 rad')]
NAMES = ['X max', 'X RMS', 'Y max', 'Y RMS', 'θ max', 'θ RMS']
PAIRS = {'PEER01': 1, 'PEER02': 2, 'PEER03': 3, 'PEER04': 4, 'PEER11': 11, 'PEER13': 13, 'PEER14': 14, 'PEER15': 15}
EVENT = {'PEER01': 'ImperialValley1979', 'PEER02': 'ImperialValley1979', 'PEER03': 'ImperialValley1979', 'PEER04': 'ImperialValley1979', 'PEER11': 'ImperialValley1979',
         'PEER13': 'Northridge1994', 'PEER14': 'Kobe1995', 'PEER15': 'ChiChi1999', 'ElCentro_1940': 'ElCentro1940', 'Pohang_2017_BUS2': 'Pohang2017', 'Gyeongju_2016_CHJ2': 'Gyeongju2016'}
ORDER = ['PEER01', 'PEER02', 'PEER03', 'PEER04', 'PEER11', 'PEER13', 'PEER14', 'PEER15', 'ElCentro_1940', 'Pohang_2017_BUS2', 'Gyeongju_2016_CHJ2']
TOL = 1e-12

def readcsv(p):
    with open(p, encoding='utf-8-sig') as f:
        return list(csv.DictReader(l for l in f if not l.startswith('#')))
def w(path, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)
def red(c, u): return 100.0 * (1.0 - c / u)

# ---------------- 원문 표 ----------------
P = collections.defaultdict(dict)
for r in readcsv(os.path.join(HERE, 'paper_tables_4_6.csv')):
    P[int(r['no'])][(r['component'], r['stat'])] = {k: float(r[k]) for k in ('without', 'passive', 's_tlcd', 'rs_tlcd')}

# ---------------- 현재 결과 ----------------
JC = {(r['record_id'], r['method']): {k: float(r[k]) for k in ('ux_max', 'ux_rms', 'uy_max', 'uy_rms', 'th_max', 'th_rms')} for r in readcsv(os.path.join(RES, 'control_metrics_record_JC_fixed_all.csv'))}
pr_file = next((p for p in (os.path.join(HERE, 'PR_records.csv'), os.path.join(HERE, 'PR_records_octave.csv')) if os.path.exists(p)), None)
PR, pr_src = {}, 'none'
if pr_file:
    pr_src = 'MATLAB' if pr_file.endswith('PR_records.csv') else 'Octave 예비(MATLAB 확인 전)'
    for r in readcsv(pr_file):
        PR[(r['record_id'], float(r['dt']), r['method'])] = {k: float(r[k]) for k in ('ux_max', 'ux_rms', 'uy_max', 'uy_rms', 'th_max', 'th_rms')}

# 꼬리 0 구간(10 s)을 뺀 RMS (민감도). 시계열은 JC 고정 시간축 결과의 0.02 s 간격 저장본
def rms_no_tail(rid, method):
    f = os.path.join(HERE, '..', 'results', f'JC_series_{rid}_all.csv')
    man = {r['record_id']: r for r in readcsv(os.path.join(HERE, '..', '..', 'data', 'record_manifest.csv'))}
    if not os.path.exists(f): return None
    n_end = (int(man[rid]['n_samples_dt001']) - 1 - 1000) * 0.01
    ux, uy, th = [], [], []
    for r in readcsv(f):
        if r['method'] == method and float(r['t_s']) <= n_end + 1e-9: ux.append(float(r['ux_m'])); uy.append(float(r['uy_m'])); th.append(float(r['th_rad']))
    if not ux: return None
    return [float(np.sqrt(np.mean(np.square(a)))) for a in (ux, uy, th)]

# ---------------- reproduction_metrics.csv ----------------
rows = []
for rid, no in PAIRS.items():
    for (c, s, key, f, unit), nm in zip(IDX, NAMES):
        p = P[no][(c, s)]
        u = JC[(rid, 'U')][key] * f; ro = JC[(rid, 'R')][key] * f
        x = dict(paper_no=no, record_id=rid, index=nm, unit=unit, paper_without=p['without'], paper_passive=p['passive'], paper_s_tlcd=p['s_tlcd'], paper_rs_tlcd=p['rs_tlcd'],
                 ours_without_JCrun=round(u, 4), U_ratio_ours_over_paper=round(u / p['without'], 4),
                 ours_R_operational=round(ro, 4), R_oper_error_pct=round(100 * (ro / p['rs_tlcd'] - 1), 2),
                 paper_reduction_rs_pct=round(red(p['rs_tlcd'], p['without']), 3), ours_reduction_R_operational_pct=round(red(ro, u), 3))
        x['diff_oper_minus_paper_pp'] = round(x['ours_reduction_R_operational_pct'] - x['paper_reduction_rs_pct'], 3)
        for dt in (0.01, 0.005):
            if (rid, dt, 'R') in PR:
                ur = PR[(rid, dt, 'U')][key] * f; rr = PR[(rid, dt, 'R')][key] * f
                x[f'ours_without_repro_dt{dt:g}'] = round(ur, 4); x[f'ours_R_repro_dt{dt:g}'] = round(rr, 4)
                x[f'ours_reduction_R_repro_dt{dt:g}_pct'] = round(red(rr, ur), 3)
                x[f'diff_repro_dt{dt:g}_minus_paper_pp'] = round(red(rr, ur) - x['paper_reduction_rs_pct'], 3)
            else:
                x[f'ours_without_repro_dt{dt:g}'] = x[f'ours_R_repro_dt{dt:g}'] = x[f'ours_reduction_R_repro_dt{dt:g}_pct'] = x[f'diff_repro_dt{dt:g}_minus_paper_pp'] = ''
        if s == 'rms':
            a = rms_no_tail(rid, 'U'); b = rms_no_tail(rid, 'R'); k = {'X': 0, 'Y': 1, 'TH': 2}[c]
            x['sens_without_RMS_no_tail'] = round(a[k] * f, 4) if a else ''
            x['sens_U_ratio_no_tail'] = round(a[k] * f / p['without'], 4) if a else ''
            x['sens_reduction_R_oper_no_tail_pct'] = round(red(b[k], a[k]), 3) if (a and b) else ''
        else:
            x['sens_without_RMS_no_tail'] = x['sens_U_ratio_no_tail'] = x['sens_reduction_R_oper_no_tail_pct'] = ''
        x['R_repro_source'] = pr_src
        rows.append(x)
w(os.path.join(HERE, 'reproduction_metrics.csv'), rows)

# ---------------- reproduction_summary.csv: 같은 8쌍 부분집합 ----------------
def mean_red(getter):
    out = {}
    for k, nm in enumerate(NAMES):
        out[nm] = float(np.mean([getter(rid, no, k) for rid, no in PAIRS.items()]))
    return out
def ev_equal(getter):
    byev = collections.defaultdict(list)
    for rid, no in PAIRS.items():
        byev[EVENT[rid]].append([getter(rid, no, k) for k in range(6)])
    return np.mean([np.mean(v, axis=0) for v in byev.values()], axis=0)
g_paper = lambda rid, no, k: red(P[no][IDX[k][:2]]['rs_tlcd'], P[no][IDX[k][:2]]['without'])
g_oper = lambda rid, no, k: red(JC[(rid, 'R')][IDX[k][2]], JC[(rid, 'U')][IDX[k][2]])
g_u_paper_passive = lambda rid, no, k: red(P[no][IDX[k][:2]]['passive'], P[no][IDX[k][:2]]['without'])
g_s_paper = lambda rid, no, k: red(P[no][IDX[k][:2]]['s_tlcd'], P[no][IDX[k][:2]]['without'])
def g_repro(dt):
    return lambda rid, no, k: red(PR[(rid, dt, 'R')][IDX[k][2]], PR[(rid, dt, 'U')][IDX[k][2]])
summ = []
def add(name, getter, note):
    m = mean_red(getter); e = ev_equal(getter)
    row = dict(case=name, subset='원문 공통 8쌍 (표 2의 1,2,3,4,11,13,14,15)', note=note)
    for nm in NAMES: row[f'paper_mean_{nm}'] = round(m[nm], 2)
    row['paper_mean_6idx'] = round(float(np.mean(list(m.values()))), 2); row['event_equal_6idx'] = round(float(np.mean(e)), 2)
    summ.append(row)
add('원문 RS-TLCD (표 4-6의 8쌍 값)', g_paper, '원문 표 4-6에서 같은 8쌍만 뽑아 계산')
add('원문 수동 TLCD (같은 8쌍)', g_u_paper_passive, '참고')
add('원문 S-TLCD (같은 8쌍)', g_s_paper, '참고')
add('현재 R, 운영 시간축 (JC, d_cmd=1)', g_oper, 'AI 비교의 기준 R')
for dt in (0.01, 0.005):
    if all((rid, dt, 'R') in PR for rid in PAIRS):
        add(f'현재 R, 원문 재현 조건(지연 0), dt={dt:g}', g_repro(dt), f'R_repro 출처: {pr_src}')
# 참고: 원문 15쌍 평균(표 7), 직접 비교 금지
t7 = {'RS-TLCD': [15.48, 13.74, 11.50, 38.03, 18.00, 16.03], 'S-TLCD': [13.29, 10.40, 9.52, 33.46, 16.81, 13.06], '수동 TLCD': [15.39, 11.45, 9.85, 33.54, 14.33, 11.43]}
order7 = [0, 2, 4, 1, 3, 5]   # 표 7 열 순서(X max, Y max, θ max, X RMS, Y RMS, θ RMS) → NAMES 순서
for case, v in t7.items():
    row = dict(case=f'[참고] 원문 표 7 {case}, 15쌍 평균', subset='원문 15쌍 전체 (현재 8쌍과 직접 비교하지 않음)', note='원문 표 7 인쇄값')
    vv = [v[0], v[3], v[1], v[4], v[2], v[5]]
    for nm, x in zip(NAMES, vv): row[f'paper_mean_{nm}'] = x
    row['paper_mean_6idx'] = round(float(np.mean(vv)), 2); row['event_equal_6idx'] = ''
    summ.append(row)
w(os.path.join(HERE, 'reproduction_summary.csv'), summ)

# ---------------- matched_R_AI_metrics.csv ----------------
METHODS = ['U', 'R', 'J-zero', 'J-persistence', 'J-AIF', 'J-AI', 'C1J-AI', 'J-PREVIEW']
mrows = []
for rid in ORDER:
    grp = 'A 원문 공통' if rid in PAIRS else 'B 개발 추가'
    for m in METHODS:
        d = JC[(rid, m)]; u = JC[(rid, 'U')]; r0 = JC[(rid, 'R')]
        x = dict(group=grp, record_id=rid, event=EVENT[rid], timing='고정 시간축(JC)', method=m)
        for (c, s, key, f, unit), nm in zip(IDX, NAMES): x[f'abs_{nm}_{unit}'] = round(d[key] * f, 4)
        rd = [red(d[k[2]], u[k[2]]) for k in IDX]; rr = [red(r0[k[2]], u[k[2]]) for k in IDX]
        for nm, v in zip(NAMES, rd): x[f'red_{nm}_pct'] = round(v, 3)
        x['mean6_pct'] = round(float(np.mean(rd)), 3)
        for nm, a, b in zip(NAMES, rd, rr): x[f'delta_vs_R_{nm}_pp'] = round(a - b, 3)
        x['delta_vs_R_mean6_pp'] = round(float(np.mean(rd) - np.mean(rr)), 3)
        thm, thr = rd[4] - rr[4], rd[5] - rr[5]
        x['torsion_max_margin_pp'] = round(thm, 3); x['torsion_rms_margin_pp'] = round(thr, 3)
        x['torsion_violation'] = '' if m in ('U', 'R') else ('예' if (thm < -TOL or thr < -TOL) else '아니오')
        mrows.append(x)
ACT = [('실측 지연 1차(JC, 개발 3기록)', 'control_metrics_record_JC_actual.csv'), ('실측 지연 2차(JCA, 11기록)', 'control_metrics_record_JC_actual_all_actualall.csv')]
for tlabel, fname in ACT:
    f = os.path.join(RES, fname)
    if not os.path.exists(f): continue
    A = {(r['record_id'], r['method']): {k: float(r[k]) for k in ('ux_max', 'ux_rms', 'uy_max', 'uy_rms', 'th_max', 'th_rms')} for r in readcsv(f)}
    for rid in ORDER:
        if (rid, 'J-AI') not in A: continue
        u = A[(rid, 'U')]; r0 = A[(rid, 'R')]; d = A[(rid, 'J-AI')]
        x = dict(group='A 원문 공통' if rid in PAIRS else 'B 개발 추가', record_id=rid, event=EVENT[rid], timing=tlabel, method='J-AI')
        for (c, s_, key, ff, unit), nm in zip(IDX, NAMES): x[f'abs_{nm}_{unit}'] = round(d[key] * ff, 4)
        rd = [red(d[k[2]], u[k[2]]) for k in IDX]; rr = [red(r0[k[2]], u[k[2]]) for k in IDX]
        for nm, v in zip(NAMES, rd): x[f'red_{nm}_pct'] = round(v, 3)
        x['mean6_pct'] = round(float(np.mean(rd)), 3)
        for nm, a_, b_ in zip(NAMES, rd, rr): x[f'delta_vs_R_{nm}_pp'] = round(a_ - b_, 3)
        x['delta_vs_R_mean6_pp'] = round(float(np.mean(rd) - np.mean(rr)), 3)
        x['torsion_max_margin_pp'] = round(rd[4] - rr[4], 3); x['torsion_rms_margin_pp'] = round(rd[5] - rr[5], 3)
        x['torsion_violation'] = '예' if (rd[4] - rr[4] < -TOL or rd[5] - rr[5] < -TOL) else '아니오'
        mrows.append(x)
        xr = dict(group=x['group'], record_id=rid, event=EVENT[rid], timing=tlabel, method='R')
        for (c, s_, key, ff, unit), nm in zip(IDX, NAMES): xr[f'abs_{nm}_{unit}'] = round(r0[key] * ff, 4)
        for nm, v in zip(NAMES, rr): xr[f'red_{nm}_pct'] = round(v, 3)
        xr['mean6_pct'] = round(float(np.mean(rr)), 3); xr['torsion_violation'] = ''
        mrows.append(xr)
fields = list(dict.fromkeys(k for r in mrows for k in r))
w(os.path.join(HERE, 'matched_R_AI_metrics.csv'), mrows, fields)

# ---------------- matched_R_AI_summary.csv ----------------
def cell(sel_rids, method, timing='고정 시간축(JC)'):
    rows_ = [r for r in mrows if r['method'] == method and r['timing'] == timing and r['record_id'] in sel_rids]
    return rows_
DEV3 = ['PEER14', 'ElCentro_1940', 'Pohang_2017_BUS2']   # 개발 3사건(고베·El Centro·포항)
SETS = {'A 원문 공통 8쌍 (4사건)': list(PAIRS), 'A+B 개발 11기록 (7사건, 확대 평가)': ORDER, 'B 개발 추가 3기록': [r for r in ORDER if r not in PAIRS], '개발 3사건 (고베·El Centro·포항)': DEV3}
ssum = []
for timing in ['고정 시간축(JC)'] + [t for t, _ in ACT]:
  sets = SETS if timing.startswith('고정') else ({'A 원문 공통 8쌍 (4사건)': list(PAIRS), 'A+B 개발 11기록 (7사건, 확대 평가)': ORDER, '개발 3사건 (고베·El Centro·포항)': DEV3} if '2차' in timing else {'개발 3사건 (고베·El Centro·포항)': DEV3})
  for sname, rids in sets.items():
    for m in (METHODS[1:] if timing.startswith('고정') else ['J-AI']):
        rs = cell(rids, m, timing)
        if len(rs) != len(rids): continue
        rrs = cell(rids, 'R', timing)
        pm = [float(np.mean([r[f'red_{nm}_pct'] for r in rs])) for nm in NAMES]; pr_ = [float(np.mean([r[f'red_{nm}_pct'] for r in rrs])) for nm in NAMES]
        byev = collections.defaultdict(list); byev_r = collections.defaultdict(list)
        for r, r0 in zip(rs, rrs):
            byev[r['event']].append([r[f'red_{nm}_pct'] for nm in NAMES]); byev_r[r0['event']].append([r0[f'red_{nm}_pct'] for nm in NAMES])
        em = np.mean([np.mean(v, axis=0) for v in byev.values()], axis=0); em_r = np.mean([np.mean(v, axis=0) for v in byev_r.values()], axis=0)
        evd = {e: np.mean(byev[e], axis=0) - np.mean(byev_r[e], axis=0) for e in byev}
        ev_viol = [e for e, v in evd.items() if v[4] < -TOL or v[5] < -TOL]
        rec_viol = [r['record_id'] for r in rs if r['torsion_violation'] == '예']
        x = dict(subset=sname, method=m, n_records=len(rs), n_events=len(byev), timing=timing)
        for nm, a, b in zip(NAMES, pm, pr_): x[f'paper_mean_delta_{nm}_pp'] = round(a - b, 2)
        x['paper_mean_6idx_pct'] = round(float(np.mean(pm)), 2); x['R_paper_mean_6idx_pct'] = round(float(np.mean(pr_)), 2)
        x['paper_mean_delta_6idx_pp'] = round(float(np.mean(pm) - np.mean(pr_)), 2)
        x['event_equal_6idx_pct'] = round(float(np.mean(em)), 2); x['R_event_equal_6idx_pct'] = round(float(np.mean(em_r)), 2)
        x['event_equal_delta_pp'] = round(float(np.mean(em) - np.mean(em_r)), 2)
        x['n_events_better'] = sum(1 for e in evd if np.mean(evd[e]) > 1e-9); x['n_events_worse'] = sum(1 for e in evd if np.mean(evd[e]) < -1e-9)
        ev_any = sorted({r['event'] for r in rs if r['torsion_violation'] == '예'}, key=lambda e: list(byev).index(e))
        x['torsion_violation_events'] = len(ev_any); x['torsion_violation_event_names'] = ';'.join(ev_any)          # 주 집계: 위반 기록이 하나라도 있는 사건
        x['torsion_violation_records'] = len(rec_viol); x['torsion_violation_record_names'] = ';'.join(rec_viol)
        x['aux_torsion_violation_events_by_event_mean'] = len(ev_viol); x['aux_torsion_violation_event_mean_names'] = ';'.join(ev_viol)   # 보조: 사건 평균 저감률 기준
        x['worst_torsion_event_mean_pp'] = round(float(min([0.0] + [min(v[4], v[5]) for v in evd.values()])), 2)
        x['worst_torsion_record_pp'] = round(float(min([0.0] + [min(r['torsion_max_margin_pp'], r['torsion_rms_margin_pp']) for r in rs])), 2)
        ssum.append(x)
w(os.path.join(HERE, 'matched_R_AI_summary.csv'), ssum)

# ---------------- 화면 요약 ----------------
print('R 재현 출처:', pr_src)
for r in summ: print(f"{r['case'][:46]:46s}", ' '.join(f"{r.get(f'paper_mean_{nm}', '')!s:>6}" for nm in NAMES), '| 6idx', r['paper_mean_6idx'], '| ev', r['event_equal_6idx'])
print()
for r in ssum:
    if r['method'] in ('J-AI', 'J-zero', 'J-persistence', 'C1J-AI', 'J-AIF', 'J-PREVIEW'):
        print(f"{r['subset'][:22]:22s} {r['method']:14s} paperΔ {r['paper_mean_delta_6idx_pp']:+.2f} eventΔ {r['event_equal_delta_pp']:+.2f} better/worse {r['n_events_better']}/{r['n_events_worse']} torsion ev(any-record) {r['torsion_violation_events']} [{r['torsion_violation_event_names']}] ev(mean) {r['aux_torsion_violation_events_by_event_mean']} rec {r['torsion_violation_records']} worst {r['worst_torsion_event_mean_pp']:+.2f}/{r['worst_torsion_record_pp']:+.2f}  [{r['torsion_violation_event_names']}]")
