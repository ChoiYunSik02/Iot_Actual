function run_angle_ai_check(datadir, outdir, policies, recs)
% 회전각 예측 AI의 MATLAB 독립 구현. Python angleai/runa.py + features.py와 같은 정의.
% RS-TLCD 모델·펌프·밸브(A)·회전 규칙은 reproduction_v2b/matlab/run_v2b_rs_check.m과 동일하고, 회전 목표각만 정책별로 다르다.
% policies: 'R'(원문 규칙), 'AI'(angle_ai_m1.mat MLP), 'W13'(최근 1.3 s 방향)
% 사용 예: run_angle_ai_check('C:\Users\cys\Desktop\iot-actuator-week08\peer_records_table2', pwd, {'R','AI'}, 1:15)
if nargin<3, policies={'R','AI'}; end
T=readtab_(fullfile(datadir,'records_table2.csv')); if nargin<4, recs=1:numel(T.x); end
here=fileparts(mfilename('fullpath')); NN=load(fullfile(here,'angle_ai_m1.mat'));
P.N=30; P.m=9.216e5; P.J=2.797e8; P.kx=1.6213e9*ones(P.N,1); P.kx(1)=1.021e9; P.kt=5.0261e11*ones(P.N,1); P.kt(1)=3.1651e11;
P.ex=6; P.ey=2; P.MD=694767; P.F0=0.3373; g=9.81; rho=1000; P.lam=0.237;
L0=2*g/(2*pi*P.F0)^2; Av=P.MD/(rho*L0); Ah=Av/P.lam; P.cd=@(kap) 0.5*rho*Ah*delta_(P.lam,kap);
w2=(2*pi*P.F0)^2; Mn=fullM(P.MD,P.MD,P); Kn=fullK(P.MD*w2,P.MD*w2,P);
ev=sort(eig(Kn,Mn)); w=sqrt(ev(1:2)); ab=[1/(2*w(1)) w(1)/2; 1/(2*w(2)) w(2)/2]\[0.02;0.02]; P.a0=ab(1); P.a1=ab(2);
for ip=1:numel(policies)
    pol=policies{ip}; met=[]; DEC=[];
    for r=recs
        [ax,dt]=readAT2(fullfile(datadir,T.x{r})); [ay,~]=readAT2(fullfile(datadir,T.y{r}));
        n=min(numel(ax),numel(ay)); x=ax(1:n)*0.35/max(abs(ax)); y=ay(1:n)*0.35/max(abs(ay));
        [yy,dec]=runrs(P,x,y,dt,pol,NN);
        met=[met; r met6(yy)]; DEC=[DEC; r*ones(size(dec,1),1) dec]; %#ok<AGROW>
        fprintf('%s rec %d done\n',pol,r);
    end
    csvw_(fullfile(outdir,sprintf('matlab_angle_%s_metrics.csv',pol)),{'no','Xmax','Xrms','Ymax','Yrms','thmax','thrms'},met);
    csvw_(fullfile(outdir,sprintf('matlab_angle_%s_dec.csv',pol)),{'rec','step0','t','f','thR_deg','tht_deg'},DEC);
end
fprintf('MATLAB_ANGLE_DONE\n');
end
% ------------------------------------------------------------------
function [y,dec]=runrs(P,ax,ay,dt,pol,NN)
N=P.N; xt=N; xd=N+1; yt=2*N+1; yd=2*N+2; tt=3*N+2; n=3*N+2;
nf=round(2.6/dt); nc=round(1/dt); FMIN=0.3204; FMAX=0.3542; RATE=30*pi/180; QTH=0.5*pi/180;
cache=containers.Map('KeyType','char','ValueType','any');
x=zeros(2*n,1); T=numel(ax); y=zeros(T,3); vprev=[0 0]; hx=zeros(T,1); hy=zeros(T,1);
th=0; tht=0; f=P.F0; kap=0.4; thprev=pi/4; dec=zeros(0,5);
for k=1:T
    k0=k-1;
    vt=[x(n+xt) x(n+yt)]; if k0>0, acc=(vt-vprev)/dt; else, acc=[0 0]; end; vprev=vt;
    vd=[x(n+xd) x(n+yd)]; vr=vd-vt; aa=acc+[ax(k) ay(k)]; hx(k)=x(xt); hy(k)=x(yt);
    if k0>0 && mod(k0,nf)==0
        wx=min(max(ident_(hx(1:k),dt),FMIN),FMAX); wy=min(max(ident_(hy(1:k),dt),FMIN),FMAX);
        Dx=abs(hx(k)); Dy=abs(hy(k)); if Dx+Dy>0, f=(Dy*wy+Dx*wx)/(Dy+Dx); else, f=P.F0; end
        thR=atan2(max(abs(hy(k-nf+1:k))),max(abs(hx(k-nf+1:k))));
        switch pol
            case 'R', tht=thR;
            otherwise
                Fv=feats_(dt,hx(1:k),hy(1:k),ax(1:k),ay(1:k),th,thprev);
                if strcmp(pol,'W13'), tht=Fv(1);
                else, tht=min(max(mlp_(NN,Fv)*pi/180,0),pi/2); end
        end
        thprev=thR; dec(end+1,:)=[k0 k0*dt f thR*180/pi tht*180/pi]; %#ok<AGROW>
    end
    th=th+min(max(tht-th,-RATE*dt),RATE*dt);
    if k0>0 && mod(k0,nc)==0
        c=cos(th); s=sin(th); a_=c*vr(1)+s*vr(2); sx=a_*c*aa(1); sy=a_*s*aa(2);
        if sx<=0 && sy<=0, kap=0.8; elseif sx>0 && sy>0, kap=0.1; else, kap=0.4; end
    end
    fq=floor(f*1e5+0.5)/1e5; thq=floor(th/QTH+0.5)*QTH; thq=floor(thq*1e4+0.5)/1e4;
    key=sprintf('%.5f_%.4f',fq,thq);
    if ~isKey(cache,key)
        if cache.Count>2000, cache=containers.Map('KeyType','char','ValueType','any'); end
        cc=max(cos(thq),0.02); ss=max(sin(thq),0.02); w2=(2*pi*fq)^2;
        M=fullM(P.MD*cc,P.MD*ss,P); K=fullK(P.MD*cc*w2*cc,P.MD*ss*w2*ss,P); C=P.a0*M+P.a1*K; Mi=inv(M);
        A=[zeros(n) eye(n); -Mi*K -Mi*C];
        E=zeros(n,2); E(1:N+1,1)=1; E(N+2:2*N+2,2)=1; Bf=zeros(n,2); Bf(xt,1)=1; Bf(xd,1)=-1; Bf(yt,2)=1; Bf(yd,2)=-1;
        B=[zeros(n,4); -E Mi*Bf];
        Z=zeros(2*n+4); Z(1:2*n,1:2*n)=A*dt; Z(1:2*n,2*n+1:end)=B*dt; Ez=expm(Z); cache(key)={Ez(1:2*n,1:2*n),Ez(1:2*n,2*n+1:end)};
    end
    AB=cache(key); F=P.cd(kap)*abs(vr).*vr;
    y(k,:)=[x(xt) x(yt) x(tt)];
    x=AB{1}*x+AB{2}*[ax(k); ay(k); F'];
end
end
function a=ang_(u,v)
if isempty(u), a=pi/4; else, a=atan2(max(abs(v)),max(abs(u))); end
end
function F=feats_(dt,hx,hy,gx,gy,th,thprev)
% Python features.py와 같은 13개 특징 (결정 시각까지의 관측만)
n1=round(1.3/dt); n2=round(2.6/dt); n5=round(5.2/dt); L=numel(hx);
i1=max(1,L-n1+1):L; i2=max(1,L-n2+1):L; i5=max(1,L-n5+1):L;
a13=ang_(hx(i1),hy(i1)); a26=ang_(hx(i2),hy(i2)); a52=ang_(hx(i5),hy(i5)); aall=ang_(hx,hy);
g13=ang_(gx(i1),gy(i1)); g26=ang_(gx(i2),gy(i2));
rx=sqrt(mean(hx(i2).^2)); ry=sqrt(mean(hy(i2).^2)); arms=atan2(ry,rx);
m13=max(max(abs(hx(i1))),max(abs(hy(i1)))); m26=max(max(abs(hx(i2))),max(abs(hy(i2))));
if m26>0, grow=m13/m26; else, grow=1; end
gm13=max(max(abs(gx(i1))),max(abs(gy(i1)))); gm26=max(max(abs(gx(i2))),max(abs(gy(i2))));
if gm26>0, ggrow=gm13/gm26; else, ggrow=1; end
t=min(L*dt,60)/60;
F=[a13 a26 a52 aall g13 g26 arms grow ggrow a26-thprev th t cos(2*a26)];
end
function o=mlp_(NN,F)
% sklearn MLPRegressor(32,32, tanh) 순전파. 출력은 각도(°)
z=(F-NN.mu)./NN.sd; h=tanh(z*NN.W1+NN.b1); h=tanh(h*NN.W2+NN.b2); o=h*NN.W3+NN.b3;
end
function v=met6(y)
s=[100 100 1e4]; a=abs(y).*s; r=sqrt(mean(y.^2,1)).*s; v=[max(a(:,1)) r(1) max(a(:,2)) r(2) max(a(:,3)) r(3)];
end
function d=delta_(lam,kap)
d1=(1-lam)^2+0.5*abs(1-lam); d2=((1-kap)+0.707*(1-kap)^0.375)^2*(1/kap)^2; d=d1+lam^2*d2;
end
function K=shear_(k)
n=numel(k); K=zeros(n); for i=1:n, K(i,i)=K(i,i)+k(i); if i<n, K(i,i)=K(i,i)+k(i+1); K(i,i+1)=-k(i+1); K(i+1,i)=-k(i+1); end, end
end
function T=readtab_(f)
fid=fopen(f,'r'); fgetl(fid); T.x={}; T.y={};
while true
    l=fgetl(fid); if ~ischar(l), break; end
    if isempty(strtrim(l)), continue; end
    c=strsplit(strtrim(l),','); T.x{end+1}=strtrim(c{end-1}); T.y{end+1}=strtrim(c{end});
end
fclose(fid);
end
function csvw_(f,h,M)
fid=fopen(f,'w'); fprintf(fid,'%s',h{1}); fprintf(fid,',%s',h{2:end}); fprintf(fid,'\n');
for i=1:size(M,1), fprintf(fid,'%.10g',M(i,1)); fprintf(fid,',%.10g',M(i,2:end)); fprintf(fid,'\n'); end
fclose(fid);
end
function [a,dt]=readAT2(f)
txt=fileread(f); L=regexp(txt,'\r?\n','split'); tok=regexp(L{4},'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)','tokens','once');
n=str2double(tok{1}); dt=str2double(tok{2}); v=sscanf(strjoin(L(5:end),' '),'%f'); a=v(1:n)*9.80665;
end
function M=fullM(mdx,mdy,P)
N=P.N; M=diag([P.m*ones(1,N) mdx P.m*ones(1,N) mdy P.J*ones(1,N)]);
end
function K=fullK(kdx,kdy,P)
N=P.N; S=shear_(P.kx); Kx=zeros(N+1); Kx(1:N,1:N)=S; Kx(N,N)=Kx(N,N)+kdx; Kx(N+1,N+1)=kdx; Kx(N,N+1)=-kdx; Kx(N+1,N)=-kdx;
Ky=zeros(N+1); Ky(1:N,1:N)=S; Ky(N,N)=Ky(N,N)+kdy; Ky(N+1,N+1)=kdy; Ky(N,N+1)=-kdy; Ky(N+1,N)=-kdy;
Kxt=zeros(N+1,N); Kxt(1:N,:)=S*P.ey; Kyt=zeros(N+1,N); Kyt(1:N,:)=S*P.ex;
n=3*N+2; K=zeros(n); K(1:N+1,1:N+1)=Kx; K(N+2:2*N+2,N+2:2*N+2)=Ky; K(2*N+3:end,2*N+3:end)=shear_(P.kt);
K(1:N+1,2*N+3:end)=Kxt; K(2*N+3:end,1:N+1)=Kxt'; K(N+2:2*N+2,2*N+3:end)=Kyt; K(2*N+3:end,N+2:2*N+2)=Kyt';
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
