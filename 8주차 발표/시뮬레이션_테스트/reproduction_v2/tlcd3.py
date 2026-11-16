import numpy as np
from scipy.signal import cont2discrete
from model import N, kx, kt, ex, ey, shear, freqs
from tlcd import load_records, metrics, delta, MD, F0, G, RHO
def full_K(kdx, kdy, devcouple):
    """자유도 순서: X층 30, X장치, Y층 30, Y장치, θ층 30  (총 92). 식 15~22를 글자 그대로."""
    Kx=np.zeros((N+1,N+1)); Kx[:N,:N]=shear(kx); Kx[N-1,N-1]+=kdx; Kx[N,N]=kdx; Kx[N-1,N]=Kx[N,N-1]=-kdx
    Ky=np.zeros((N+1,N+1)); Ky[:N,:N]=shear(kx); Ky[N-1,N-1]+=kdy; Ky[N,N]=kdy; Ky[N-1,N]=Ky[N,N-1]=-kdy
    Kt=shear(kt)
    if devcouple: Kxt=Kx[:, :N]*ey; Kyt=Ky[:, :N]*ex
    else:
        Kxt=np.zeros((N+1,N)); Kxt[:N]=shear(kx)*ey; Kyt=np.zeros((N+1,N)); Kyt[:N]=shear(kx)*ex
    n=3*N+2; K=np.zeros((n,n))
    K[:N+1,:N+1]=Kx; K[N+1:2*N+2,N+1:2*N+2]=Ky; K[2*N+2:,2*N+2:]=Kt
    K[:N+1,2*N+2:]=Kxt; K[2*N+2:,:N+1]=Kxt.T; K[N+1:2*N+2,2*N+2:]=Kyt; K[2*N+2:,N+1:2*N+2]=Kyt.T
    return K
def full_M(mdx,mdy):
    m=9.216e5; J=2.797e8
    return np.diag(np.r_[np.full(N,m),mdx,np.full(N,m),mdy,np.full(N,J)])
IDX=dict(xt=N-1,xd=N,yt=2*N,yd=2*N+1,tt=3*N+1)
def make(dt,kd,devcouple,ray_full=True):
    M=full_M(MD,MD); K=full_K(kd,kd,devcouple); n=K.shape[0]
    Kr=K if ray_full else full_K(0,0,devcouple)
    f=freqs(M,Kr)[:2]; w=2*np.pi*f
    a0,a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02]); C=a0*M+a1*Kr
    if not ray_full: C[[IDX['xd'],IDX['yd']],:]=0; C[:,[IDX['xd'],IDX['yd']]]=0
    Mi=np.linalg.inv(M)
    A=np.block([[np.zeros((n,n)),np.eye(n)],[-Mi@K,-Mi@C]])
    E=np.zeros((n,2)); E[:N+1,0]=1; E[N+1:2*N+2,1]=1
    Bf=np.zeros((n,2)); Bf[IDX['xt'],0]=1; Bf[IDX['xd'],0]=-1; Bf[IDX['yt'],1]=1; Bf[IDX['yd'],1]=-1
    B=np.vstack([np.zeros((n,4)), np.hstack([-E, Mi@Bf])])
    Ad,Bd,_,_,_=cont2discrete((A,B,np.eye(2*n),np.zeros((2*n,4))),dt,method='zoh')
    return Ad,Bd,n
def run(ax,ay,dt,sysm,cfun):
    Ad,Bd,n=sysm; i=IDX
    x=np.zeros(2*n); T=len(ax); y=np.empty((T,3))
    for k in range(T):
        vrel=np.array([x[n+i['xd']]-x[n+i['xt']], x[n+i['yd']]-x[n+i['yt']]]); vabs=x[[n+i['xd'],n+i['yd']]]
        y[k]=x[[i['xt'],i['yt'],i['tt']]]
        x=Ad@x+Bd@np.r_[ax[k],ay[k],cfun(vrel,vabs)]
    return y
