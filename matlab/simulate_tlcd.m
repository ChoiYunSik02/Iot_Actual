function out = simulate_tlcd(p, b, t, ag, mode)
%SIMULATE_TLCD  건물-TLCD 연성계를 Newmark-beta 법으로 시간적분합니다.
%
%   out = simulate_tlcd(p, b, t, ag, mode)
%
%   mode : 'none'       무제어 (건물만)
%          'passive'    고정 오리피스 TLCD
%          'semiactive' 밸브 조절형 TLCD (지연 반영)
%
%   지배방정식 (최상층 설치, n자유도 건물 + 액체 1자유도)
%
%     (Ms + mf·e·e')·xdd + alpha·mf·e·xfdd + Cs·xd + Ks·x = -(Ms + mf·e·e')·r·agg
%      alpha·mf·e'·xdd  + mf·xfdd + 0.5·rho·A·xi·|xfd|·xfd + 2·rho·A·g·xf
%                                                          = -alpha·mf·agg
%
%   비선형 감쇠항 때문에 매 스텝 고정점 반복으로 수렴시킵니다.
%   포화는 하드스톱 페널티(강성 k_stop × kf)로 모델링합니다.

n  = p.n;
N  = numel(t);
dt = t(2) - t(1);

useTLCD = ~strcmpi(mode, 'none');

if useTLCD
    tl = tlcd_design(p, b);
    nd = n + 1;
    mf = tl.mf;  A = tl.A;  kf = tl.kf;
    e  = b.e;

    M = zeros(nd);
    M(1:n,1:n) = b.M + mf*(e*e');
    M(1:n,end) = p.alpha*mf*e;
    M(end,1:n) = p.alpha*mf*e';
    M(end,end) = mf;

    K = zeros(nd);  K(1:n,1:n) = b.K;  K(end,end) = kf;
    C0 = zeros(nd); C0(1:n,1:n) = b.C;

    Lvec = [-(b.M + mf*(e*e'))*b.r; -p.alpha*mf];
    kstop = p.k_stop * kf;
    % 유효 스트로크 한계: 기하학적 한계와 사용자 지정 한계 중 작은 값
    slim = min(tl.stroke_max, p.stroke_limit);
else
    tl = struct('stroke_max', Inf, 'mf', 0, 'L', NaN, 'B', NaN, 'h', NaN, ...
                'A', NaN, 'wf', NaN, 'f', NaN, 'd', NaN, 'kf', NaN);
    nd = n;
    M  = b.M;  K = b.K;  C0 = b.C;
    Lvec = -b.M * b.r;
    kstop = 0;
    slim  = Inf;
    A = NaN;
end

% Newmark 평균가속도법
gam = 0.5;  bet = 0.25;
a0 = 1/(bet*dt^2);  a1 = gam/(bet*dt);
a2 = 1/(bet*dt);    a3 = 1/(2*bet) - 1;
a4 = gam/bet - 1;   a5 = dt*(gam/(2*bet) - 1);

x = zeros(nd,N);  v = zeros(nd,N);  acc = zeros(nd,N);
xi_hist = zeros(1,N);
sat     = false(1,N);

xi_cur = p.xi;
xi_hist(1) = xi_cur;

F1 = Lvec * ag(1);
acc(:,1) = M \ (F1 - C0*v(:,1) - K*x(:,1));

nlag = max(0, round(p.delay/dt));

for i = 1:N-1
    % ── 준능동 밸브 제어 (지연된 계측값 사용) ────────────
    if useTLCD && strcmpi(mode,'semiactive')
        j = max(1, i - nlag);
        vtop = v(n, j);        % 최상층 속도 (지연)
        vf   = v(end, j);      % 물기둥 속도 (지연)
        % on-off 그라운드훅형: 물기둥이 건물과 반대로 움직이면 밸브를 열어
        % 에너지 전달을 키우고, 같은 방향이면 닫아 감쇠를 키운다.
        if vtop * vf < 0
            xi_cur = p.xi_lo;
        else
            xi_cur = p.xi_hi;
        end
    end
    xi_hist(i+1) = xi_cur;

    Fn = Lvec * ag(i+1);

    % 고정점 반복 (비선형 감쇠 + 하드스톱)
    vg = v(:,i);   % 초기 추정
    xg = x(:,i);
    for it = 1:6
        C = C0;
        Fs = zeros(nd,1);
        if useTLCD
            C(end,end) = 0.5*p.rho*A*xi_cur*abs(vg(end));
            ov = abs(xg(end)) - slim;
            if ov > 0
                Fs(end) = -kstop * ov * sign(xg(end));
            end
        end
        Keff = K + a1*C + a0*M;
        Feff = Fn + Fs ...
             + M*(a0*x(:,i) + a2*v(:,i) + a3*acc(:,i)) ...
             + C*(a1*x(:,i) + a4*v(:,i) + a5*acc(:,i));
        xn = Keff \ Feff;
        vn = a1*(xn - x(:,i)) - a4*v(:,i) - a5*acc(:,i);
        if max(abs(vn - vg)) < 1e-10 * max(1, max(abs(vn)))
            xg = xn; vg = vn; break;
        end
        xg = xn; vg = vn;
    end

    x(:,i+1) = xg;
    v(:,i+1) = vg;
    acc(:,i+1) = a0*(xg - x(:,i)) - a2*v(:,i) - a3*acc(:,i);

    if useTLCD
        sat(i+1) = abs(xg(end)) >= slim*0.999;
    end
end

%% ── 출력 ────────────────────────────────────────────────
out.t   = t;
out.x   = x(1:n,:);
out.v   = v(1:n,:);
out.acc_abs = acc(1:n,:) + ag(:)';         % 절대가속도
out.top     = x(n,:);
out.mode    = mode;
out.tlcd    = tl;

out.peak_disp = max(abs(out.top));
out.rms_disp  = sqrt(mean(out.top.^2));   % rms()는 Signal Processing Toolbox 필요
out.peak_acc  = max(abs(out.acc_abs(n,:)));

if useTLCD
    out.xf         = x(end,:);
    out.vf         = v(end,:);
    out.peak_xf    = max(abs(out.xf));
    out.stroke_max = slim;
    out.stroke_use = out.peak_xf / out.stroke_max;   % 1.0 이상이면 포화
    out.sat_ratio  = mean(sat);
    out.xi_hist    = xi_hist;
else
    out.xf = []; out.peak_xf = NaN; out.stroke_use = NaN;
    out.sat_ratio = NaN; out.stroke_max = NaN;
end

end
