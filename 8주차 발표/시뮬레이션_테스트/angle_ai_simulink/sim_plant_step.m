function xn=sim_plant_step(x,ag,u)
% Simulink 플랜트 블록이 매 스텝 호출: x_{k+1} = Ad(fq,thq) x_k + Bd [ag; F(kap, vr)]
% u = [fq; thq; kap; dt]
persistent cache P
if isempty(P), P=sim_params(); end
if isempty(cache), cache=containers.Map('KeyType','char','ValueType','any'); end
N=P.N; xt=N; xd=N+1; yt=2*N+1; yd=2*N+2; n=3*N+2; fq=u(1); thq=u(2); kap=u(3); dt=u(4);
key=sprintf('%.5f_%.4f_%g',fq,thq,dt);
if ~isKey(cache,key)
    if cache.Count>2000, cache=containers.Map('KeyType','char','ValueType','any'); end
    cc=max(cos(thq),0.02); ss=max(sin(thq),0.02); w2=(2*pi*fq)^2;
    M=fullM_(P.MD*cc,P.MD*ss,P); K=fullK_(P.MD*cc*w2*cc,P.MD*ss*w2*ss,P); C=P.a0*M+P.a1*K; Mi=inv(M);
    A=[zeros(n) eye(n); -Mi*K -Mi*C];
    E=zeros(n,2); E(1:N+1,1)=1; E(N+2:2*N+2,2)=1; Bf=zeros(n,2); Bf(xt,1)=1; Bf(xd,1)=-1; Bf(yt,2)=1; Bf(yd,2)=-1;
    B=[zeros(n,4); -E Mi*Bf];
    Z=zeros(2*n+4); Z(1:2*n,1:2*n)=A*dt; Z(1:2*n,2*n+1:end)=B*dt; Ez=expm(Z); cache(key)={Ez(1:2*n,1:2*n),Ez(1:2*n,2*n+1:end)};
end
AB=cache(key);
vt=[x(n+xt) x(n+yt)]; vd=[x(n+xd) x(n+yd)]; vr=vd-vt;
d1=(1-P.lam)^2+0.5*abs(1-P.lam); d2=((1-kap)+0.707*(1-kap)^0.375)^2*(1/kap)^2; cd=0.5*P.rho*P.Ah*(d1+P.lam^2*d2);
F=cd*abs(vr).*vr;
xn=AB{1}*x(:)+AB{2}*[ag(1); ag(2); F'];
end
function M=fullM_(mdx,mdy,P)
N=P.N; M=diag([P.m*ones(1,N) mdx P.m*ones(1,N) mdy P.J*ones(1,N)]);
end
function K=shear_(k)
n=numel(k); K=zeros(n); for i=1:n, K(i,i)=K(i,i)+k(i); if i<n, K(i,i)=K(i,i)+k(i+1); K(i,i+1)=-k(i+1); K(i+1,i)=-k(i+1); end, end
end
function K=fullK_(kdx,kdy,P)
N=P.N; S=shear_(P.kx); Kx=zeros(N+1); Kx(1:N,1:N)=S; Kx(N,N)=Kx(N,N)+kdx; Kx(N+1,N+1)=kdx; Kx(N,N+1)=-kdx; Kx(N+1,N)=-kdx;
Ky=zeros(N+1); Ky(1:N,1:N)=S; Ky(N,N)=Ky(N,N)+kdy; Ky(N+1,N+1)=kdy; Ky(N,N+1)=-kdy; Ky(N+1,N)=-kdy;
Kxt=zeros(N+1,N); Kxt(1:N,:)=S*P.ey; Kyt=zeros(N+1,N); Kyt(1:N,:)=S*P.ex;
n=3*N+2; K=zeros(n); K(1:N+1,1:N+1)=Kx; K(N+2:2*N+2,N+2:2*N+2)=Ky; K(2*N+3:end,2*N+3:end)=shear_(P.kt);
K(1:N+1,2*N+3:end)=Kxt; K(2*N+3:end,1:N+1)=Kxt'; K(N+2:2*N+2,2*N+3:end)=Kyt; K(2*N+3:end,N+2:2*N+2)=Kyt';
end
