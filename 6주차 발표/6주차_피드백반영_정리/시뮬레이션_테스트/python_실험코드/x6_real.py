import sys, glob, os, numpy as np, json, multiprocessing as mp
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
D=os.environ.get('W5_RECORDS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'matlab', 'w5', 'records')) + os.sep
FILES={'El Centro 1940 (NS)':'elcentro_NS.txt','El Centro 1940 (EW)':'elcentro_EW.txt','포항 2017 (BUS2 N)':'pohang_BUS2_BHN.txt','포항 2017 (BUS2 E)':'pohang_BUS2_BHE.txt','경주 2016 (BUS2 N)':'gyeongju_BUS2_BHN.txt','경주 2016 (CHJ2 N)':'gyeongju_CHJ2_BHN.txt','경주 2016 (CHJ2 E)':'gyeongju_CHJ2_BHE.txt'}
PGAS=[0.2,0.4,0.6,0.8,1.0,1.5]
def load(f):
    d=np.loadtxt(D+f); return d[:,0],d[:,1]
def job(a):
    name,pga,bld=a; t,x=load(FILES[name]); x=x-np.mean(x)
    x=x/np.abs(x).max()*pga*G
    i0=int(np.argmax(np.abs(x)>0.3)); t0=max(t[i0]-0.1,t[0])
    tt=np.arange(NSTEP)*DT+t0; ag=np.interp(tt,t,x,right=0.0)
    rng=np.random.default_rng(hash((name,pga,bld))%2**31)
    fs=1.0; sc=dict(ag=ag,F=np.zeros(NSTEP),jf=5,fscale=fs,fscale2=fs*0.85 if bld else fs,t_sw=1.5,zeta=0.02,info=dict())
    p=mkpack(sc,rng); J=[];Y=[]
    for u in U_GRID:
        mt=metrics(p,run(p,1,u)); J.append(mt['J']); Y.append(mt['ystroke'])
    return name,pga,bld,J,Y
if __name__=='__main__':
    jobs=[(n,p,b) for n in FILES for p in PGAS for b in (False,True)]
    with mp.Pool(2) as pl: R=pl.map(job,jobs)
    json.dump(R,open('x6_real.json','w'),default=float)
    import collections
    print('PGA  overflow% per u (', U_GRID,')  [N=',len(FILES)*2,']')
    for p in PGAS:
        rr=[r for r in R if r[1]==p]; Y=np.array([r[4] for r in rr]); J=np.array([r[3] for r in rr])
        print(p,(Y>1).mean(0).round(2),'stroke',Y.mean(0).round(2),'J',J.mean(0).round(3),'orc',J.min(1).mean().round(3))
    Y=np.array([r[4] for r in R]);J=np.array([r[3] for r in R]);print('ALL',(Y>1).mean(0).round(3),J.mean(0).round(3),J.min(1).mean().round(3))
