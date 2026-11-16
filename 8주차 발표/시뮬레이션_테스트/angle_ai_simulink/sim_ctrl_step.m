function u=sim_ctrl_step(t,x,ag,pol)
% Simulink 제어기 블록이 매 스텝 호출. 원문 펌프(식 10·11)·밸브(식 12, A)·회전 속도 제한은 그대로,
% 회전 목표각만 pol에 따라: 1=R(원문 식 13), 2=AI(회전각 예측 MLP), 3=W13(최근 1.3 s 방향).
% 출력 u=[fq; thq; kap; dt]. t=0에서 내부 상태를 초기화한다.
persistent k hx hy gx gy vprev th tht f kap thprev NN dt
N=30; xt=N; xd=N+1; yt=2*N+1; yd=2*N+2; n=3*N+2;
FMIN=0.3204; FMAX=0.3542; RATE=30*pi/180; QTH=0.5*pi/180; F0=0.3373;
if isempty(k) || t<1e-9
    dt=evalin('base','SIM_DT'); T=evalin('base','SIM_T');
    k=0; hx=zeros(T,1); hy=hx; gx=hx; gy=hx; vprev=[0 0]; th=0; tht=0; f=F0; kap=0.4; thprev=pi/4;
    if isempty(NN), NN=load(fullfile(fileparts(mfilename('fullpath')),'angle_ai_m1.mat')); end
end
nf=round(2.6/dt); nc=round(1/dt); k0=k; kk=k+1;
vt=[x(n+xt) x(n+yt)]; if k0>0, acc=(vt-vprev)/dt; else, acc=[0 0]; end; vprev=vt;
vd=[x(n+xd) x(n+yd)]; vr=vd-vt; aa=acc+[ag(1) ag(2)]; hx(kk)=x(xt); hy(kk)=x(yt); gx(kk)=ag(1); gy(kk)=ag(2);
if k0>0 && mod(k0,nf)==0
    wx=min(max(ident_(hx(1:kk),dt),FMIN),FMAX); wy=min(max(ident_(hy(1:kk),dt),FMIN),FMAX);
    Dx=abs(hx(kk)); Dy=abs(hy(kk)); if Dx+Dy>0, f=(Dy*wy+Dx*wx)/(Dy+Dx); else, f=F0; end
    thR=atan2(max(abs(hy(kk-nf+1:kk))),max(abs(hx(kk-nf+1:kk))));
    if pol==1, tht=thR;
    else
        Fv=feats_(dt,hx(1:kk),hy(1:kk),gx(1:kk),gy(1:kk),th,thprev);
        if pol==3, tht=Fv(1); else, tht=min(max(mlp_(NN,Fv)*pi/180,0),pi/2); end
    end
    thprev=thR;
end
th=th+min(max(tht-th,-RATE*dt),RATE*dt);
if k0>0 && mod(k0,nc)==0
    c=cos(th); s=sin(th); a_=c*vr(1)+s*vr(2); sx=a_*c*aa(1); sy=a_*s*aa(2);
    if sx<=0 && sy<=0, kap=0.8; elseif sx>0 && sy>0, kap=0.1; else, kap=0.4; end
end
fq=floor(f*1e5+0.5)/1e5; thq=floor(th/QTH+0.5)*QTH; thq=floor(thq*1e4+0.5)/1e4;
u=[fq; thq; kap; dt]; k=k+1;
end
function a=ang_(u,v)
if isempty(u), a=pi/4; else, a=atan2(max(abs(v)),max(abs(u))); end
end
function F=feats_(dt,hx,hy,gx,gy,th,thprev)
n1=round(1.3/dt); n2=round(2.6/dt); n5=round(5.2/dt); L=numel(hx);
i1=max(1,L-n1+1):L; i2=max(1,L-n2+1):L; i5=max(1,L-n5+1):L;
a13=ang_(hx(i1),hy(i1)); a26=ang_(hx(i2),hy(i2)); a52=ang_(hx(i5),hy(i5)); aall=ang_(hx,hy);
g13=ang_(gx(i1),gy(i1)); g26=ang_(gx(i2),gy(i2));
rx=sqrt(mean(hx(i2).^2)); ry=sqrt(mean(hy(i2).^2)); arms=atan2(ry,rx);
m13=max(max(abs(hx(i1))),max(abs(hy(i1)))); m26=max(max(abs(hx(i2))),max(abs(hy(i2))));
if m26>0, grow=m13/m26; else, grow=1; end
gm13=max(max(abs(gx(i1))),max(abs(gy(i1)))); gm26=max(max(abs(gx(i2))),max(abs(gy(i2))));
if gm26>0, ggrow=gm13/gm26; else, ggrow=1; end
tt=min(L*dt,60)/60;
F=[a13 a26 a52 aall g13 g26 arms grow ggrow a26-thprev th tt cos(2*a26)];
end
function o=mlp_(NN,F)
z=(F-NN.mu)./NN.sd; h=tanh(z*NN.W1+NN.b1); h=tanh(h*NN.W2+NN.b2); o=h*NN.W3+NN.b3;
end
function fr=ident_(sig,dt)
if numel(sig)<8, fr=0.3373; return; end
F=linspace(0.05,2.0,391); t=(0:numel(sig)-1)'*dt; tk=t(end); mags=zeros(size(F));
for i=1:numel(F)
    f=F(i); sd=6/(2*pi*f); msk=t>=tk-4*sd; tau=t(msk)-tk;
    psi=exp(-1i*2*pi*f*tau).*exp(-tau.^2/(2*sd^2)); mags(i)=abs(sum(sig(msk).*psi))*dt*sqrt(f);
end
[~,ix]=max(mags); fr=F(ix);
end
