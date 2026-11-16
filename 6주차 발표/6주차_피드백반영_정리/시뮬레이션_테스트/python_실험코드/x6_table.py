import sys, json, pickle, numpy as np, multiprocessing as mp
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x6 import *
O=json.load(open('x6_results.json')); R=pickle.load(open('x6_stage1.pkl','rb'))
te=range(300,500); seeds=[R[i]['seed'] for i in te]
J=np.array(O['Jte_all']); ub=J.argmin(1)
tab=O['table']; 
def u_of(pg):
    for lo,hi,u in tab:
        if lo<=pg<hi: return u
    return tab[-1][2] if pg>=tab[-1][1] else tab[0][2]
rule=O['rule_preds']['0.3']; ai=O['preds']['0.3_asym']
def work(a):
    k,seed=a; rng=np.random.default_rng(seed); sc=gen_pulse(rng); p=mkpack(sc,rng)
    cfgs={'E0':(1,1.0,None),'E1':(1,4.0,None),'E2':(8,2.0,(2.0,999.0,1.0)),'E3':(8,2.0,(u_of(rule[k]),0.32,1.0)),'E4':(8,2.0,(u_of(ai[k]),0.32,1.0)),'Oracle':(1,float(U_GRID[ub[k]]),None)}
    out={}
    for n,(m,pa,th) in cfgs.items():
        mm,h=run(p,m,pa,th,record=True); mt=metrics(p,mm,h)
        out[n]=[mt['J'],mt['pk'],mt['rms'],mt['ystroke'],mt['y_first']]
    return out
if __name__=='__main__':
    with mp.Pool(2) as pl: res=pl.map(work,list(enumerate(seeds)))
    T={}
    for n in res[0]:
        a=np.array([r[n] for r in res])
        T[n]=dict(J=a[:,0].mean()*100,pk_red=(1-a[:,1].mean())*100,rms_red=(1-a[:,2].mean())*100,over=(a[:,3]>1).mean()*100,util=a[:,3].mean()*100,first=a[:,4].mean()*100)
        print(n,{k:round(v,1) for k,v in T[n].items()})
    json.dump(T,open('x6_table.json','w'))
