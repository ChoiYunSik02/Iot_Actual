function run_v2b_check(datadir, outdir)
% Python v2b와 같은 정의로 무제어·수동 TLCD·S-TLCD(Morlet, 즉시 적용)를 독립 구현해 15기록 지표를 CSV로 쓴다.
% 같은 사람이 작성한 코드이므로 "같은 식을 두 언어가 같게 계산하는지"만 확인한다(원문과 같다는 뜻이 아님).
% 사용: run_v2b_check('C:\Users\cys\Desktop\iot-actuator-week08\peer_records_table2', ...
%                    'C:\Users\cys\Desktop\iot-actuator-week08\reproduction_v2b')
if nargin<1, datadir='C:\Users\cys\Desktop\iot-actuator-week08\peer_records_table2'; end
if nargin<2, outdir=fileparts(mfilename('fullpath')); end
T=readtable(fullfile(datadir,'records_table2.csv'),'TextType','string');
N=30; m=9.216e5; J=2.797e8; kx=1.6213e9*ones(N,1); kx(1)=1.021e9; kt=5.0261e11*ones(N,1); kt(1)=3.1651e11;
ex=6; ey=2; MD=463178; F0=0.3373; g=9.81; rho=1000; lam=0.231;
L0=2*g/(2*pi*F0)^2; Av=MD/(rho*L0); Ah=Av/lam;
cd=@(kap) 0.5*rho*Ah*delta_(lam,kap);
Ks=@(k) shear_(k);
% ---- 건물(식 19 문자 그대로)
Kb=zeros(3*N); Kb(1:N,1:N)=Ks(kx); Kb(N+1:2*N,N+1:2*N)=Ks(kx); Kb(2*N+1:end,2*N+1:end)=Ks(kt);
Kb(1:N,2*N+1:end)=Ks(kx)*ey; Kb(2*N+1:end,1:N)=Ks(kx)*ey; Kb(N+1:2*N,2*N+1:end)=Ks(kx)*ex; Kb(2*N+1:end,N+1:2*N)=Ks(kx)*ex;
Mb=diag([m*ones(1,2*N), J*ones(1,N)]);
rows=[]; CL=[];
for r=1:height(T)
    [ax,dt]=readAT2(fullfile(datadir,T.x_file(r))); [ay,~]=readAT2(fullfile(datadir,T.y_file(r)));
    n=min(numel(ax),numel(ay)); x=ax(1:n)*0.35/max(abs(ax)); y=ay(1:n)*0.35/max(abs(ay));
    % 무제어
    [Ad,Bd]=zohd(Mb,Kb,rayleigh(Mb,Kb),[eyeE(N,0)],dt,'unc');
    yu=simlin(Ad,Bd,[x y],[N 2*N 3*N]);
    % 수동/S-TLCD: 자유도 순서 X층30, X장치, Y층30, Y장치, θ층30
    kd=MD*(2*pi*F0)^2; M=fullM(MD,MD,m,J,N); Kf=fullK(kd,kd,kx,kt,ex,ey,N); C=rayleigh(M,Kf);
    yp=simdev(M,C,kx,kt,ex,ey,N,MD,x,y,dt,cd,'passive');
    [ys,lg]=simdev(M,C,kx,kt,ex,ey,N,MD,x,y,dt,cd,'stlcd');
    CL=[CL; r*ones(size(lg,1),1) lg]; %#ok<AGROW>
    rows=[rows; r, met(yu), met(yp), met(ys)]; %#ok<AGROW>
    fprintf('rec %d done\n',r);
end
hdr={'no'}; for c={'unc','pas','stl'}, for s={'Xmax','Xrms','Ymax','Yrms','thmax','thrms'}, hdr{end+1}=[c{1} '_' s{1}]; end, end %#ok<AGROW>
writetable(array2table(rows,'VariableNames',hdr),fullfile(outdir,'matlab_v2b_metrics.csv'));
writetable(array2table(CL,'VariableNames',{'rec','type','step0','t','v1','v2'}),fullfile(outdir,'matlab_v2b_cmdlog.csv'));
% type 1 = 진동수 명령(Hz), 2 = kappa 명령. step0 = 0부터 센 시간 스텝 번호
fprintf('MATLAB_V2B_DONE\n');
end
function v=met(y)
s=[100 100 1e4]; a=abs(y).*s; r=sqrt(mean(y.^2,1)).*s; v=[max(a(:,1)) r(1) max(a(:,2)) r(2) max(a(:,3)) r(3)];
end
function d=delta_(lam,kap)
d1=(1-lam)^2+0.5*abs(1-lam); d2=((1-kap)+0.707*(1-kap)^0.375)^2*(1/kap)^2; d=d1+lam^2*d2;
end
function K=shear_(k)
n=numel(k); K=zeros(n); for i=1:n, K(i,i)=K(i,i)+k(i); if i<n, K(i,i)=K(i,i)+k(i+1); K(i,i+1)=-k(i+1); K(i+1,i)=-k(i+1); end, end
end
function [a,dt]=readAT2(f)
txt=fileread(f); L=splitlines(txt); tok=regexp(L{4},'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)','tokens','once');
n=str2double(tok{1}); dt=str2double(tok{2}); v=sscanf(strjoin(L(5:end)',' '),'%f'); a=v(1:n)*9.80665;
end
function C=rayleigh(M,K)
w2=sort(eig(K,M)); w=sqrt(w2(1:2)); ab=[1/(2*w(1)) w(1)/2; 1/(2*w(2)) w(2)/2]\[0.02;0.02]; C=ab(1)*M+ab(2)*K;
end
function E=eyeE(N,~)
E=zeros(3*N,2); E(1:N,1)=1; E(N+1:2*N,2)=1;
end
function [Ad,Bd]=zohd(M,K,C,E,dt,~)
n=size(M,1); Mi=inv(M); A=[zeros(n) eye(n); -Mi*K -Mi*C]; B=[zeros(n,size(E,2)); -E];
Z=zeros(2*n+size(B,2)); Z(1:2*n,1:2*n)=A*dt; Z(1:2*n,2*n+1:end)=B*dt; Ez=expm(Z); Ad=Ez(1:2*n,1:2*n); Bd=Ez(1:2*n,2*n+1:end);
end
function y=simlin(Ad,Bd,u,idx)
x=zeros(size(Ad,1),1); T=size(u,1); y=zeros(T,3);
for k=1:T, y(k,:)=x(idx)'; x=Ad*x+Bd*u(k,:)'; end
end
function M=fullM(mdx,mdy,m,J,N)
M=diag([m*ones(1,N) mdx m*ones(1,N) mdy J*ones(1,N)]);
end
function K=fullK(kdx,kdy,kx,kt,ex,ey,N)
S=shear_(kx); Kx=zeros(N+1); Kx(1:N,1:N)=S; Kx(N,N)=Kx(N,N)+kdx; Kx(N+1,N+1)=kdx; Kx(N,N+1)=-kdx; Kx(N+1,N)=-kdx;
Ky=zeros(N+1); Ky(1:N,1:N)=S; Ky(N,N)=Ky(N,N)+kdy; Ky(N+1,N+1)=kdy; Ky(N,N+1)=-kdy; Ky(N+1,N)=-kdy;
Kxt=zeros(N+1,N); Kxt(1:N,:)=S*ey; Kyt=zeros(N+1,N); Kyt(1:N,:)=S*ex;
n=3*N+2; K=zeros(n); K(1:N+1,1:N+1)=Kx; K(N+2:2*N+2,N+2:2*N+2)=Ky; K(2*N+3:end,2*N+3:end)=shear_(kt);
K(1:N+1,2*N+3:end)=Kxt; K(2*N+3:end,1:N+1)=Kxt'; K(N+2:2*N+2,2*N+3:end)=Kyt; K(2*N+3:end,N+2:2*N+2)=Kyt';
end
function [y,lg]=simdev(M,C,kx,kt,ex,ey,N,MD,ax,ay,dt,cd,mode)
xt=N; xd=N+1; yt=2*N+1; yd=2*N+2; tt=3*N+2; n=3*N+2;
E=zeros(n,2); E(1:N+1,1)=1; E(N+2:2*N+2,2)=1; Bf=zeros(n,2); Bf(xt,1)=1; Bf(xd,1)=-1; Bf(yt,2)=1; Bf(yd,2)=-1;
Mi=inv(M); B=[zeros(n,4); -E Mi*Bf]; cache=containers.Map('KeyType','char','ValueType','any');
F0=0.3373; f=[F0 F0]; kap=[0.4 0.4]; nf=round(2.6/dt); nc=round(1/dt);
x=zeros(2*n,1); T=numel(ax); y=zeros(T,3); hx=zeros(T,1); hy=zeros(T,1); vprev=[0 0]; lg=zeros(0,5);
for k=1:T
    vtop=[x(n+xt) x(n+yt)]; if k>1, acc=(vtop-vprev)/dt; else, acc=[0 0]; end; vprev=vtop;
    vrel=[x(n+xd)-x(n+xt) x(n+yd)-x(n+yt)]; hx(k)=x(xt); hy(k)=x(yt);
    if strcmp(mode,'stlcd')
        if k>1 && mod(k-1,nf)==0
            f(1)=min(max(ident_(hx(1:k),dt),0.3204),0.3542); f(2)=min(max(ident_(hy(1:k),dt),0.3204),0.3542);
            lg(end+1,:)=[1 k-1 (k-1)*dt f(1) f(2)]; %#ok<AGROW>
        end
        if k>1 && mod(k-1,nc)==0
            aa=acc+[ax(k) ay(k)]; for j=1:2, if vrel(j)*aa(j)>0, kap(j)=0.1; else, kap(j)=0.8; end, end
            lg(end+1,:)=[2 k-1 (k-1)*dt kap(1) kap(2)]; %#ok<AGROW>
        end
    end
    key=sprintf('%.5f_%.5f',f(1),f(2));
    if ~isKey(cache,key)
        K=fullK(MD*(2*pi*f(1))^2,MD*(2*pi*f(2))^2,kx,kt,ex,ey,N); A=[zeros(n) eye(n); -Mi*K -Mi*C];
        Z=zeros(2*n+4); Z(1:2*n,1:2*n)=A*dt; Z(1:2*n,2*n+1:end)=B*dt; Ez=expm(Z); cache(key)={Ez(1:2*n,1:2*n),Ez(1:2*n,2*n+1:end)};
    end
    AB=cache(key); F=[cd(kap(1)) cd(kap(2))].*abs(vrel).*vrel;
    y(k,:)=[x(xt) x(yt) x(tt)]; x=AB{1}*x+AB{2}*[ax(k); ay(k); F'];
end
end
function fr=ident_(sig,dt)
% Python stlcd.ident('morlet')와 같은 정의: 과거 쪽 Morlet(ω0=6) 계수 크기 × sqrt(f) 최대
if numel(sig)<8, fr=0.3373; return; end
F=linspace(0.05,2.0,391); t=(0:numel(sig)-1)'*dt; tk=t(end); mags=zeros(size(F));
for i=1:numel(F)
    f=F(i); sd=6/(2*pi*f); msk=t>=tk-4*sd; tau=t(msk)-tk;
    psi=exp(-1i*2*pi*f*tau).*exp(-tau.^2/(2*sd^2)); mags(i)=abs(sum(sig(msk).*psi))*dt*sqrt(f);
end
[~,ix]=max(mags); fr=F(ix);
end
