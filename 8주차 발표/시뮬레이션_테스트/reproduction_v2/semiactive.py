import numpy as np
from scipy.linalg import expm
from tlcd3 import full_K, full_M, IDX, N
from tlcd import load_records, metrics, delta, MD, F0, G, RHO
from model import freqs
LAM=0.231; L0=2*G/(2*np.pi*F0)**2; AV=MD/(RHO*L0); AH=AV/LAM
def cdamp(kap,lam=LAM): return 0.5*RHO*AH*delta(lam,kap)   # 식 7 계수(2단계 채택)
FMIN,FMAX=0.3204,0.3542
class Plant:
    """92자유도. 장치 강성은 A 안에(암시적), 비선형 감쇠는 입력 힘. Rayleigh 감쇠는 공칭(0.3373 Hz) 전체 시스템 기준으로 고정."""
    def __init__(self,dt,md=MD):
        self.dt=dt; self.M=full_M(md,md); self.md=md
        k0=md*(2*np.pi*F0)**2; Kf=full_K(k0,k0,False); n=Kf.shape[0]; self.n=n
        f=freqs(self.M,Kf)[:2]; w=2*np.pi*f
        a0,a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02]); self.C=a0*self.M+a1*Kf
        self.Mi=np.linalg.inv(self.M)
        E=np.zeros((n,2)); E[:N+1,0]=1; E[N+1:2*N+2,1]=1
        Bf=np.zeros((n,2)); Bf[IDX['xt'],0]=1; Bf[IDX['xd'],0]=-1; Bf[IDX['yt'],1]=1; Bf[IDX['yd'],1]=-1
        self.B=np.vstack([np.zeros((n,4)), np.hstack([-E, self.Mi@Bf])]); self.cache={}
    def disc(self,fx,fy):
        key=(round(fx,5),round(fy,5))
        if key not in self.cache:
            n=self.n; K=full_K(self.md*(2*np.pi*fx)**2,self.md*(2*np.pi*fy)**2,False)
            A=np.block([[np.zeros((n,n)),np.eye(n)],[-self.Mi@K,-self.Mi@self.C]])
            # ZOH: [[A,B],[0,0]] 지수
            Z=np.zeros((2*n+4,2*n+4)); Z[:2*n,:2*n]=A*self.dt; Z[:2*n,2*n:]=self.B*self.dt
            Ez=expm(Z); self.cache[key]=(Ez[:2*n,:2*n],Ez[:2*n,2*n:])
        return self.cache[key]
def simulate(plant,ax,ay,ctrl):
    """ctrl.step(k, t, obs) -> (fx, fy, kapx, kapy); obs: 최상층 X,Y 변위·속도·가속도, 장치 상대속도"""
    n=plant.n; i=IDX; dt=plant.dt; x=np.zeros(2*n); T=len(ax)
    y=np.empty((T,3)); log=np.empty((T,4)); acc_prev=np.zeros(2); xprev=x.copy()
    for k in range(T):
        top=x[[i['xt'],i['yt']]]; vtop=x[[n+i['xt'],n+i['yt']]]
        vd=x[[n+i['xd'],n+i['yd']]]; vrel=vd-vtop
        acc=(vtop-xprev[[n+i['xt'],n+i['yt']]])/dt if k>0 else np.zeros(2)   # 상대가속도(후방차분)
        obs=dict(top=top,vtop=vtop,atop=acc,atop_abs=acc+np.array([ax[k],ay[k]]),vd=vd,vrel=vrel)
        fx,fy,kx_,ky_=ctrl.step(k,k*dt,obs)
        Ad,Bd=plant.disc(fx,fy)
        F=np.array([cdamp(kx_),cdamp(ky_)])*np.abs(vrel)*vrel
        y[k]=x[[i['xt'],i['yt'],i['tt']]]; log[k]=(fx,fy,kx_,ky_)
        xprev=x; x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
    return y,log
class Passive:
    def step(self,k,t,o): return F0,F0,0.4,0.4
