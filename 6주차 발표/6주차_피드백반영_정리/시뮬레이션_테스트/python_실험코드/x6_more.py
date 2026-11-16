import sys, json, pickle, numpy as np, multiprocessing as mp
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
import x6_real, x6_burst
U=np.array(U_GRID)
def real_job(a):
    name,pga,bld=a; t,x=x6_real.load(x6_real.FILES[name]); x=x-np.mean(x); x=x/np.abs(x).max()*pga*G
    i0=int(np.argmax(np.abs(x)>0.3)); t0=max(t[i0]-0.1,t[0]); tt=np.arange(NSTEP)*DT+t0; ag=np.interp(tt,t,x,right=0.0)
    rng=np.random.default_rng(hash((name,pga,bld))%2**31)
    sc=dict(ag=ag,F=np.zeros(NSTEP),jf=5,fscale=1.0,fscale2=0.85 if bld else 1.0,t_sw=1.5,zeta=0.02,info={})
    p=mkpack(sc,rng); R=[]
    for u in U_GRID:
        mt=metrics(p,run(p,1,u)); R.append([mt['J'],mt['rms'],mt['pk'],mt['ystroke']])
    return name,pga,bld,R
def burst_job(seed):
    rng=np.random.default_rng(seed); tp=rng.uniform(0.8,1.6); a=rng.uniform(0.3,1.5); nc=int(rng.integers(3,7))
    n=int(nc*tp/DT); ag=np.zeros(NSTEP); t=np.arange(n)*DT; ag[:n]=a*G*np.sin(2*np.pi*t/tp)*np.sin(np.pi*t/(n*DT))**0.5
    fs=rng.uniform(0.95,1.02); bld=rng.random()<0.5
    sc=dict(ag=ag,F=np.zeros(NSTEP),jf=5,fscale=fs,fscale2=fs*0.85 if bld else fs,t_sw=1.5,zeta=rng.uniform(0.01,0.03),info={})
    p=mkpack(sc,rng); R=[]
    for u in U_GRID:
        mt=metrics(p,run(p,1,u)); R.append([mt['J'],mt['rms'],mt['pk'],mt['ystroke']])
    return R
def x2_job(a):
    seed,ub=a; rng=np.random.default_rng(seed); sc=gen_pulse(rng); p=mkpack(sc,rng); out=[]
    for d in [0,0.1,0.3,0.5,1,2,3,6]:
        mt=metrics(p,run(p,8,1.0,(float(U[ub]),d,1.0))); out.append([mt['J'],mt['rms'],mt['pk'],mt['ystroke']])
    return out
if __name__=='__main__':
    out={}
    with mp.Pool(2) as pl:
        jobs=[(n,p,b) for n in x6_real.FILES for p in x6_real.PGAS for b in (False,True)]
        out['real']=pl.map(real_job,jobs); print('real')
        out['burst']=pl.map(burst_job,range(300,500)); print('burst')
        R=pickle.load(open('x6_stage1.pkl','rb')); te=range(300,500)
        J=np.array([R[i]['J'] for i in te]); ub=J.argmin(1)
        out['x2']=pl.map(x2_job,[(R[i]['seed'],int(ub[k])) for k,i in enumerate(te)]); print('x2')
    json.dump(out,open('x6_more.json','w'),default=float)
    # summaries
    real=out['real']
    for p in x6_real.PGAS:
        rr=np.array([r[3] for r in real if r[1]==p]); print('real',p,'rms_red xi6',round((1-rr[:,2,1].mean())*100,1),'over',(rr[:,:,3]>1).mean(0).round(2))
    rr=np.array([r[3] for r in real]); print('real ALL xi6 rms_red',round((1-rr[:,2,1].mean())*100,1),'xi12',round((1-rr[:,4,1].mean())*100,1))
    b=np.array(out['burst']); print('burst rms_red',((1-b[:,:,1].mean(0))*100).round(1),'over',(b[:,:,3]>1).mean(0).round(2),'pk_red',((1-b[:,:,2].mean(0))*100).round(1))
    x=np.array(out['x2']); print('x2 rms_red',((1-x[:,:,1].mean(0))*100).round(2),'over',(x[:,:,3]>1).mean(0).round(3),'pk',((1-x[:,:,2].mean(0))*100).round(2))
    s1=np.array([[r['rms'][k] for k in range(7)] for r in R]); print('stage1 rms_red per u',((1-s1.mean(0))*100).round(1))
    # table-known on real
    tot=[];ov=[]
    for p in x6_real.PGAS:
        rr=np.array([r[3] for r in real if r[1]==p]); ok=[k for k in range(7) if (rr[:,k,3]>1).mean()==0]; k=min(ok,key=lambda k:rr[:,k,0].mean())
        tot.append(rr[:,k,1]); ov.append(rr[:,k,3]>1)
    print('real table-known rms_red',round((1-np.concatenate(tot).mean())*100,1),'over',np.concatenate(ov).mean())
