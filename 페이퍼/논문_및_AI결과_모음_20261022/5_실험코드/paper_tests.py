# -*- coding: utf-8 -*-
"""논문 결론의 견고성 시험 (2026-10-22). 학습 없이 시뮬레이션만 — 사전 고정 동조 vs 원문 RS (+ Oracle).
  T1 회전 법칙 3종 (A: cos 한 번 · B: 원문식 · C: 질량 보존)  × 감쇠 배율 30
  T2 감쇠 배율 20 · 30 · 40  (법칙 B)
  T3 장치 조정 범위 ±5% · ±20%  (법칙 B)
  T4 초반 구간 효과: 원문이 지적한 '처음 약 8 s' — 트리거 후 8 s · 강진동 시작(Arias 5%) 후 8 s의 최상층 최대 변위 저감
각 조건에서: E1b 수동 디튜닝(0.3204 Hz) · E2 원문 RS · 고정값(같은 지진을 뺀 교차검증으로 고른 칸) · 고정값(사후, 11기록에서 최선) · Oracle.
고정값 선택은 실제 기록의 칸별 점수만 씀 (합성 라벨 불필요). 사건 7개 (Imperial Valley 1979 기록 5개는 한 묶음), 평균 ± SE는 사건 단위.
사용: python paper_tests.py [--workers 16] [--quick] [--nrec 11]
결과: results/paper_tests_cos2.json (+ 표 출력)
"""
import argparse, importlib, json, os, time
from multiprocessing import Pool
import numpy as np
import records
import rstlcd as R0
from exp_switch import trig_t

DT = 0.01
MODS = {'A': 'rstlcd', 'B': 'rstlcd_cos2', 'C': 'rstlcd_masscons'}
F_NOM = R0.F_RANGE


def test_records():
    return [(f'PEER {no} {st}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)


def sim(job):
    """job = (key, law, cs, case, x, y, f_range, f, th, series). 반환: key, 지표 또는 시계열."""
    key, law, cs, case, x, y, fr, f, th, series = job
    R = importlib.import_module(MODS[law])
    kw = dict(case=case, c_scale=cs)
    if case == 'passive': kw['f0'] = 0.3204
    if case == 'rstlcd':
        kw['f_range'] = fr
        if f is not None: kw.update(f0=f, theta0=th, rs_freq=lambda t, s: f, rs_theta=lambda t, s: th)
    out = R.simulate(x, y, DT, **kw)
    return key, (out if series else R.metrics(out))


def red_mean(R, m, b0):
    return float(np.mean(list(R.reduction(m, b0).values())))


def events_of(names):
    ev = {}
    for i, nm in enumerate(names):
        k = 'IV1979' if (nm.startswith('PEER') and int(nm.split()[1]) in (1, 2, 3, 4, 11)) else nm
        ev.setdefault(k, []).append(i)
    return list(ev.values())


def summarize(S, e2, e1b, names, label):
    """S[r, a, b] 칸별 점수, e2[r], e1b[r] → 교차검증 고정값 · 사후 고정값 · Oracle 표 한 줄."""
    n = len(names); ev = events_of(names); flat = S.reshape(n, -1)
    cv = np.zeros(n)
    for e in ev:
        tr = [i for i in range(n) if i not in e]
        c = flat[tr].mean(0).argmax() if tr else flat.mean(0).argmax()
        for r in e: cv[r] = flat[r, c]
    ph = flat.mean(0).max(); orc = flat.max(1)
    d = np.array([np.mean([(cv - e2)[r] for r in e]) for e in ev]); se = d.std(ddof=1) / np.sqrt(len(ev)) if len(ev) > 1 else float('nan')
    row = dict(label=label, E1b=float(e1b.mean()), E2=float(e2.mean()), fixed_cv=float(cv.mean()), fixed_posthoc=float(ph), oracle=float(orc.mean()),
               fixed_minus_E2_event_mean=float(d.mean()), fixed_minus_E2_event_se=float(se), events_improved=int((d > 0).sum()), n_events=len(ev),
               best_cell_posthoc=[int(v) for v in np.unravel_index(flat.mean(0).argmax(), S.shape[1:])])
    print(f'{label:30s} E1b {row["E1b"]:6.2f}  E2 {row["E2"]:6.2f}  고정(CV) {row["fixed_cv"]:6.2f}  고정(사후) {ph:6.2f}  Oracle {orc.mean():6.2f} | 고정(CV)−E2 {d.mean():+5.2f} ± {se:4.2f} ({row["events_improved"]}/{len(ev)})', flush=True)
    return row, cv


def run_cond(pool, recs, law, cs, f_range, nf, ti, e2_cache=None, extra_series=False):
    """한 조건의 E0 · E1b · E2 + 칸 격자 → S, e2, e1b."""
    F = np.linspace(*f_range, nf); TH = np.deg2rad(np.linspace(0, 90, 7)); n = len(recs); jobs = []
    for r, (nm, x, y) in enumerate(recs):
        jobs += [((r, 'E0'), law, cs, 'none', x, y, F_NOM, None, None, False), ((r, 'E1b'), law, cs, 'passive', x, y, F_NOM, None, None, False),
                 ((r, 'E2'), law, cs, 'rstlcd', x, y, F_NOM, None, None, False)]
        jobs += [((r, 'G', a, b), law, cs, 'rstlcd', x, y, f_range, float(F[a]), float(TH[b]), False) for a in range(nf) for b in ti]
    res = dict(pool.map(sim, jobs, chunksize=4)); R = importlib.import_module(MODS[law])
    S = np.full((n, nf, 7), np.nan); e2 = np.zeros(n); e1b = np.zeros(n)
    for r in range(n):
        b0 = res[(r, 'E0')]; e2[r] = red_mean(R, res[(r, 'E2')], b0); e1b[r] = red_mean(R, res[(r, 'E1b')], b0)
        for a in range(nf):
            for b in ti: S[r, a, b] = red_mean(R, res[(r, 'G', a, b)], b0)
    return S[:, :, ti], e2, e1b, F, TH[ti]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    ap.add_argument('--nrec', type=int, default=11)
    ap.add_argument('--quick', action='store_true', help='시험용: 격자 f 3 × θ 3 (±20%는 f 5)')
    args = ap.parse_args()
    recs = test_records()[:args.nrec]; names = [r[0] for r in recs]
    nf5, nf20 = (3, 5) if args.quick else (7, 13); ti = [0, 3, 6] if args.quick else list(range(7))
    out = dict(names=names, rows=[]); t0 = time.time()
    with Pool(args.workers) as pool:
        print('T1 회전 법칙 (감쇠 ×30, ±5%)')
        for law, lab in (('A', 'A cos 한 번 (v0)'), ('B', 'B 원문식 (채택)'), ('C', 'C 질량 보존 cos²')):
            S, e2, e1b, F, TH = run_cond(pool, recs, law, 30.0, F_NOM, nf5, ti)
            row, _ = summarize(S, e2, e1b, names, 'T1 ' + lab); row.update(test='T1', law=law, cs=30.0, S=S.tolist()); out['rows'].append(row)
        print('\nT2 감쇠 배율 (원문식, ±5%)')
        for cs in (20.0, 40.0):
            S, e2, e1b, F, TH = run_cond(pool, recs, 'B', cs, F_NOM, nf5, ti)
            row, _ = summarize(S, e2, e1b, names, f'T2 감쇠 ×{cs:g}'); row.update(test='T2', law='B', cs=cs, S=S.tolist()); out['rows'].append(row)
        print('\nT3 조정 범위 ±20% (원문식, 감쇠 ×30; E2는 원문 장치 ±5% 그대로)')
        S, e2, e1b, F, TH = run_cond(pool, recs, 'B', 30.0, (R0.F0 * 0.8, R0.F0 * 1.2), nf20, ti)
        row, _ = summarize(S, e2, e1b, names, 'T3 조정 범위 ±20%'); row.update(test='T3', law='B', cs=30.0, S=S.tolist()); out['rows'].append(row)
        # T4 초반 구간 — 원문식 · 감쇠 ×30 · ±5%에서 교차검증으로 고른 고정칸
        print('\nT4 초반 구간 최상층 최대 변위 저감 [%] (X · Y 평균), 원문식·감쇠 ×30')
        base = next(r_ for r_ in out['rows'] if r_['test'] == 'T1' and r_['law'] == 'B')
        S5 = np.array(base['S']); n = len(recs); ev = events_of(names); flat = S5.reshape(n, -1); F = np.linspace(*F_NOM, nf5); TH = np.deg2rad(np.linspace(0, 90, 7))[ti]
        cell = {}
        for e in ev:
            tr = [i for i in range(n) if i not in e]; c = flat[tr].mean(0).argmax() if tr else flat.mean(0).argmax()
            for r in e: cell[r] = np.unravel_index(c, S5.shape[1:])
        jobs = []
        for r, (nm, x, y) in enumerate(recs):
            a, b = cell[r]
            jobs += [((r, 'E0'), 'B', 30.0, 'none', x, y, F_NOM, None, None, True), ((r, 'E1'), 'B', 30.0, 'passive', x, y, F_NOM, None, None, True),
                     ((r, 'E2'), 'B', 30.0, 'rstlcd', x, y, F_NOM, None, None, True), ((r, 'FX'), 'B', 30.0, 'rstlcd', x, y, F_NOM, float(F[a]), float(TH[b]), True)]
        res = dict(pool.map(sim, jobs, chunksize=2)); w8 = int(8 / DT); t4 = {k: {'trig': [], 'onset': []} for k in ('E1', 'E2', 'FX')}
        for r, (nm, x, y) in enumerate(recs):
            i0 = int(round(trig_t(x, y) / DT)); ar = np.cumsum(x ** 2 + y ** 2); i1 = int(np.searchsorted(ar / ar[-1], 0.05))
            for k in t4:
                for tag, i in (('trig', i0), ('onset', i1)):
                    pk = lambda o: 0.5 * (np.abs(o['ux'][i:i + w8]).max() + np.abs(o['uy'][i:i + w8]).max())
                    t4[k][tag].append(100 * (1 - pk(res[(r, k)]) / pk(res[(r, 'E0')])))
        for tag, lab in (('trig', '트리거 후 8 s'), ('onset', '강진동 시작(Arias 5%) 후 8 s')):
            m = {k: float(np.mean(v[tag])) for k, v in t4.items()}
            print(f'{lab:28s} 수동 {m["E1"]:6.2f}  원문 RS {m["E2"]:6.2f}  고정값 {m["FX"]:6.2f}')
            out['rows'].append(dict(test='T4', window=tag, mean=m, per_record={k: v[tag] for k, v in t4.items()}))
    os.makedirs('results', exist_ok=True)
    json.dump(out, open('results/paper_tests_cos2.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'\n{time.time() - t0:.0f}s 저장: results/paper_tests_cos2.json')
