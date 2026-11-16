function [P, S] = plant_init(cfg, dt)
% PLANT_INIT  30층 양방향 편심 건물 + RS-TLCD 상수(P)와 초기 상태(S).
%  식·상수는 code/matlab/rstlcd_sim.m(MATLAB R2026a 구현 대조 15/15 통과본)과 같다.
%  P : 불변 행렬·장치 상수·갱신 격자(스텝)·R 법칙용 웨이블릿
%  S : 플랜트 내부 상태 u, v, a (92x1). 평가기·이상적 상태추정기만 직접 읽는다.
if nargin < 2 || isempty(dt), dt = cfg.plant.dt; end
P = struct();
P.dt = dt; P.c_scale = cfg.plant.c_scale;
P.G = 9.81; P.RHO = 1000;
N = 30; M_ST = 9.216e5; J_ST = 2.797e8;
K_XY = [1.021e9, 1.6213e9]; K_TH = [3.1651e11, 5.0261e11]; EX = 6.0; EY = 2.0; ZETA = 0.02;
F1 = 0.3373; F2 = 1.0112;
P.M_RS = 694767.0;
dv = cfg.device;
P.F0 = dv.f0_hz; P.FR = dv.f_range_hz(:)';
P.KAPPA0 = dv.kappa0; P.KMIN = min(dv.kappa_set); P.KMAX = max(dv.kappa_set); P.LAM = 0.237;
P.DT_F = dv.pump_ramp_s; P.ROT = dv.rot_rate_deg_s*pi/180;
P.TH_RANGE = dv.theta_range_deg(:)'*pi/180;
P.nF = round(dv.grid_pump_s/dt); P.nTH = round(dv.grid_angle_s/dt); P.nC = round(dv.grid_valve_s/dt);
% ---- 건물 (3N 자유도) ----
kxy = [K_XY(1), repmat(K_XY(2),1,N-1)]; kth = [K_TH(1), repmat(K_TH(2),1,N-1)];
Kx = shear_k(kxy); Kt = shear_k(kth); Ky = Kx; Z = zeros(N);
Ks = [Kx, Z, Kx*EY; Z, Ky, Ky*EX; Kx*EY, Ky*EX, Kt];
Ms = [repmat(M_ST,2*N,1); repmat(J_ST,N,1)];
w1 = 2*pi*F1; w2 = 2*pi*F2;
ab = [1/(2*w1), w1/2; 1/(2*w2), w2/2] \ [ZETA; ZETA];
Cs = ab(1)*diag(Ms) + ab(2)*Ks;
% ---- 전체 92 자유도: [x1..x30, xd, y1..y30, yd, th1..th30] ----
P.N = N;
P.IX = 1:N; P.IDX = N+1; P.IY = N+2:2*N+1; P.IDY = 2*N+2; P.ITH = 2*N+3:3*N+2; P.ND = 3*N+2;
idx = [P.IX, P.IY, P.ITH];
P.K0 = zeros(P.ND); P.K0(idx,idx) = Ks; P.C0 = zeros(P.ND); P.C0(idx,idx) = Cs;
P.M0 = zeros(P.ND,1); P.M0(idx) = Ms;
P.E = zeros(P.ND,2); P.E([P.IX, P.IDX],1) = 1; P.E([P.IY, P.IDY],2) = 1;
P.tx = P.IX(end); P.ty = P.IY(end); P.tth = P.ITH(end);
% 장치와 무관한 Newmark 행렬 (장치 자리는 단위 질량·강성 자리표시; plant_step이 장치 블록만 더함)
P.Mb = P.M0; P.Mb(P.IDX) = 1; P.Mb(P.IDY) = 1;
P.Kb = P.K0; P.Kb(P.IDX,P.IDX) = 1; P.Kb(P.IDY,P.IDY) = 1;
P.Ab = diag(P.Mb) + 0.5*dt*P.C0 + 0.25*dt^2*P.Kb;
% 장치 상수
P.L0 = 2*P.G/(2*pi*P.F0)^2; P.Av = P.M_RS/(P.RHO*P.L0); P.Ah = P.Av/P.LAM;
% 웨이블릿 (반쪽 Morlet, 과거 샘플만) — R 법칙(원문 식 10-11)의 진동수 식별
P.wf = exp(linspace(log(0.1), log(2.0), 80))'; sig = 6.0./(2*pi*P.wf);
P.nw = ceil(3*max(sig)/dt); tau = (0:P.nw-1)*dt;
gk = exp(-tau.^2./(2*sig.^2)); gk(tau > 3*sig) = 0;
P.W = gk .* exp(1i*2*pi*P.wf*tau) ./ sum(gk,2);
% 확인용 매개변수 (run_validation.m 항목과 같은 정의)
[~,D] = eig(Ks, diag(Ms)); fn = sort(sqrt(abs(diag(D))))/2/pi;
P.params = struct('f123', fn(1:3)', 'rayleigh_a', ab(1), 'rayleigh_b', ab(2), 'Av', P.Av, 'Ah', P.Ah, 'L0', P.L0, ...
    'delta', [tlcd_delta(P,0.1), tlcd_delta(P,0.4), tlcd_delta(P,0.8)]);
S = struct('u', zeros(P.ND,1), 'v', zeros(P.ND,1), 'a', zeros(P.ND,1), 'i', 0);
end

function K = shear_k(k)
n = numel(k); K = zeros(n);
for i = 1:n
    K(i,i) = K(i,i) + k(i);
    if i < n
        K(i,i) = K(i,i) + k(i+1); K(i,i+1) = -k(i+1); K(i+1,i) = -k(i+1);
    end
end
end
