function P=sim_params()
% 30층 편심 건물 + RS-TLCD 파라미터 (run_angle_ai_check.m과 동일)
persistent PP
if isempty(PP)
P.N=30; P.m=9.216e5; P.J=2.797e8; P.kx=1.6213e9*ones(P.N,1); P.kx(1)=1.021e9; P.kt=5.0261e11*ones(P.N,1); P.kt(1)=3.1651e11;
P.ex=6; P.ey=2; P.MD=694767; P.F0=0.3373; g=9.81; rho=1000; P.lam=0.237;
L0=2*g/(2*pi*P.F0)^2; Av=P.MD/(rho*L0); P.Ah=Av/P.lam; P.rho=rho;
w2=(2*pi*P.F0)^2; Mn=fullM_(P.MD,P.MD,P); Kn=fullK_(P.MD*w2,P.MD*w2,P);
ev=sort(eig(Kn,Mn)); w=sqrt(ev(1:2)); ab=[1/(2*w(1)) w(1)/2; 1/(2*w(2)) w(2)/2]\[0.02;0.02]; P.a0=ab(1); P.a1=ab(2);
PP=P;
end
P=PP;
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
