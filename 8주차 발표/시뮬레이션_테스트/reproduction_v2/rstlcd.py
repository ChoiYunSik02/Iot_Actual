import numpy as np
from scipy.linalg import expm
from model import build, freqs, N
from tlcd import load_records, metrics, delta, F0, G, RHO
from stlcd import ident
MD_RS=694767.0; LAM_RS=0.237
L0=2*G/(2*np.pi*F0)**2; AV=MD_RS/(RHO*L0); AH=AV/LAM_RS
def cdamp(kap): return 0.5*RHO*AH*delta(LAM_RS,kap)
FMIN,FMAX=0.3204,0.3542
XT,YT,TT,DV=N-1,2*N-1,3*N-1,3*N
class RSPlant:
    """회전 장치 1자유도(축 방향 액주 등가 변위). 건물과의 결합은 축 방향 사영: 상대변위 = u_d - (cosθ u_xt + sinθ u_yt).
    원문 식 20의 m·cosθ 두 자유도 표기는 θ>90°에서 음의 질량이 되어 그대로 쓸 수 없어 이 형태로 대체(가정)."""
    def __init__(self,dt):
        self.dt=dt; Mb,Kb=build('lit'); self.Mb=Mb; self.Kb=Kb; n=3*N+1; self.n=n
        self.M=np.zeros((n,n)); self.M[:n-1,:n-1]=Mb; self.M[DV,DV]=MD_RS; self.Mi=np.linalg.inv(self.M)
        K0=self.K(F0,0.0); f=freqs(self.M,K0)[:2]; w=2*np.pi*f
        self.a0,self.a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02]); self.cache={}
    def K(self,f,th):
        n=self.n; K=np.zeros((n,n)); K[:n-1,:n-1]=self.Kb; k=MD_RS*(2*np.pi*f)**2; c,s=np.cos(th),np.sin(th)
        p=np.zeros(n); p[DV]=1; p[XT]=-c; p[YT]=-s; K+=k*np.outer(p,p); return K
    def disc(self,f,th):
        key=(round(f,5),round(th,4))
        if key not in self.cache:
            n=self.n; K=self.K(f,th); C=self.a0*self.M+self.a1*K; c,s=np.cos(th),np.sin(th)
            A=np.block([[np.zeros((n,n)),np.eye(n)],[-self.Mi@K,-self.Mi@C]])
            E=np.zeros((n,2)); E[:N,0]=1; E[N:2*N,1]=1; E[DV]=[c,s]
            bf=np.zeros(n); bf[XT]=c; bf[YT]=s; bf[DV]=-1
            B=np.vstack([np.zeros((n,3)), np.hstack([-E,(self.Mi@bf)[:,None]])])
            Z=np.zeros((2*n+3,2*n+3)); Z[:2*n,:2*n]=A*self.dt; Z[:2*n,2*n:]=B*self.dt
            Ez=expm(Z); self.cache[key]=(Ez[:2*n,:2*n],Ez[:2*n,2*n:])
        return self.cache[key]
class RSCtrl:
    def __init__(self,dt,ident_m='morlet',angle='absmax',dfreq='current',rate=np.deg2rad(30)):
        self.dt=dt; self.m=ident_m; self.angle=angle; self.dfreq=dfreq; self.rate=rate
        self.nf=int(round(2.6/dt)); self.nc=int(round(1.0/dt)); self.hx=[]; self.hy=[]
        self.f=F0; self.th=0.0; self.th_tgt=0.0; self.kap=0.4
    def step(self,k,t,o):
        self.hx.append(o['top'][0]); self.hy.append(o['top'][1])
        if k>0 and k%self.nf==0:
            hx=np.array(self.hx); hy=np.array(self.hy)
            wx=min(max(ident(hx,self.dt,self.m),FMIN),FMAX); wy=min(max(ident(hy,self.dt,self.m),FMIN),FMAX)
            if self.dfreq=='current': Dx,Dy=abs(hx[-1]),abs(hy[-1])
            else: Dx,Dy=np.abs(hx[-self.nf:]).max(),np.abs(hy[-self.nf:]).max()
            self.f=(Dy*wy+Dx*wx)/(Dy+Dx) if Dx+Dy>0 else F0
            wx_=hx[-self.nf:]; wy_=hy[-self.nf:]
            if self.angle=='absmax': self.th_tgt=np.arctan2(np.abs(wy_).max(),np.abs(wx_).max())
            else:  # 최근 구간 변위의 주축 방향(0~180°)
                C=np.cov(np.vstack([wx_,wy_])); v=np.linalg.eigh(C)[1][:,-1]; a=np.arctan2(v[1],v[0])%np.pi; self.th_tgt=a
        d=self.th_tgt-self.th; step=self.rate*self.dt
        self.th+= np.clip(d,-step,step)
        if k>0 and k%self.nc==0:
            c,s=np.cos(self.th),np.sin(self.th); a=o['atop_abs']
            sx=(o['vrel']*c)*a[0]; sy=(o['vrel']*s)*a[1]
            self.kap=0.8 if (sx<=0 and sy<=0) else (0.1 if (sx>0 and sy>0) else 0.4)
        return self.f,self.th,self.kap
def simulate_rs(plant,ax,ay,ctrl):
    n=plant.n; dt=plant.dt; x=np.zeros(2*n); T=len(ax); y=np.empty((T,3)); log=np.empty((T,3)); vprev=np.zeros(2)
    th=0.0
    for k in range(T):
        top=x[[XT,YT]]; vtop=x[[n+XT,n+YT]]; acc=(vtop-vprev)/dt if k>0 else np.zeros(2); vprev=vtop.copy()
        c,s=np.cos(th),np.sin(th); vrel=x[n+DV]-(c*vtop[0]+s*vtop[1])
        o=dict(top=top,vtop=vtop,atop_abs=acc+np.array([ax[k],ay[k]]),vrel=vrel)
        f,th,kap=ctrl.step(k,k*dt,o)
        c,s=np.cos(th),np.sin(th); vrel=x[n+DV]-(c*vtop[0]+s*vtop[1])
        Ad,Bd=plant.disc(f,round(th/np.deg2rad(0.5))*np.deg2rad(0.5))
        F=cdamp(kap)*abs(vrel)*vrel
        y[k]=x[[XT,YT,TT]]; log[k]=(f,np.rad2deg(th),kap)
        x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
    return y,log
