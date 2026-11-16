% 6주차 교차검증: 파이썬 시뮬레이터(sim.py)와 같은 지배방정식을 MATLAB(ode45)으로 독립 구현해 비교
% 실행: 이 파일과 ref.csv 가 있는 폴더에서  w6_crosscheck
function w6_crosscheck
N=6; G=9.81; F1=0.872; MEFF=1382.1e3; MU=0.005; ALPHA=0.6; LT=4.0; YMAX=0.8;
GAM=0.95; XIOPT=6; zeta=0.02;
% --- 건물 (전단건물, 층질량/강성 균등, 1차 모드질량 MEFF 맞춤)
K0=zeros(N); for i=1:N, K0(i,i)=K0(i,i)+1; if i>1, K0(i,i-1)=-1; K0(i-1,i)=-1; K0(i-1,i-1)=K0(i-1,i-1)+1; end, end
[V,D]=eig(K0); [w2,ix]=sort(diag(D)); ph=V(:,ix(1)); phi=ph/ph(end);
m=MEFF*(phi'*phi)/(sum(phi)^2); w1=2*pi*F1; k=w1^2*m/w2(1);
M0=m*eye(N); Kb=k*K0;
% --- Rayleigh 감쇠 (1,2차 모드)
wn=sqrt(sort(eig(Kb,M0))); a0=2*zeta*wn(1)*wn(2)/(wn(1)+wn(2)); a1=2*zeta/(wn(1)+wn(2));
Cb=a0*M0+a1*Kb;
ref=readmatrix('ref.csv'); out=zeros(size(ref,1),6);
for r=1:size(ref,1)
  A=ref(r,1); xi=ref(r,2);
  if xi==0, mf=1e-3; xv=XIOPT; else, mf=MU*MEFF; xv=xi; end
  e=zeros(N,1); e(end)=1;
  Mc=zeros(N+1); Mc(1:N,1:N)=M0+mf*(e*e'); Mc(1:N,N+1)=ALPHA*mf*e; Mc(N+1,1:N)=ALPHA*mf*e'; Mc(N+1,N+1)=mf;
  kf=mf*(GAM*w1)^2; cnl=0.5*mf/LT; Rg=(M0+mf*(e*e'))*ones(N,1);
  Tp=1.0;
  ag=@(t) (t<Tp/2)*A*G*sin(2*pi*t/Tp);
  f=@(t,x) rhs(t,x);
  opts=odeset('RelTol',1e-9,'AbsTol',1e-12,'MaxStep',0.0025);
  t=(0:0.0025:24)'; x0=zeros(2*N+2,1);
  [~,X]=ode45(f,t,x0,opts);
  roof=X(:,N); y=X(:,2*N+1);
  out(r,:)=[A xi max(abs(roof)) sqrt(mean(roof(2:end).^2)) max(abs(y)) 0];
end
% ---- 비교 출력
fprintf('A(g)  xi   roof peak(m) MATLAB/파이썬   roof RMS(m) MATLAB/파이썬   y peak(m) MATLAB/파이썬\n');
for r=1:size(ref,1)
  fprintf('%.1f  %2d   %.5f / %.5f (%+.2f%%)   %.5f / %.5f (%+.2f%%)   %.4f / %.4f (%+.2f%%)\n',ref(r,1),ref(r,2),...
   out(r,3),ref(r,3),100*(out(r,3)/ref(r,3)-1),out(r,4),ref(r,4),100*(out(r,4)/ref(r,4)-1),out(r,5),ref(r,5),100*(out(r,5)/ref(r,5)-1));
end
writematrix(out(:,1:5),'matlab_result.csv');
disp('저장: matlab_result.csv');
  function dx=rhs(t,x)
    q=x(1:N); qd=x(N+1:2*N); y=x(2*N+1); yd=x(2*N+2);
    s=zeros(N+1,1);
    s(1:N)=-(Cb*qd+Kb*q)-Rg*ag(t);
    stop=0; if y>YMAX, stop=100*kf*(y-YMAX); elseif y<-YMAX, stop=100*kf*(y+YMAX); end
    s(N+1)=-xv*cnl*abs(yd)*yd-kf*y-stop-ALPHA*mf*ag(t);
    acc=Mc\s;
    dx=[qd; acc(1:N); yd; acc(N+1)];
  end
end
