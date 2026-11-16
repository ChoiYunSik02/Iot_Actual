"""MATLAB run_v2b_check.m 결과와 Python v2b 결과 대조.
판정 기준(실행 전 고정, 2026-10-31): 무제어·수동은 18개 지표×15기록 최대 상대차 1e-6 이하,
S-TLCD는 1e-4 이하. 넘으면 불합격으로 보고하고 기준을 바꾸지 않는다."""
import numpy as np, pandas as pd, sys
m=pd.read_csv(sys.argv[1] if len(sys.argv)>1 else 'matlab_v2b_metrics.csv')
py={'unc':np.load('out_unc_zoh_up1.npy'),'pas':np.load('out_passive_up1.npy'),'stl':np.load('out_S_step_up1.npy')}
tol={'unc':1e-6,'pas':1e-6,'stl':1e-4}
cols=['Xmax','Xrms','Ymax','Yrms','thmax','thrms']
for c in ['unc','pas','stl']:
    mm=m[[f'{c}_{s}' for s in cols]].values; d=np.abs(mm/py[c]-1); i,j=np.unravel_index(d.argmax(),d.shape)
    print(f"{c}: 최대 상대차 {d.max():.2e} (기록 {i+1}, {cols[j]})  기준 {tol[c]:.0e}  → {'합격' if d.max()<=tol[c] else '불합격'}")
