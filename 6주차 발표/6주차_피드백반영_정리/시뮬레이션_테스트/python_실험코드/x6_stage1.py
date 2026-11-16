import sys, numpy as np, pickle, multiprocessing as mp
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x6, sim
from x6 import *
def work(args):
    seed = args
    rng = np.random.default_rng(seed)
    sc = gen_pulse(rng)
    p = mkpack(sc, rng)
    Js=[];Ys=[];Rs=[];Ps=[]
    for u in U_GRID:
        m = run(p,1,u); mt = metrics(p,m)
        Js.append(mt['J']);Ys.append(mt['ystroke']);Rs.append(mt['rms']);Ps.append(mt['pk'])
    m,h = run(p,1,1.0,record=True)
    mt = metrics(p,m,h)
    nz = np.random.default_rng(seed+99999)
    ag = h[:,5]+nz.normal(0,0.02,len(h)); ra = h[:,3]+nz.normal(0,0.02,len(h)); y = h[:,1]+nz.normal(0,0.002,len(h))
    it = int(np.argmax(np.abs(ag)>0.3))
    idx = it + np.arange(0,50)*int(round(0.01/DT))
    idx = np.minimum(idx,len(h)-1)
    feat = np.stack([ag[idx], ra[idx], y[idx]*10])   # 3x50
    return dict(seed=seed, info=sc['info'], J=Js, ystroke=Ys, rms=Rs, pk=Ps, feat=feat, it=it, yfirst=mt['y_first'])
if __name__=='__main__':
    seeds = list(range(1000,1500))
    with mp.Pool(2) as pool: res = pool.map(work, seeds, chunksize=5)
    pickle.dump(res, open('x6_stage1.pkl','wb'))
    print('done', len(res))
