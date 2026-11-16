import numpy as np, re, csv, os
from scipy.signal import cont2discrete
from model import N, build, freqs
G=9.81; RHO=1000.0
MD=463178.0; F0=0.3373
P='/mnt/user-data/outputs/peer15/'
if not os.path.isdir(P):  # 저장소 안의 같은 15쌍 (컨테이너 경로가 없을 때)
    P=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','peer_records_table2')+os.sep
rec=list(csv.DictReader(open(P+'records_table2.csv')))
def rd(f):
    L=open(P+f).read().split('\n'); m_=re.search(r'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)',L[3]); n=int(m_.group(1))
    return np.array(' '.join(L[4:]).split(),float)[:n]*9.80665, float(m_.group(2))
def load_records():
    out=[]
    for r in rec:
        ax,dt=rd(r['x_file']); ay,_=rd(r['y_file']); n=min(len(ax),len(ay))
        out.append((ax[:n]*0.35/abs(ax).max(), ay[:n]*0.35/abs(ay).max(), dt))
    return out
def delta(lam,kap):
    d1=(1-lam)**2+0.5*abs(1-lam)
    d2=((1-kap)+0.707*(1-kap)**0.375)**2*(1/kap)**2
    return d1+lam**2*d2
def base_matrices():
    """건물(무제어 채택 조건) + 장치 2자유도(X장치 u_dx, Y장치 u_dy). 장치 스프링·감쇠는 외부 힘으로 처리."""
    Mb,Kb=build('lit'); nb=3*N
    f=freqs(Mb,Kb)[:2]; w=2*np.pi*f
    a0,a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02])
    Cb=a0*Mb+a1*Kb
    return Mb,Kb,Cb
def make_sim(dt, md=MD):
    """상태: 건물 90자유도 + 장치 2. 장치-건물 사이 힘(스프링+감쇠)은 입력으로 넣어 시간에 따라 바뀌는 강성·감쇠를 다룬다."""
    Mb,Kb,Cb=base_matrices(); nb=3*N; n=nb+2
    M=np.zeros((n,n)); M[:nb,:nb]=Mb; M[nb,nb]=md; M[nb+1,nb+1]=md
    K=np.zeros((n,n)); K[:nb,:nb]=Kb
    C=np.zeros((n,n)); C[:nb,:nb]=Cb
    Mi=np.diag(1/np.diag(M)) if False else np.linalg.inv(M)
    A=np.block([[np.zeros((n,n)),np.eye(n)],[-Mi@K,-Mi@C]])
    E=np.zeros((n,2)); E[:N,0]=1; E[N:2*N,1]=1; E[nb,0]=1; E[nb+1,1]=1
    # 입력: [ag_x, ag_y, Fx, Fy]  Fx: X장치가 최상층 X에 주는 힘(+), 장치에는 -Fx
    Bf=np.zeros((n,2)); Bf[N-1,0]=1; Bf[nb,0]=-1; Bf[2*N-1,1]=1; Bf[nb+1,1]=-1
    B=np.vstack([np.zeros((n,4)), np.hstack([-E, Mi@Bf])])
    Ad,Bd,_,_,_=cont2discrete((A,B,np.eye(2*n),np.zeros((2*n,4))),dt,method='zoh')
    return Ad,Bd,n
def run(ax,ay,dt,law,cache={}):
    """law(t, rel_disp[2], rel_vel[2], y_top) -> (k[2], c_coef[2]) ; F = k*rel + c(|v|)*v, rel = u_d - u_top"""
    key=dt
    if key not in cache: cache[key]=make_sim(dt)
    Ad,Bd,n=cache[key]; nb=3*N
    x=np.zeros(2*n); T=len(ax); y=np.empty((T,3)); dv=np.empty((T,2))
    top=[N-1,2*N-1]
    for k in range(T):
        d=x[[nb,nb+1]]-x[top]; v=x[[n+nb,n+nb+1]]-x[[n+top[0],n+top[1]]]
        y[k]=x[[N-1,2*N-1,3*N-1]]
        kk,cf=law(k*dt,d,v,x)
        F=kk*d+cf*np.abs(v)*v
        x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
        dv[k]=d
    return y,dv
def metrics(y):
    s=np.array([100,100,1e4]); a=np.abs(y)*s; r=np.sqrt((y**2).mean(0))*s
    return np.array([a[:,0].max(),r[0],a[:,1].max(),r[1],a[:,2].max(),r[2]])
