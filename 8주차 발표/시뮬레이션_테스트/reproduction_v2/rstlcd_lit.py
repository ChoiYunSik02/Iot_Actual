import numpy as np
from scipy.linalg import expm
from tlcd3 import full_K, full_M, IDX, N
from model import freqs
from tlcd import load_records, metrics, F0
from rstlcd import RSCtrl, MD_RS, cdamp
CFLOOR=0.02
class RSLitPlant:
    """원문 식 15~24 문자 그대로: X장치 질량 m cosθ, 강성 2 m cosθ g/L cosθ; Y장치 m sinθ, sinθ. θ는 0~90°만 허용, cos/sin 하한 0.02."""
    def __init__(self,dt):
        self.dt=dt; M=full_M(MD_RS,1e-9*MD_RS+MD_RS*CFLOOR)
        K=full_K(MD_RS*(2*np.pi*F0)**2, MD_RS*CFLOOR**2*(2*np.pi*F0)**2, False)
        f=freqs(full_M(MD_RS,MD_RS),full_K(MD_RS*(2*np.pi*F0)**2,MD_RS*(2*np.pi*F0)**2,False))[:2]; w=2*np.pi*f
        self.a0,self.a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02]); self.cache={}
    def disc(self,f,th):
        key=(round(f,5),round(th,4))
        if key not in self.cache:
            c=max(np.cos(th),CFLOOR); s=max(np.sin(th),CFLOOR); w2=(2*np.pi*f)**2
            M=full_M(MD_RS*c,MD_RS*s); K=full_K(MD_RS*c*w2*c, MD_RS*s*w2*s, False); n=K.shape[0]
            C=self.a0*M+self.a1*K; Mi=np.linalg.inv(M)
            A=np.block([[np.zeros((n,n)),np.eye(n)],[-Mi@K,-Mi@C]])
            E=np.zeros((n,2)); E[:N+1,0]=1; E[N+1:2*N+2,1]=1
            Bf=np.zeros((n,2)); Bf[IDX['xt'],0]=1; Bf[IDX['xd'],0]=-1; Bf[IDX['yt'],1]=1; Bf[IDX['yd'],1]=-1
            B=np.vstack([np.zeros((n,4)), np.hstack([-E, Mi@Bf])])
            Z=np.zeros((2*n+4,2*n+4)); Z[:2*n,:2*n]=A*self.dt; Z[:2*n,2*n:]=B*self.dt
            Ez=expm(Z); self.cache[key]=(Ez[:2*n,:2*n],Ez[:2*n,2*n:]); self.n=n
        return self.cache[key]
def simulate_lit(plant,ax,ay,ctrl):
    i=IDX; n=3*N+2; dt=plant.dt; x=np.zeros(2*n); T=len(ax); y=np.empty((T,3)); log=np.empty((T,3)); vprev=np.zeros(2)
    for k in range(T):
        top=x[[i['xt'],i['yt']]]; vtop=x[[n+i['xt'],n+i['yt']]]; acc=(vtop-vprev)/dt if k>0 else np.zeros(2); vprev=vtop.copy()
        vrel2=x[[n+i['xd'],n+i['yd']]]-vtop
        # RSCtrl 감쇠 판정용: 축 방향 상대속도 대신 X·Y 사영 상대속도를 직접 쓰도록 vrel을 X·Y 합성으로 전달
        th_prev=getattr(ctrl,'th',0.0); c,s=np.cos(th_prev),np.sin(th_prev)
        o=dict(top=top,vtop=vtop,atop_abs=acc+np.array([ax[k],ay[k]]),vrel=c*vrel2[0]+s*vrel2[1])
        f,th,kap=ctrl.step(k,k*dt,o)
        Ad,Bd=plant.disc(f,round(th/np.deg2rad(0.5))*np.deg2rad(0.5))
        F=cdamp(kap)*np.abs(vrel2)*vrel2
        y[k]=x[[i['xt'],i['yt'],i['tt']]]; log[k]=(f,np.rad2deg(th),kap)
        x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
    return y,log
