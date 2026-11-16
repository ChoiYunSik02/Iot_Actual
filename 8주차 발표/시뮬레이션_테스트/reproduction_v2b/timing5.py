"""5번 기록 처리량 측정(D0·A). 각 항목 시간은 이 컨테이너 CPU 기준(노트북 MATLAB은 별도 측정 필요)."""
import numpy as np, time, json, csv
from rs_ref import Plant
from sim_layer import simulate, RPolicy
from tlcd import load_records, metrics
from stlcd import ident
import rs_ref
R=load_records(); ax,ay,dt=R[4]; T=len(ax); print('rec5 steps',T,'dt',dt,'len s',T*dt)
# (a) 저장된 결과와 일치
pl=Plant(dt); y,dec,st=simulate(pl,ax,ay,RPolicy(dt)); m=metrics(y)
ref=np.load('rsref_A_metrics.npy')[4]; print('metrics rel diff vs stored',float(np.max(abs(m-ref)/abs(ref))))
rows=list(csv.reader(open('py_rs_A_dec.csv')))[1:]; r5=[r for r in rows if r[0]=='5']; print('decisions stored',len(r5),'new',len(dec))
uz=np.load('out_unc_zoh_up1.npy'); print('red6 mean all 15 (stored)', float(((1-np.load('rsref_A_metrics.npy')/uz)*100).mean()))
# (b) 전체 1기록 시간: 차가운 캐시 / 따뜻한 캐시
t=time.perf_counter(); pl=Plant(dt); simulate(pl,ax,ay,RPolicy(dt)); cold=time.perf_counter()-t
ncache=len(pl.cache)
t=time.perf_counter(); simulate(pl,ax,ay,RPolicy(dt)); warm=time.perf_counter()-t
# (c) 구성 요소
t=time.perf_counter(); Ad,Bd=pl.disc(0.3300,np.deg2rad(37.0)); expm_t=time.perf_counter()-t
x=np.random.randn(2*(3*30+2)); u=np.r_[0.1,0.1,0.0,0.0]; t=time.perf_counter()
for _ in range(20000): x=Ad@x*0.999+Bd@u
step_t=(time.perf_counter()-t)/20000
sig=np.random.randn(int(30/dt)); t=time.perf_counter()
for _ in range(5): ident(sig,dt,'morlet')
ident_t=(time.perf_counter()-t)/5
# 점수망 크기 동일(98-128-64-1) 순전파 46후보(무작위 가중치, 시간만 측정)
W1=np.random.randn(98,128);W2=np.random.randn(128,64);W3=np.random.randn(64,1); X=np.random.randn(46,98)
t=time.perf_counter()
for _ in range(2000): h=np.maximum(X@W1,0);h=np.maximum(h@W2,0);o=h@W3
mlp_t=(time.perf_counter()-t)/2000
# (d) 4 s 예측 롤아웃 프로토타입: 같은 상태에서 후보별(f,θ목표,κ) 4 s(=4/dt 스텝). 캐시 미스(expm) 포함/제외
def rollout(plant,x0,fq,tht,kap,h=4.0):
    x=x0.copy(); th=0.0 if False else None
    return None
H=int(round(4.0/dt)); i=rs_ref.IDX; n=3*30+2
def roll(plant,x0,th0,f,tht,kap,gnd=None):
    x=x0.copy(); th=th0; miss0=len(plant.cache); t=time.perf_counter()
    for k in range(H):
        th+=float(np.clip(tht-th,-rs_ref.RATE*dt,rs_ref.RATE*dt))
        fq=np.floor(f*1e5+0.5)/1e5; thq=np.floor(th/rs_ref.QTH+0.5)*rs_ref.QTH; thq=np.floor(thq*1e4+0.5)/1e4
        Ad,Bd=plant.disc(fq,thq); vr=x[[n+i['xd'],n+i['yd']]]-x[[n+i['xt'],n+i['yt']]]
        x=Ad@x+Bd@np.r_[0,0,rs_ref.cdamp(kap)*np.abs(vr)*vr]
    return time.perf_counter()-t,len(plant.cache)-miss0
import copy
rng=np.random.default_rng(0); x0=rng.standard_normal(2*n)*1e-3
pc=Plant(dt); res_cold=[];res_warm=[]
cands=[(f,np.deg2rad(a),k) for f in (0.3204,0.3373,0.3542) for a in (0,22.5,45,67.5,90) for k in (0.1,0.4,0.8)]
for c in cands: res_cold.append(roll(pc,x0,np.deg2rad(10),*c))
for c in cands: res_warm.append(roll(pc,x0,np.deg2rad(10),*c))
cold_t=np.array([r[0] for r in res_cold]); warm_t=np.array([r[0] for r in res_warm]); miss=np.array([r[1] for r in res_cold])
out=dict(rec5_steps=T,dt=dt,sim_cold_s=cold,sim_warm_s=warm,cache_entries_after_run=ncache,expm_s=expm_t,plant_step_s=step_t,
 morlet_ident_30s_s=ident_t,mlp46_forward_s=mlp_t,n_cands=len(cands),H_steps=H,
 rollout_cold_mean_s=float(cold_t.mean()),rollout_warm_mean_s=float(warm_t.mean()),rollout_new_expm_mean=float(miss.mean()),rollout_new_expm_max=int(miss.max()),
 rollout_warm_total_45_s=float(warm_t.sum()),rollout_cold_total_45_s=float(cold_t.sum()))
json.dump(out,open('timing5_result.json','w'),indent=1); print(json.dumps(out,indent=1))
