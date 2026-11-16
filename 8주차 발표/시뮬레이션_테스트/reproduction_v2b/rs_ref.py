"""RS-TLCD 기준 구현 v2b (원문 식 15~24 표기의 두 자유도 모델). MATLAB run_v2b_rs_check.m과 한 줄씩 대응.
v2(rstlcd_lit + dyn.RS2)와의 차이: 이산 행렬을 '반올림한 키 값'(진동수 1e-5 Hz, 행렬각 0.5° 단위)으로 계산(v2는 처음 본 값으로 계산 후 재사용).
밸브 속도 해석: 'A' 두 상대속도를 축으로 합성 후 X·Y로 재사영(v2), 'B' 각 자유도 상대속도 직접, 'C' 장치 절대속도를 축으로 합성·재사영한 값 − 층 속도(식 12 문자 그대로 읽기)."""
import numpy as np, sys, csv
from scipy.linalg import expm
from tlcd3 import full_K, full_M, IDX, N
from model import freqs
from tlcd import load_records, metrics, delta, F0, G, RHO
from stlcd import ident
MD=694767.0; LAM=0.237; L0=2*G/(2*np.pi*F0)**2; AV=MD/(RHO*L0); AH=AV/LAM
FMIN,FMAX=0.3204,0.3542; CF=0.02; RATE=np.deg2rad(30); QTH=np.deg2rad(0.5)
def cdamp(kap): return 0.5*RHO*AH*delta(LAM,kap)
def kappa(sx,sy): return 0.8 if (sx<=0 and sy<=0) else (0.1 if (sx>0 and sy>0) else 0.4)
class Plant:
    def __init__(s,dt):
        s.dt=dt; w2=(2*np.pi*F0)**2
        f=freqs(full_M(MD,MD),full_K(MD*w2,MD*w2,False))[:2]; w=2*np.pi*f
        s.a0,s.a1=np.linalg.solve([[1/(2*w[0]),w[0]/2],[1/(2*w[1]),w[1]/2]],[0.02,0.02]); s.cache={}
    def disc(s,fq,thq):
        key=(fq,thq)
        if key not in s.cache:
            if len(s.cache)>2000: s.cache.clear()
            c=max(np.cos(thq),CF); sn=max(np.sin(thq),CF); w2=(2*np.pi*fq)**2
            M=full_M(MD*c,MD*sn); K=full_K(MD*c*w2*c,MD*sn*w2*sn,False); n=K.shape[0]
            C=s.a0*M+s.a1*K; Mi=np.linalg.inv(M)
            A=np.block([[np.zeros((n,n)),np.eye(n)],[-Mi@K,-Mi@C]])
            E=np.zeros((n,2)); E[:N+1,0]=1; E[N+1:2*N+2,1]=1
            Bf=np.zeros((n,2)); Bf[IDX['xt'],0]=1; Bf[IDX['xd'],0]=-1; Bf[IDX['yt'],1]=1; Bf[IDX['yd'],1]=-1
            B=np.vstack([np.zeros((n,4)),np.hstack([-E,Mi@Bf])])
            Z=np.zeros((2*n+4,2*n+4)); Z[:2*n,:2*n]=A*s.dt; Z[:2*n,2*n:]=B*s.dt; Ez=expm(Z)
            s.cache[key]=(Ez[:2*n,:2*n],Ez[:2*n,2*n:])
        return s.cache[key]
def run(plant,ax,ay,valve,shadow=False):
    i=IDX; n=3*N+2; dt=plant.dt; nf=int(round(2.6/dt)); nc=int(round(1/dt))
    x=np.zeros(2*n); T=len(ax); y=np.empty((T,3)); vprev=np.zeros(2); hx=np.empty(T); hy=np.empty(T)
    th=0.0; tht=0.0; f=F0; kap=0.4; dec=[]; st=[]; sh=[]
    for k in range(T):
        vt=x[[n+i['xt'],n+i['yt']]]; acc=(vt-vprev)/dt if k>0 else np.zeros(2); vprev=vt.copy()
        vd=x[[n+i['xd'],n+i['yd']]]; vr=vd-vt; aa=acc+np.array([ax[k],ay[k]])
        hx[k]=x[i['xt']]; hy[k]=x[i['yt']]
        if k>0 and k%nf==0:
            wx=min(max(ident(hx[:k+1],dt,'morlet'),FMIN),FMAX); wy=min(max(ident(hy[:k+1],dt,'morlet'),FMIN),FMAX)
            Dx,Dy=abs(hx[k]),abs(hy[k]); f=(Dy*wy+Dx*wx)/(Dy+Dx) if Dx+Dy>0 else F0
            tht=np.arctan2(np.abs(hy[k-nf+1:k+1]).max(),np.abs(hx[k-nf+1:k+1]).max())
            dec.append((1,k,k*dt,f,np.rad2deg(tht),wx,wy))
        th+=np.clip(tht-th,-RATE*dt,RATE*dt)
        if k>0 and k%nc==0:
            c,s_=np.cos(th),np.sin(th)
            def S(v):
                if v=='A': ax_=c*vr[0]+s_*vr[1]; return ax_*c*aa[0], ax_*s_*aa[1]
                if v=='B': return vr[0]*aa[0], vr[1]*aa[1]
                if v=='C': ab=c*vd[0]+s_*vd[1]; return (ab*c-vt[0])*aa[0], (ab*s_-vt[1])*aa[1]
            sx,sy=S(valve); kap=kappa(sx,sy); dec.append((2,k,k*dt,kap,sx,sy,0))
            if shadow:
                r=[k*dt,np.rad2deg(th),vr[0],vr[1],vd[0],vd[1],vt[0],vt[1],aa[0],aa[1]]
                for v in 'ABC': a_,b_=S(v); r+=[a_,b_,kappa(a_,b_)]
                sh.append(r)
        # r1: 반올림 규칙을 '0.5 올림'(floor(x+0.5))으로 고정. Python round(짝수 쪽)와 MATLAB round(0에서 먼 쪽)의 동점 처리 차이 제거
        fq=np.floor(f*1e5+0.5)/1e5; thq=np.floor(th/QTH+0.5)*QTH; thq=np.floor(thq*1e4+0.5)/1e4
        Ad,Bd=plant.disc(fq,thq); F=cdamp(kap)*np.abs(vr)*vr
        y[k]=x[[i['xt'],i['yt'],i['tt']]]
        if k%nc==0: st.append((k,k*dt,np.rad2deg(th),np.rad2deg(thq),fq,kap,x[i['xd']]-x[i['xt']],x[i['yd']]-x[i['yt']]))
        x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
    return y,dec,st,sh
if __name__=='__main__':
    valve=sys.argv[1]; shadow=len(sys.argv)>2 and sys.argv[2]=='shadow'
    R=load_records(); plants={}; met=[]; D=[]; S=[]; SH=[]
    for j,(ax,ay,dt) in enumerate(R):
        if dt not in plants: plants[dt]=Plant(dt)
        y,dec,st,sh=run(plants[dt],ax,ay,valve,shadow); met.append(metrics(y))
        D+=[(j+1,)+d for d in dec]; S+=[(j+1,)+s for s in st]; SH+=[[j+1]+s for s in sh]; print(valve,'rec',j+1,flush=True)
    np.save(f'rsref_{valve}_metrics.npy',np.array(met))
    with open(f'py_rs_{valve}_dec.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow(['rec','type','step0','t','v1','v2','v3','v4']); w.writerows(D)
    with open(f'py_rs_{valve}_state.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow(['rec','step0','t','theta_act','theta_mat','f_applied','kappa','rel_x','rel_y']); w.writerows(S)
    if shadow:
        with open('rs_valve_shadow_log.csv','w',newline='') as fh:
            w=csv.writer(fh); w.writerow(['rec','t','theta','vrel_x','vrel_y','vdev_x','vdev_y','vtop_x','vtop_y','atop_x','atop_y','A_sx','A_sy','A_kap','B_sx','B_sy','B_kap','C_sx','C_sy','C_kap']); w.writerows(SH)
    from paper_tables import UNC,RST
    uz=np.load('out_unc_zoh_up1.npy'); ro=(1-np.array(met)/uz)*100; print(valve,'red6 %.3f'%ro.mean(), np.round(ro.mean(0),2))
