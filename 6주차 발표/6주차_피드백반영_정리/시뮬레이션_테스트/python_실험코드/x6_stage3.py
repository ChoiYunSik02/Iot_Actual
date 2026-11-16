import sys, numpy as np, pickle, multiprocessing as mp, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
from x6_stage2 import feat_only, winvec, sim_job, pool_eval
U=np.array(U_GRID)
def jgrid(seed):
    rng=np.random.default_rng(seed); sc=gen_pulse(rng); p=mkpack(sc,rng)
    Js=[];Ys=[]
    for u in U_GRID:
        m=run(p,1,u); mt=metrics(p,m); Js.append(mt['J']); Ys.append(mt['ystroke'])
    f=feat_only(seed)
    return dict(J=Js,Y=Ys,feat=f['feat'],A=f['A'],Tp=f['Tp'])
def mlpn(X,Y,seed=0,H=32,ep=1500,lr=3e-3,wd=1e-3):
    r=np.random.default_rng(seed); d=X.shape[1]; k=Y.shape[1]
    P=[r.normal(0,1/np.sqrt(d),(d,H)),np.zeros(H),r.normal(0,1/np.sqrt(H),(H,k)),np.zeros(k)]
    m=[np.zeros_like(a) for a in P]; v=[np.zeros_like(a) for a in P]
    for t in range(1,ep+1):
        h=np.tanh(X@P[0]+P[1]); o=h@P[2]+P[3]; g=2*(o-Y)/len(Y)
        gr=[X.T@((g@P[2].T)*(1-h**2))+wd*P[0],((g@P[2].T)*(1-h**2)).sum(0),h.T@g+wd*P[2],g.sum(0)]
        for i in range(4):
            m[i]=0.9*m[i]+0.1*gr[i]; v[i]=0.999*v[i]+0.001*gr[i]**2
            P[i]-=lr*(m[i]/(1-0.9**t))/(np.sqrt(v[i]/(1-0.999**t))+1e-8)
    return P
def predn(P,X): return np.tanh(X@P[0]+P[1])@P[2]+P[3]
if __name__=='__main__':
    R=pickle.load(open('x6_stage1.pkl','rb')); ste=[r['seed'] for r in R][300:500]
    tseeds=list(range(9000,11500))
    with mp.Pool(2) as pool: D=pool.map(jgrid,tseeds,chunksize=10)
    pickle.dump(D,open('x6_stage3_train.pkl','wb'))
    Jtr=np.array([d['J'] for d in D]); w=0.3
    Xtr=np.stack([winvec(d['feat'],w) for d in D])
    Ytr=(Jtr-Jtr.mean(1,keepdims=True))*100
    with mp.Pool(2) as pool: Fte=pool.map(feat_only,ste,chunksize=10)
    Xte=np.stack([winvec(f['feat'],w) for f in Fte])
    P=mlpn(Xtr,Ytr); Pr=predn(P,Xte)
    res={}
    for name,mask in [('all7',np.ones(7,bool)),('guard(u>=1.0)',U>=1.0)]:
        sel=np.where(mask)[0]; ch=sel[Pr[:,sel].argmin(1)]
        jobs=[[(8,1.0,(float(U[c]),0.32,1.0))] for c in ch]
        r=np.array(pool_eval(ste,jobs))[:,0,:]
        res[name]=[float(r[:,0].mean()),float((r[:,1]>1).mean()),float(r[:,1].mean()),np.bincount(ch,minlength=7).tolist()]
        print(name,res[name])
    json.dump(res,open('x6_stage3.json','w'))
