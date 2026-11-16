import sys, numpy as np, multiprocessing as mp
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
def work(seed):
    rng=np.random.default_rng(seed)
    tp=rng.uniform(0.8,1.6); a=rng.uniform(0.3,1.5); nc=int(rng.integers(3,7))
    n=int(nc*tp/DT); ag=np.zeros(NSTEP); t=np.arange(n)*DT
    ag[:n]=a*G*np.sin(2*np.pi*t/tp)*np.sin(np.pi*t/(n*DT))**0.5
    fs=rng.uniform(0.95,1.02); bld=rng.random()<0.5
    sc=dict(ag=ag,F=np.zeros(NSTEP),jf=5,fscale=fs,fscale2=fs*0.85 if bld else fs,t_sw=1.5,zeta=rng.uniform(0.01,0.03),info=dict(Tp=tp,A=a,B=bld))
    p=mkpack(sc,rng); J=[];Y=[]
    for u in U_GRID:
        mt=metrics(p,run(p,1,u)); J.append(mt['J']); Y.append(mt['ystroke'])
    return J,Y,a,nc
if __name__=='__main__':
    with mp.Pool(2) as pl: R=pl.map(work,range(300,500))
    J=np.array([r[0] for r in R]);Y=np.array([r[1] for r in R]);A=np.array([r[2] for r in R])
    print('overflow%',(Y>1).mean(0).round(3)); print('stroke',Y.mean(0).round(2)); print('J',J.mean(0).round(3)); print('oracle',J.min(1).mean().round(3))
    m=A>1.0; print('A>1g n',m.sum(),'overflow%',(Y[m]>1).mean(0).round(2),'stroke',Y[m].mean(0).round(2))
