# -*- coding: utf-8 -*-
"""교수님 피드백 점검: 유입 진동수(입력 지진의 스펙트럼 특성)가 최선 감쇠기 진동수를 결정하는가?
상수 설정 7x7 점수(exp_switch_cos2.json, S[:,'pre'])에서 기록별 최선 f와 입력 특성의 순위상관."""
import json, numpy as np, records as R
d = json.load(open('results/exp_switch_cos2.json', encoding='utf-8'))
S = np.array(d['S'])[:, 0]                     # (11, f7, theta7), 상수 설정
recs = d['records']
P, _ = R.paper_pairs(); H = R.held_pairs()
acc = {f'PEER {n} {s}': (x, y) for n, s, x, y in P}; acc.update({n: (x, y) for n, x, y in H})
f_grid = np.linspace(0.3204, 0.3542, 7)
def feats(x, y, dt=0.01):
    f = np.fft.rfftfreq(len(x), dt); A = np.sqrt(np.abs(np.fft.rfft(x))**2 + np.abs(np.fft.rfft(y))**2)
    out = {}
    m = (f >= 0.1) & (f <= 5); out['dominant f (0.1-5 Hz)'] = f[m][A[m].argmax()]
    out['spectral centroid (0.1-5 Hz)'] = (f[m]*A[m]).sum()/A[m].sum()
    b = (f >= 0.25) & (f <= 0.45); out['energy 0.25-0.45 Hz / 0.1-5 Hz'] = (A[b]**2).sum()/(A[m]**2).sum()
    return out
rows = []
for i, nm in enumerate(recs):
    x, y = acc[nm]; ft = feats(x, y)
    bi = np.unravel_index(S[i].argmax(), S[i].shape)
    ft['best f'] = f_grid[bi[0]]; ft['best theta'] = bi[1]*15; ft['gain over worst f (same theta)'] = S[i][:, bi[1]].max()-S[i][:, bi[1]].min()
    rows.append((nm, ft))
def rank(v):
    v=np.asarray(v,float); o=np.argsort(v,kind='mergesort'); r=np.empty(len(v)); i=0
    while i<len(v):
        j=i
        while j+1<len(v) and v[o[j+1]]==v[o[i]]: j+=1
        r[o[i:j+1]]=(i+j)/2; i=j+1
    return r
print('| Record | best f (Hz) | best theta | dominant f | centroid | E(0.25-0.45)/E | spread over f at best theta |')
print('|---|---|---|---|---|---|---|')
for nm, ft in rows:
    print(f"| {nm} | {ft['best f']:.4f} | {ft['best theta']} | {ft['dominant f (0.1-5 Hz)']:.2f} | {ft['spectral centroid (0.1-5 Hz)']:.2f} | {ft['energy 0.25-0.45 Hz / 0.1-5 Hz']:.3f} | {ft['gain over worst f (same theta)']:.2f} |")
bf = np.array([r[1]['best f'] for r in rows])
print()
for k in ('dominant f (0.1-5 Hz)', 'spectral centroid (0.1-5 Hz)', 'energy 0.25-0.45 Hz / 0.1-5 Hz'):
    v = np.array([r[1][k] for r in rows]); rho = np.corrcoef(rank(v), rank(bf))[0, 1]
    print(f'Spearman rho(best f, {k}) = {rho:+.2f}  (n=11)')
sp = np.array([r[1]['gain over worst f (same theta)'] for r in rows])
print(f'frequency spread at the best angle: mean {sp.mean():.2f} points, max {sp.max():.2f} (cf. angle: Fig. 5b)')

# 사건 단위 (Imperial Valley 5개 = 1건, 특성은 평균): 독립 7건
grp={}
for i,(nm,ft) in enumerate(rows):
    k='IV' if nm.startswith('PEER') and int(nm.split()[1]) in (1,2,3,4,11) else nm
    grp.setdefault(k,[]).append(i)
print('\n사건 단위 (n=7):')
for k in ('dominant f (0.1-5 Hz)','spectral centroid (0.1-5 Hz)','energy 0.25-0.45 Hz / 0.1-5 Hz'):
    v=np.array([np.mean([rows[i][1][k] for i in g]) for g in grp.values()]); b=np.array([np.mean([rows[i][1]['best f'] for i in g]) for g in grp.values()])
    print(f'Spearman rho(best f, {k}) = {np.corrcoef(rank(v),rank(b))[0,1]:+.2f}  (n=7)')
