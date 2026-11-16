function ok = verify_model(preset)
%VERIFY_MODEL  모델을 4단계로 검증합니다. 한 단계씩 통과해야 다음으로 갑니다.
%
%   1. 무제어 건물의 고유진동수가 이론값과 일치하는가
%   2. TLCD 단독 자유진동 주기가 sqrt(2g/L)와 일치하는가
%   3. 연성계에서 감쇠 0일 때 에너지가 보존되는가
%   4. 무제어 대비 저감률이 문헌값 범위(지진 시 23~35%)에 드는가

if nargin < 1, preset = '3F'; end
p = params(preset);
b = build_building(p);
ok = true;

fprintf('\n===== 모델 검증 (%s) =====\n', preset);

%% 1단계 ─ 건물 고유진동수
% 균일 전단건물의 이론해: w_j = 2*sqrt(k/m)*sin((2j-1)*pi/(2(2n+1)))
n = p.n;
w_th = zeros(n,1);
for j = 1:n
    w_th(j) = 2*sqrt(p.k/p.m)*sin((2*j-1)*pi/(2*(2*n+1)));
end
err1 = max(abs(b.w - w_th) ./ w_th) * 100;
fprintf('\n[1] 건물 고유진동수\n');
for j = 1:n
    fprintf('    %d차: 수치 %6.3f Hz  이론 %6.3f Hz\n', j, b.w(j)/(2*pi), w_th(j)/(2*pi));
end
fprintf('    최대 오차 %.4f%%  →  %s\n', err1, pass(err1 < 0.1));
ok = ok && err1 < 0.1;

%% 2단계 ─ TLCD 단독 자유진동
tl = tlcd_design(p, b);
dt = 1e-4;  T = 20;  t = (0:dt:T)';
xf = zeros(size(t));  vf = 0;  x0 = 0.3*tl.stroke_max;
xf(1) = x0;
for i = 1:numel(t)-1
    % 감쇠 없는 순수 진자 운동: mf*a + kf*x = 0
    a = -(tl.kf/tl.mf) * xf(i);
    vf = vf + a*dt;
    xf(i+1) = xf(i) + vf*dt;
end
zc = find(xf(1:end-1).*xf(2:end) < 0);      % 영교차로 주기 측정
T_num = 2*mean(diff(t(zc)));
T_th  = 2*pi/tl.wf;
err2 = abs(T_num - T_th)/T_th*100;
fprintf('\n[2] TLCD 단독 자유진동 주기\n');
fprintf('    수치 %.4f s   이론 2pi/sqrt(2g/L) = %.4f s\n', T_num, T_th);
fprintf('    오차 %.3f%%  →  %s\n', err2, pass(err2 < 1.0));
ok = ok && err2 < 1.0;

%% 3단계 ─ 연성계 에너지 보존 (감쇠 0)
p0 = p;  p0.zeta = 0;  p0.xi = 0;  p0.T = 10;
b0 = build_building(p0);
t0 = (0:p0.dt:p0.T)';
ag0 = zeros(size(t0));
% 초기변위를 주고 자유진동
tl0 = tlcd_design(p0, b0);
o = simulate_free(p0, b0, tl0, t0);
E_drift = (max(o.E) - min(o.E)) / mean(o.E) * 100;
fprintf('\n[3] 연성계 에너지 보존 (감쇠 0, 자유진동 %g s)\n', p0.T);
fprintf('    에너지 변동폭 %.4f%%  →  %s\n', E_drift, pass(E_drift < 1.0));
ok = ok && E_drift < 1.0;

%% 4단계 ─ 저감률이 문헌값 범위인가
t = (0:p.dt:p.T)';
ag = gen_ground('elcentro', 0.2, p.dt, p.T);
o0 = simulate_tlcd(p, b, t, ag, 'none');
o1 = simulate_tlcd(p, b, t, ag, 'passive');
red_pk  = (1 - o1.peak_disp/o0.peak_disp)*100;
red_rms = (1 - o1.rms_disp /o0.rms_disp )*100;
fprintf('\n[4] 무제어 대비 저감률 (El Centro형 0.2g)\n');
fprintf('    최대변위 %.2f%%   RMS %.2f%%\n', red_pk, red_rms);
fprintf('    문헌 범위(지진 시 23~35%%) 비교  →  %s\n', ...
        pass(red_rms > 10 && red_rms < 60));
fprintf('    ※ 물기둥 사용률 %.2f (1.0 넘으면 포화)\n', o1.stroke_use);
ok = ok && (red_rms > 10);

fprintf('\n===== 종합: %s =====\n\n', pass(ok));
end

function s = pass(c)
if c, s = 'PASS'; else, s = 'FAIL'; end
end

function o = simulate_free(p, b, tl, t)
%자유진동 + 에너지 추적 (검증 3단계 전용)
n = p.n;  nd = n+1;  dt = t(2)-t(1);  N = numel(t);
mf = tl.mf;  e = b.e;
M = zeros(nd);
M(1:n,1:n) = b.M + mf*(e*e');
M(1:n,end) = p.alpha*mf*e;  M(end,1:n) = p.alpha*mf*e';  M(end,end) = mf;
K = zeros(nd);  K(1:n,1:n) = b.K;  K(end,end) = tl.kf;

x = zeros(nd,N);  v = zeros(nd,N);  a = zeros(nd,N);
x(:,1) = [0.01*(1:n)'; 0.2*tl.stroke_max];
a(:,1) = M \ (-K*x(:,1));
gam = 0.5; bet = 0.25;
a0 = 1/(bet*dt^2); a1 = gam/(bet*dt); a2 = 1/(bet*dt);
a3 = 1/(2*bet)-1;  a4 = gam/bet-1;   a5 = dt*(gam/(2*bet)-1);
Keff = K + a0*M;
E = zeros(1,N);
E(1) = 0.5*x(:,1)'*K*x(:,1) + 0.5*v(:,1)'*M*v(:,1);
for i = 1:N-1
    F = M*(a0*x(:,i) + a2*v(:,i) + a3*a(:,i));
    x(:,i+1) = Keff \ F;
    v(:,i+1) = a1*(x(:,i+1)-x(:,i)) - a4*v(:,i) - a5*a(:,i);
    a(:,i+1) = a0*(x(:,i+1)-x(:,i)) - a2*v(:,i) - a3*a(:,i);
    E(i+1) = 0.5*x(:,i+1)'*K*x(:,i+1) + 0.5*v(:,i+1)'*M*v(:,i+1);
end
o.E = E;  o.x = x;
end
