function out = w5_simulate(p, b, tl, t, ag, gam, xib, useTLCD)
%W5_SIMULATE  6층 건물 + 밀폐형 TLCD(준능동 밸브) 시간이력해석.
%
%   gam(t), xib(t) : 매 스텝의 튜닝비 · 기준 손실계수 (길이 N 벡터)
%                    → 펌프/공기압/밸브 사전 동작으로 시간에 따라 변할 수 있음
%   useTLCD        : false 면 무제어 건물만
%
%   밸브 제어 — Ocean Eng. 2025 의 Δ-DBG 규칙과 2배/0.6배 범위를 그대로 사용
%     (최상층 변위 증분) × (물기둥 속도) <= 0  →  xi = 2.0 × xib   (감쇠 최대)
%                                         > 0  →  xi = 0.6 × xib   (감쇠 최소)
%
%   액체 방정식 (밀폐형: 복원강성 = 중력 + 공기스프링, 합계를 튜닝비로 지정)
%     a·mf·e'·xdd + mf·xfdd + ½ρA·xi·|xfd|·xfd + kf(t)·xf = −a·mf·ag
%     kf(t) = mf·(gam(t)·w1d)^2    (w1d = 설계 시점 건물 1차 각진동수)

%   2축(ag 가 N×2): 비편심 건물이라 X·Y 를 따로 풀고 합성합니다 (4주차와 같은 방식).
%     각 축에 같은 TLCD(μ 0.5%) · 같은 설정 → 합성 변위 r = sqrt(x² + y²)
%     rms_disp · peak_disp 는 r 기준, stroke_use 는 두 축 중 큰 값
if size(ag,2) == 2
    ox = w5_simulate(p, b, tl, t, ag(:,1), gam, xib, useTLCD);
    oy = w5_simulate(p, b, tl, t, ag(:,2), gam, xib, useTLCD);
    r  = hypot(ox.top, oy.top);
    out.top = r;  out.topX = ox.top;  out.topY = oy.top;
    out.rms_disp   = sqrt(mean(r.^2));
    out.peak_disp  = max(r);
    out.stroke_use = max(ox.stroke_use, oy.stroke_use);
    return
end

n = p.n;  N = numel(t);  dt = t(2) - t(1);

if useTLCD
    nd = n + 1;  mf = tl.mf;  a = tl.alpha;  e = b.e;
    M = zeros(nd);
    M(1:n,1:n) = b.M + mf*(e*e');
    M(1:n,end) = a*mf*e;   M(end,1:n) = a*mf*e';   M(end,end) = mf;
    K0 = zeros(nd);  K0(1:n,1:n) = b.K;
    C0 = zeros(nd);  C0(1:n,1:n) = b.C;
    Lvec = [-(b.M + mf*(e*e'))*b.r; -a*mf];
    kf = mf * (gam(:)' * p.w1d).^2;
    cA = 0.5 * p.rho * tl.A;
else
    nd = n;  M = b.M;  K0 = b.K;  C0 = b.C;  Lvec = -b.M*b.r;
end

gm = 0.5;  bt = 0.25;
a0 = 1/(bt*dt^2);  a1 = gm/(bt*dt);  a2 = 1/(bt*dt);
a3 = 1/(2*bt) - 1; a4 = gm/bt - 1;  a5 = dt*(gm/(2*bt) - 1);

x = zeros(nd,N);  v = zeros(nd,N);  acc = zeros(nd,N);
K = K0;  if useTLCD, K(end,end) = kf(1); end
acc(:,1) = M \ (Lvec*ag(1) - C0*v(:,1) - K*x(:,1));
xi_hist = zeros(1,N);

for i = 1:N-1
    if useTLCD
        K(end,end) = kf(i+1);
        dx = x(n,i) - x(n,max(1,i-1));
        if dx * v(end,i) <= 0, xi = 2.0*xib(i); else, xi = 0.6*xib(i); end
        xi_hist(i) = xi;
        kstop = tl.k_stop * kf(i+1);
    end
    Fn = Lvec * ag(i+1);
    xg = x(:,i);  vg = v(:,i);
    for it = 1:6
        C = C0;  Fs = zeros(nd,1);
        if useTLCD
            C(end,end) = cA * xi * abs(vg(end));
            ov = abs(xg(end)) - tl.stroke;
            if ov > 0, Fs(end) = -kstop*ov*sign(xg(end)); end
        end
        Keff = K + a1*C + a0*M;
        Feff = Fn + Fs + M*(a0*x(:,i) + a2*v(:,i) + a3*acc(:,i)) ...
                       + C*(a1*x(:,i) + a4*v(:,i) + a5*acc(:,i));
        xn = Keff \ Feff;
        vn = a1*(xn - x(:,i)) - a4*v(:,i) - a5*acc(:,i);
        done = max(abs(vn - vg)) < 1e-9 * max(1, max(abs(vn)));
        xg = xn;  vg = vn;
        if done, break; end
    end
    x(:,i+1) = xg;  v(:,i+1) = vg;
    acc(:,i+1) = a0*(xg - x(:,i)) - a2*v(:,i) - a3*acc(:,i);
end

top = x(n,:);
out.top       = top;
out.rms_disp  = sqrt(mean(top.^2));      % rms() 는 툴박스 함수라 직접 계산
out.peak_disp = max(abs(top));
if useTLCD
    out.xf         = x(end,:);
    out.stroke_use = max(abs(out.xf)) / tl.stroke;   % 1 이상 = 한계 도달
    out.xi_hist    = xi_hist;
else
    out.stroke_use = NaN;
end
end
