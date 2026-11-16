import numpy as np, re, csv, itertools, scipy.linalg as sl
from scipy.signal import cont2discrete
from model import *
P='/mnt/user-data/outputs/peer15/'
rec=list(csv.DictReader(open(P+'records_table2.csv')))
def rd(f):
    L=open(P+f).read().split('\n'); m_=re.search(r'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)',L[3]); n=int(m_.group(1))
    return np.array(' '.join(L[4:]).split(),float)[:n]*9.80665, float(m_.group(2))
PAPER=np.array([
[4.484,4.406,7.028,10.040,5.801,12.104,4.338,10.373,8.059,3.242,7.676,6.996,1.610,2.098,5.086],
[2.044,2.080,3.023,4.109,1.655,5.551,1.773,3.861,3.414,1.449,2.683,2.916,0.856,0.569,1.336],
[3.148,1.837,2.825,5.399,10.462,5.818,5.583,9.974,7.174,4.115,5.691,10.083,2.014,2.262,4.282],
[1.234,0.619,1.147,2.276,4.151,2.331,1.593,3.660,3.141,1.543,2.190,4.155,0.734,0.358,1.505],
[15.492,7.611,8.432,28.896,63.364,26.008,17.292,63.809,49.680,23.793,32.990,62.737,10.493,10.074,31.919],
[6.053,2.871,3.029,10.716,25.416,8.568,7.146,21.827,18.759,8.119,11.728,24.859,4.299,1.935,9.544]]).T  # 15x6: Xmax Xrms Ymax Yrms thmax thrms
cache={}
def sysd(kv,dm,dt):
    key=(kv,dm,dt)
    if key in cache: return cache[key]
    M,K=build(kv); n=3*N
    if dm=='coupled': f=freqs(M,K)[:2]
    else: f=np.array([0.3373,1.0112])
    w=2*np.pi*f; z=0.02
    a0,a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[z,z])
    C=a0*M+a1*K
    Mi=np.linalg.inv(M)
    A=np.block([[np.zeros((n,n)),np.eye(n)],[-Mi@K,-Mi@C]])
    E=np.zeros((n,2)); E[:N,0]=1; E[N:2*N,1]=1
    B=np.vstack([np.zeros((n,2)),-E])
    Cm=np.zeros((3,2*n)); Cm[0,N-1]=1; Cm[1,2*N-1]=1; Cm[2,3*N-1]=1
    Ad,Bd,_,_,_=cont2discrete((A,B,Cm,np.zeros((3,2))),dt,method='foh')
    cache[key]=(Ad,Bd,Cm); return cache[key]
def sim(kv,dm,ax,ay,dt,pad):
    Ad,Bd,Cm=sysd(kv,dm,dt)
    n=min(len(ax),len(ay)); u=np.c_[ax[:n],ay[:n]]
    if pad: u=np.r_[u,np.zeros((int(pad/dt),2))]
    x=np.zeros(Ad.shape[0]); y=np.empty((len(u),3))
    # FOH discretization in scipy expects u[k] and handles internally via augmented state? use lsim-like loop
    for k in range(len(u)):
        y[k]=Cm@x; x=Ad@x+Bd@u[k]
    return y
def metrics(y):
    s=np.array([100,100,1e4])
    a=np.abs(y)*s; r=np.sqrt((y**2).mean(0))*s
    return np.array([a[:,0].max(),r[0],a[:,1].max(),r[1],a[:,2].max(),r[2]])
recs=[]
for r in rec:
    ax,dt=rd(r['x_file']); ay,dt2=rd(r['y_file']); assert dt==dt2; recs.append((ax,ay,dt))
res={}
for kv,dm,sc,pad in itertools.product(['cm','lit'],['coupled','table1'],['each','common'],[0,30]):
    out=[]
    for ax,ay,dt in recs:
        if sc=='each': fx=0.35/abs(ax).max(); fy=0.35/abs(ay).max()
        else: fx=fy=0.35/max(abs(ax).max(),abs(ay).max())
        out.append(metrics(sim(kv,dm,ax*fx,ay*fy,dt,pad)))
    out=np.array(out); rel=out/PAPER-1
    res[(kv,dm,sc,pad)]=out
    print(f"{kv:3s} {dm:7s} {sc:6s} pad{pad:2d} | mean|rel| all={np.abs(rel).mean()*100:5.1f}%  per-index:",' '.join(f'{v*100:5.1f}' for v in np.abs(rel).mean(0)))
np.save('res.npy',{str(k):v for k,v in res.items()},allow_pickle=True)
