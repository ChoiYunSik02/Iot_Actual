# -*- coding: utf-8 -*-
"""exp_switch2 결과 분석: 규칙별 (1) 사후 최선 고정칸 평균 (2) 같은 지진을 뺀 교차검증(사건 단위, pre 대비)."""
import json, sys, os
import numpy as np
import records
DT = 0.01
path = sys.argv[1] if len(sys.argv) > 1 else 'results/exp_switch2_cos2.json'
J = json.load(open(path, encoding='utf-8')); rules = J['rules']; names = J['records']; n = len(names)
S = np.array(J['S'], dtype=float)                       # (기록, 규칙, f, θ) — 계산 안 한 칸은 nan
ev = {}
for i, nm in enumerate(names):
    key = 'IV1979' if (nm.startswith('PEER') and int(nm.split()[1]) in (1, 2, 3, 4, 11)) else nm
    ev.setdefault(key, []).append(i)
ev = list(ev.values()); ne = len(ev)
Sf = S.reshape(n, len(rules), -1); cell_ok = ~np.isnan(Sf).any(axis=(0, 1)); Sf = Sf[:, :, cell_ok]


def loeo(rule_idx):
    out = np.zeros(n)
    for e in ev:
        tr = [i for i in range(n) if i not in e]
        if not tr: continue
        m = Sf[tr][:, rule_idx, :].mean(0); ri, ci = np.unravel_index(m.argmax(), m.shape)
        for r in e: out[r] = Sf[r, rule_idx[ri], ci]
    return out


pre_i = rules.index('pre'); base = loeo([pre_i])
print(f'기록 {n}개 · 사건 {ne}개 · 칸 {int(cell_ok.sum())}개 · 규칙 {len(rules)}개')
print('규칙   사후 최선칸 평균   교차검증 평균   pre 대비 (기록단위)   사건단위 ± SE   개선 사건')
rows = []
for i, rule in enumerate(rules):
    post = Sf[:, i, :].mean(0).max(); o = loeo([i]); de = np.array([np.mean([(o - base)[r] for r in e]) for e in ev])
    se = de.std(ddof=1) / np.sqrt(ne) if ne > 1 else float('nan')
    rows.append((rule, post, o.mean(), np.mean(o - base), de.mean(), se, int((de > 0).sum())))
for rule, post, cv, dr, dm, se, w in rows:
    print(f'{rule:5s}  {post:10.2f}        {cv:8.2f}       {dr:+6.2f}            {dm:+6.2f} ± {se:4.2f}      {w}/{ne}')
o_all = loeo(list(range(len(rules)))); de = np.array([np.mean([(o_all - base)[r] for r in e]) for e in ev])
print(f'\n전체 규칙에서 고르기(교차검증): 평균 {o_all.mean():.2f}, pre 대비 사건단위 {de.mean():+.2f} ± {de.std(ddof=1) / np.sqrt(ne):.2f} ({int((de > 0).sum())}/{ne})')
# 전환 시점 vs 강진동 구간
recs = [(f'{no}', x, y) for no, st, x, y in records.paper_pairs(DT)[0]] + records.held_pairs(DT)
print('\n기록별 전환 시점 [s] (자료 시작 기준) — Arias 5~95% 구간과 비교')
best = [r_[0] for r_ in sorted(rows, key=lambda t: -t[4]) if r_[0] != 'pre'][:3]
print('기록'.ljust(26) + 'Arias5~95%'.ljust(14) + ''.join(b.rjust(8) for b in best))
for r in range(n):
    x, y = recs[r][1], recs[r][2]; ar = np.cumsum(x ** 2 + y ** 2); ar /= ar[-1]
    w = f'{np.searchsorted(ar, .05) * DT:.0f}~{np.searchsorted(ar, .95) * DT:.0f}'
    print(names[r][:24].ljust(26) + w.ljust(14) + ''.join(('inf' if J['switch_times'][r][b] is None else f"{J['switch_times'][r][b]:.1f}").rjust(8) for b in best))
