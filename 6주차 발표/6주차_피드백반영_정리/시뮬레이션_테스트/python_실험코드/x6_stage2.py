import sys, numpy as np, pickle, multiprocessing as mp, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
import x6
U=np.array(U_GRID); UDEF=2.0; G_=9.81
def feat_only(seed):
    rng=np.random.default_rng(seed); sc=gen_pulse(rng); p=mkpack(sc,rng)
    m,h=run(p,1,1.0,record=True)
    nz=np.random.default_rng(seed+99999)
    ag=h[:,5]+nz.normal(0,0.02,len(h)); ra=h[:,3]+nz.normal(0,0.02,len(h)); y=h[:,1]+nz.normal(0,0.002,len(h))
    it=int(np.argmax(np.abs(ag)>0.3)); idx=np.minimum(it+np.arange(50)*int(round(0.01/DT)),len(h)-1)
    # 노이즈 없는 특징도 (노이즈 스윕용): 원신호
    cl=np.stack([h[idx,5],h[idx,3],h[idx,1]*10])
    return dict(feat=np.stack([ag[idx],ra[idx],y[idx]*10]),clean=cl,A=sc['info']['A'],Tp=sc['info']['Tp'])
def winvec(f,w):
    n=int(round(w/0.01)); v=np.zeros((3,50)); v[:,:n]=f[:,:n]; v[0]/=10; v[1]/=10
    return v.ravel()
def mlp_train(X,y,asym,seed=0,H=32,ep=1500,lr=3e-3,wd=1e-4):
    r=np.random.default_rng(seed); d=X.shape[1]
    P=[r.normal(0,1/np.sqrt(d),(d,H)),np.zeros(H),r.normal(0,1/np.sqrt(H),(H,H)),np.zeros(H),r.normal(0,1/np.sqrt(H),(H,1)),np.zeros(1)]
    m=[np.zeros_like(a) for a in P]; v=[np.zeros_like(a) for a in P]
    for t in range(1,ep+1):
        h1=np.tanh(X@P[0]+P[1]); h2=np.tanh(h1@P[2]+P[3]); o=(h2@P[4]+P[5])[:,0]
        e=o-y; w=np.where(e<0,asym,1.0); g=(2*w*e/len(y))[:,None]
        gP4=h2.T@g; gb4=g.sum(0); d2=(g@P[4].T)*(1-h2**2)
        gP2=h1.T@d2; gb2=d2.sum(0); d1=(d2@P[2].T)*(1-h1**2)
        gP0=X.T@d1; gb0=d1.sum(0)
        gr=[gP0+wd*P[0],gb0,gP2+wd*P[2],gb2,gP4+wd*P[4],gb4]
        for i in range(6):
            m[i]=0.9*m[i]+0.1*gr[i]; v[i]=0.999*v[i]+0.001*gr[i]**2
            P[i]-=lr*(m[i]/(1-0.9**t))/(np.sqrt(v[i]/(1-0.999**t))+1e-8)
    return P
def mlp_pred(P,X):
    h1=np.tanh(X@P[0]+P[1]); h2=np.tanh(h1@P[2]+P[3]); return (h2@P[4]+P[5])[:,0]
def sim_job(a):
    seed,mode_args=a
    rng=np.random.default_rng(seed); sc=gen_pulse(rng); p=mkpack(sc,rng)
    out=[]
    for (mode,param,th3) in mode_args:
        m=run(p,mode,param,th3); mt=metrics(p,m); out.append((mt['J'],mt['ystroke'],mt['rms'],mt['pk']))
    return out
def pool_eval(seeds, jobs_per_seed):
    with mp.Pool(2) as pool: return pool.map(sim_job,[(s,j) for s,j in zip(seeds,jobs_per_seed)],chunksize=4)
if __name__=='__main__':
    R=pickle.load(open('x6_stage1.pkl','rb'))
    seeds=[r['seed'] for r in R]; J=np.array([r['J'] for r in R]); Y=np.array([r['ystroke'] for r in R])
    A=np.array([r['info']['A'] for r in R])
    tr=np.arange(0,300); te=np.arange(300,500)
    # PGA->u* 표 (훈련 300)
    bins=[0.2,0.6,1.0,1.5,2.01]; tab=[]
    for lo,hi in zip(bins[:-1],bins[1:]):
        m=tr[(A[tr]>=lo)&(A[tr]<hi)]; tab.append(float(U[J[m].mean(0).argmin()]))
    def u_of(pga):
        i=min(max(np.searchsorted(bins,pga,side='right')-1,0),3); return tab[i]
    print('table',list(zip(bins[:-1],tab)))
    out={'table':[[lo,hi,u] for lo,hi,u in zip(bins[:-1],bins[1:],tab)]}
    Jte=J[te]; Yte=Y[te]; ste=[seeds[i] for i in te]
    ub=Jte.argmin(1)
    out['X1']={'E0':[Jte[:,2].mean(),(Yte[:,2]>1).mean(),Yte[:,2].mean()],'E1':[Jte[:,6].mean(),(Yte[:,6]>1).mean(),Yte[:,6].mean()],
      'Oracle':[Jte.min(1).mean(),float(np.mean(Yte[np.arange(len(te)),ub]>1)),float(np.mean(Yte[np.arange(len(te)),ub]))],
      'fixed':[[float(u),float(Jte[:,k].mean()),float((Yte[:,k]>1).mean()),float(Yte[:,k].mean())] for k,u in enumerate(U)]}
    # X2 시간 예산
    ds=[0.0,0.05,0.1,0.2,0.3,0.5,1.0]
    X2={}
    for name,hold in [('대기유지',1.0),('즉시방어',UDEF)]:
        jobs=[[(8,hold,(float(U[b]),d,1.0)) for d in ds] for b in ub]
        r=pool_eval(ste,jobs); arr=np.array(r)
        X2[name]=[[d,float(arr[:,k,0].mean()),float((arr[:,k,1]>1).mean()),float(arr[:,k,1].mean())] for k,d in enumerate(ds)]
        print('X2',name,[(d,round(x,4)) for d,x in zip(ds,arr[:,:,0].mean(0))])
    out['X2']=X2
    # 특징 (MLP용 3000 훈련, 테스트 200 : 노이즈 포함 + 깨끗한)
    tseeds=list(range(5000,8000))
    with mp.Pool(2) as pool:
        Ftr=pool.map(feat_only,tseeds,chunksize=20); Fte=pool.map(feat_only,ste,chunksize=10)
    Atr=np.array([f['A'] for f in Ftr]); Ate=np.array([f['A'] for f in Fte])
    wins=[0.1,0.2,0.3,0.5]; X3={}; X4={}; models={}
    for w in wins:
        n=int(round(w/0.01))
        # 규칙: 창 안 지반가속도 최댓값 × k
        pk_tr=np.array([np.abs(f['feat'][0,:n]).max()/G_ for f in Ftr]); pk_te=np.array([np.abs(f['feat'][0,:n]).max()/G_ for f in Fte])
        k=float(np.median(Atr/np.maximum(pk_tr,1e-3)))
        rule_te=pk_te*k
        # MLP
        Xtr=np.stack([winvec(f['feat'],w) for f in Ftr]); Xte=np.stack([winvec(f['feat'],w) for f in Fte])
        for tag,asym in [('sym',1.0),('asym',4.0)]:
            P=mlp_train(Xtr,np.log(Atr),asym,ep=1200)
            pr=np.exp(mlp_pred(P,Xte)); models[(w,tag)]=P
            pr_clip=np.clip(pr,0.2,2.0)
            X4[(w,tag)]=dict(pred=pr_clip,mae=float(np.mean(np.abs(pr_clip-Ate))),under=float(np.mean(pr_clip<0.8*Ate)))
        X3[w]=dict(k=k,pred=np.clip(rule_te,0.2,2.0),mae=float(np.mean(np.abs(np.clip(rule_te,0.2,2.0)-Ate))),under=float(np.mean(np.clip(rule_te,0.2,2.0)<0.8*Ate)))
        print('win',w,'rule mae',round(X3[w]['mae'],3),'under',round(X3[w]['under'],2),'mlp sym',round(X4[(w,'sym')]['mae'],3),round(X4[(w,'sym')]['under'],2),'asym',round(X4[(w,'asym')]['mae'],3),round(X4[(w,'asym')]['under'],2))
    # 제어 평가
    infer=0.02
    def ctrl(pred,w,delay=infer):
        jobs=[[(8,UDEF,(u_of(pg),w+delay,1.0))] for pg in pred]
        r=np.array(pool_eval(ste,jobs))[:,0,:]; return [float(r[:,0].mean()),float((r[:,1]>1).mean()),float(r[:,1].mean())]
    X34={}
    for w in wins:
        X34[f'E3_{w}']=ctrl(X3[w]['pred'],w); X34[f'E4sym_{w}']=ctrl(X4[(w,'sym')]['pred'],w); X34[f'E4asym_{w}']=ctrl(X4[(w,'asym')]['pred'],w)
        X34[f'E3_{w}']+= [X3[w]['mae'],X3[w]['under']]; X34[f'E4sym_{w}']+=[X4[(w,'sym')]['mae'],X4[(w,'sym')]['under']]; X34[f'E4asym_{w}']+=[X4[(w,'asym')]['mae'],X4[(w,'asym')]['under']]
        print(w,{k:[round(v,3) for v in X34[k]] for k in X34 if k.endswith(str(w))})
    # E2 스트로크 규칙
    jobs=[[(7,0.6,None)] for _ in ste]; r=np.array(pool_eval(ste,jobs))[:,0,:]
    X34['E2']=[float(r[:,0].mean()),float((r[:,1]>1).mean()),float(r[:,1].mean())]
    out['X34']=X34
    # X5 지연/노이즈 (E4asym, w=0.3)
    w=0.3; P=models[(w,'asym')]; X5={'delay':[],'noise':[]}
    for dl in [0.0,0.02,0.05,0.1,0.2]:
        X5['delay'].append([dl]+ctrl(X4[(w,'asym')]['pred'],w,dl))
    n=int(round(w/0.01)); rng=np.random.default_rng(7)
    for sg in [0.02,0.1,0.3,1.0,3.0]:
        Xn=[]
        for f in Fte:
            c=f['clean'].copy(); c[0]+=rng.normal(0,sg,50); c[1]+=rng.normal(0,sg,50); c[2]+=rng.normal(0,sg/10*0.1,50)
            Xn.append(winvec(c,w))
        pr=np.clip(np.exp(mlp_pred(P,np.stack(Xn))),0.2,2.0)
        X5['noise'].append([sg]+ctrl(pr,w)+[float(np.mean(np.abs(pr-Ate)))])
    out['X5']=X5; print('X5',X5)
    out['Ate']=Ate.tolist(); out['preds']={f'{w}_{t}':X4[(w,t)]['pred'].tolist() for (w,t) in X4}; out['rule_preds']={str(w):X3[w]['pred'].tolist() for w in wins}
    out['Jte_all']=Jte.tolist(); out['Yte_all']=Yte.tolist(); out['Tp_te']=[f['Tp'] for f in Fte]
    json.dump(out,open('x6_results.json','w'),default=float)
    print('SAVED')
