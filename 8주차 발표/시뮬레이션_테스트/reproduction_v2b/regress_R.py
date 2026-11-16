"""지연 0 R 회귀 확인. 사전 기준(실행 전 고정): 시간 이력 최대 절대차 <=1e-12(응답 단위), 결정 기록 개수·스텝·κ 완전 일치, 진동수·각도 지령 차이 <=1e-12, 상태 로그 열 차이 <=1e-12."""
import numpy as np, time, json
from rs_ref import Plant, run
from sim_layer import simulate, RPolicy
from tlcd import load_records, metrics
R=load_records(); plants={}; rows=[]; ok=True; ndec=0
for j,(ax,ay,dt) in enumerate(R):
    if dt not in plants: plants[dt]=Plant(dt)
    y0,d0,s0,_=run(plants[dt],ax,ay,'A')
    y1,d1,s1=simulate(plants[dt],ax,ay,RPolicy(dt,'A'))
    dy=float(np.abs(y0-y1).max()); m0=metrics(y0); m1=metrics(y1); dm=float(np.max(np.abs(m0-m1)/np.abs(m0)))
    same_n=len(d0)==len(d1); dd=0.0; kap_ok=True; step_ok=True
    if same_n:
        for a,b in zip(d0,d1):
            step_ok&=(a[0]==b[0] and a[1]==b[1]); dd=max(dd,max(abs(a[3]-b[3]),abs(a[4]-b[4]) if a[0]==1 else 0))
            if a[0]==2: kap_ok&=(a[3]==b[3])
    ds=float(np.abs(np.array(s0)-np.array(s1)).max()) if len(s0)==len(s1) else np.inf
    good=same_n and step_ok and kap_ok and dy<=1e-12 and dd<=1e-12 and ds<=1e-12; ok&=good; ndec+=len(d0)
    rows.append(dict(rec=j+1,resp_max_abs=dy,metric_max_rel=dm,n_dec=len(d0),n_dec_same=same_n,dec_cmd_max=dd,kappa_same=kap_ok,state_max=ds,pass_=good))
    print(rows[-1],flush=True)
# MATLAB A 지표와 비교(전이적 확인)
import csv
mat=np.genfromtxt('matlab_rs_A_metrics.csv',delimiter=',',skip_header=1)[:,1:]
py=np.load('rsref_A_metrics.npy'); print('rsref vs MATLAB max rel',float(np.max(np.abs(py-mat)/np.abs(mat))))
json.dump(dict(rows=rows,all_pass=bool(ok),n_decisions=ndec),open('regress_R_result.json','w'),indent=1)
print('ALL_PASS',ok,'decisions',ndec)
