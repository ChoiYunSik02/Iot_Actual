"""새 모델 시뮬레이션 층(8주차 보강): 플랜트(상태 전진) / 관측 / 제어기 / 시간축 대기열 / 액추에이터를 분리한 구조.
지연 0에서 R 정책이 rs_ref.run(해석 A)과 같은 결과를 내는지 회귀 확인용. 이산 행렬(Plant.disc)만 rs_ref와 공유한다.
고정 시간축의 '지연값'(delay_steps)은 설정값이며 실제 계산시간과 다르다."""
import numpy as np, collections
from rs_ref import Plant, cdamp, kappa, FMIN, FMAX, RATE, QTH, F0
from tlcd3 import IDX, N
from stlcd import ident
n_=3*N+2
class Observation:  # 관측 시각 k의 플랜트 사본(이상적 전체 상태)
    __slots__=('k','x','vt','vd','aa','hx','hy')
class Actuator:
    """장치 실제 상태. 진동수는 즉시 적용, 회전은 30°/s 속도 제한, 밸브는 즉시."""
    def __init__(s): s.f=F0; s.th=0.0; s.kap=0.4
    def apply_cmd(s,cmd):
        for key in ('f','tht','kap'):
            if key in cmd: setattr(s,'f' if key=='f' else ('tht' if key=='tht' else 'kap'),cmd[key])
    def advance(s,dt):
        s.th+=float(np.clip(getattr(s,'tht',0.0)-s.th,-RATE*dt,RATE*dt))
class RPolicy:
    """원문 식 10~13 (해석 A). 상태를 가지지 않고 관측과 이력만 사용."""
    def __init__(s,dt,valve='A'): s.nf=int(round(2.6/dt)); s.nc=int(round(1/dt)); s.valve=valve; s.dt=dt
    def decide(s,ob,hist_x,hist_y,th_act):
        k=ob.k; out=[]
        if k>0 and k%s.nf==0:
            wx=min(max(ident(hist_x[:k+1],s.dt,'morlet'),FMIN),FMAX); wy=min(max(ident(hist_y[:k+1],s.dt,'morlet'),FMIN),FMAX)
            Dx,Dy=abs(hist_x[k]),abs(hist_y[k]); f=(Dy*wy+Dx*wx)/(Dy+Dx) if Dx+Dy>0 else F0
            tht=np.arctan2(np.abs(hist_y[k-s.nf+1:k+1]).max(),np.abs(hist_x[k-s.nf+1:k+1]).max())
            out.append(('slow',{'f':f,'tht':tht},(1,k,k*s.dt,f,np.rad2deg(tht),wx,wy)))
        return out
    def decide_fast(s,ob,th_act):
        k=ob.k
        if k>0 and k%s.nc==0:
            c,s_=np.cos(th_act),np.sin(th_act); vr=ob.vd-ob.vt; aa=ob.aa
            ax_=c*vr[0]+s_*vr[1]; sx,sy=ax_*c*aa[0],ax_*s_*aa[1]; kap=kappa(sx,sy)
            return [('fast',{'kap':kap},(2,k,k*s.dt,kap,sx,sy,0))]
        return []
def simulate(plant,ax,ay,policy,delay_slow=0,delay_fast=0):
    """delay_*: 결정 시각에서 지령 적용까지의 스텝 수(고정 시간축 설정값). 0이면 같은 스텝에서 적용."""
    dt=plant.dt; T=len(ax); x=np.zeros(2*n_); act=Actuator(); act.tht=0.0
    y=np.empty((T,3)); hx=np.empty(T); hy=np.empty(T); vprev=np.zeros(2); q=collections.deque(); dec=[]; st=[]
    nc=policy.nc; i=IDX
    for k in range(T):
        ob=Observation(); ob.k=k; ob.x=x; ob.vt=x[[n_+i['xt'],n_+i['yt']]]
        ob.aa=((ob.vt-vprev)/dt if k>0 else np.zeros(2))+np.array([ax[k],ay[k]]); vprev=ob.vt.copy()
        ob.vd=x[[n_+i['xd'],n_+i['yd']]]; hx[k]=x[i['xt']]; hy[k]=x[i['yt']]; ob.hx=hx; ob.hy=hy
        for kind,cmd,rec in policy.decide(ob,hx,hy,act.th):
            q.append((k+delay_slow,cmd)); dec.append(rec)
        # 느린 지령 적용 후 회전 갱신, 그 다음 빠른 결정(원 구현과 같은 순서)
        while q and q[0][0]<=k: act.apply_cmd(q.popleft()[1])
        act.advance(dt)
        for kind,cmd,rec in policy.decide_fast(ob,act.th):
            q.append((k+delay_fast,cmd)); dec.append(rec)
        while q and q[0][0]<=k: act.apply_cmd(q.popleft()[1])
        fq=np.floor(act.f*1e5+0.5)/1e5; thq=np.floor(act.th/QTH+0.5)*QTH; thq=np.floor(thq*1e4+0.5)/1e4
        Ad,Bd=plant.disc(fq,thq); vr=ob.vd-ob.vt; F=cdamp(act.kap)*np.abs(vr)*vr
        y[k]=x[[i['xt'],i['yt'],i['tt']]]
        if k%nc==0: st.append((k,k*dt,np.rad2deg(act.th),np.rad2deg(thq),fq,act.kap,x[i['xd']]-x[i['xt']],x[i['yd']]-x[i['yt']]))
        x=Ad@x+Bd@np.r_[ax[k],ay[k],F]
    return y,dec,st
