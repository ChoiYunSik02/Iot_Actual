# -*- coding: utf-8 -*-
"""응답 기반 전환 규칙 (2026-10-22): 평소값(F0, 0°)으로 대기하다 '인과적 규칙'이 발동하는 순간 (f, θ)로 한 번 전환.
규칙은 지반가속도(기초 가속도계)의 과거 값만 쓴다 — 미래 정보 없음.
  pre    처음부터 (f, θ) 고정                      (기준)
  T{d}   트리거(0.5 gal) + d초                     (exp_switch 확장: 8 12 16 24)
  D{d}   강진동 시작(지금까지 최대 가속도 ≥ 0.1 m/s²) + d초  (2 5 8 12)
  A{τ}   강진동 시작 뒤, 지금까지의 최대 가속도가 τ초 동안 갱신 안 되면 (1 2 3 5)
  B{β}   강진동 시작 뒤, 최근 2 s 평균제곱 가속도가 지금까지 최대의 β배 아래로 떨어지면 (50 30 15 = 0.5 0.3 0.15)
강진동 시작 문턱 0.1 m/s²는 원문 입력 정규화(35 cm/s²)의 약 30% — 설계 지진 크기를 안다는 가정.
사용: python exp_switch2.py [--kscale 1.0] [--workers 16] [--nrec 11] [--quick] [--rules pre T8 A2 ...]
결과: results/exp_switch2_cos2.json  →  python analyze_switch2.py
"""
import argparse, json, os, time
from multiprocessing import Pool
import numpy as np
import rstlcd_cos2 as R
from gen_labels_v2 import DT, F_GRID, TH_GRID, F_RANGE
from exp_switch import test_records, trig_t, sim

ONSET = 0.1            # [m/s²]
ALL = ['pre', 'T8', 'T12', 'T16', 'T24', 'D2', 'D5', 'D8', 'D12', 'A1', 'A2', 'A3', 'A5', 'B50', 'B30', 'B15']


def switch_times(x, y, dt=DT):
    """규칙별 전환 시점 [s]. None = 처음부터 고정(pre), inf = 규칙이 끝까지 발동 안 함(대기 상태로 끝남)."""
    a = np.hypot(x, y); n = len(a); idx = np.arange(n)
    t_trig = trig_t(x, y); out = {'pre': None}
    for d in (8, 12, 16, 24): out[f'T{d}'] = t_trig + d
    pk = np.maximum.accumulate(a); on = np.flatnonzero(pk >= ONSET)
    if len(on) == 0:
        return {k: (v if k in ('pre',) or k.startswith('T') else np.inf) for k, v in out.items()} | {k: np.inf for k in ALL if k not in out}
    on = int(on[0]); t_on = on * dt
    for d in (2, 5, 8, 12): out[f'D{d}'] = t_on + d
    upd = np.r_[True, pk[1:] > pk[:-1]]; last = np.maximum.accumulate(np.where(upd, idx, 0)); since = (idx - last) * dt
    for tau in (1, 2, 3, 5):
        h = np.flatnonzero((idx >= on) & (since >= tau)); out[f'A{tau}'] = h[0] * dt if len(h) else np.inf
    W = int(2 / dt); cs = np.cumsum(a ** 2); e = (cs - np.r_[np.zeros(W), cs[:-W]]) / W; em = np.maximum.accumulate(e)
    for nm, b in (('B50', .5), ('B30', .3), ('B15', .15)):
        h = np.flatnonzero((idx >= on) & (e < b * em)); out[nm] = h[0] * dt if len(h) else np.inf
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kscale', type=float, default=1.0)
    ap.add_argument('--nrec', type=int, default=11)
    ap.add_argument('--rules', nargs='+', default=ALL)
    ap.add_argument('--quick', action='store_true', help='시험용: 칸 9개(3×3)만')
    ap.add_argument('--workers', type=int, default=max(1, os.cpu_count() - 1))
    args = ap.parse_args()
    recs = test_records()[:args.nrec]; k = args.kscale
    fi = [0, 3, 6] if args.quick else list(range(len(F_GRID))); ti = [0, 3, 6] if args.quick else list(range(len(TH_GRID)))
    st = [switch_times(x, y) for _, x, y in recs]
    jobs = []
    for r, (name, x, y) in enumerate(recs):
        jobs.append(((r, 'E0', 0, 0), x, y, dict(case='none', k_scale=k)))
        for rule in args.rules:
            for a in fi:
                for b in ti:
                    f, th = float(F_GRID[a]), float(TH_GRID[b]); ts = st[r][rule]
                    kw = dict(case='rstlcd', k_scale=k)
                    if ts is None: kw.update(f0=f, theta0=th, cmd=(1e9, f, th))
                    else: kw.update(cmd=(1e9 if not np.isfinite(ts) else ts, f, th))
                    jobs.append(((r, rule, a, b), x, y, kw))
    t0 = time.time()
    with Pool(args.workers) as pool:
        res = dict(pool.map(sim, jobs, chunksize=4))
    print(f'{len(jobs)}회 {time.time() - t0:.0f}s')
    S = np.full((len(recs), len(args.rules), len(F_GRID), len(TH_GRID)), np.nan)
    for r in range(len(recs)):
        b0 = res[(r, 'E0', 0, 0)]
        for i, rule in enumerate(args.rules):
            for a in fi:
                for b in ti:
                    S[r, i, a, b] = np.mean(list(R.reduction(res[(r, rule, a, b)], b0).values()))
    os.makedirs('results', exist_ok=True)
    json.dump(dict(k_scale=k, rules=args.rules, records=[r_[0] for r_ in recs],
                   switch_times=[{kk: (None if v is None else (None if not np.isfinite(v) else float(v))) for kk, v in s.items()} for s in st],
                   S=np.where(np.isnan(S), None, S).tolist()),
              open('results/exp_switch2_cos2.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('저장: results/exp_switch2_cos2.json  →  python analyze_switch2.py')
