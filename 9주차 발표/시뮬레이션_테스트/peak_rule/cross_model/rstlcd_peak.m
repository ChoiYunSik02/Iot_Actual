function out = rstlcd_peak(agx, agy, dt, opt)
% RSTLCD_SIM  Fu et al. (2025) 30층 양방향 편심 건물 + RS-TLCD — MATLAB 독립 구현 (모델 검증용).
%  Python 엔진(rstlcd.py + rstlcd_cos2.py)과 같은 원문 식을 다시 작성. 선형계는 매 스텝 92x92 직접 풀이.
%  opt.case  : 'none' | 'rstlcd'
%  opt.fpol  : 'law' (원문 식 10-11) | 'const' (opt.fval [Hz])
%  opt.thpol : 'law' (원문 식 13) | 'const' (opt.thval [rad]) | 'switch' (opt.i_d 스텝 전 law, 이후 opt.thval)
%  opt.c_scale (기본 30)
%  출력: ux, uy, th (최상층), f_dev, theta, kappa, f_cmd/th_cmd ([스텝 i, 목표값] 행), params
if ~isfield(opt,'c_scale'), opt.c_scale = 30; end
G = 9.81; RHO = 1000;
N = 30; M_ST = 9.216e5; J_ST = 2.797e8;
K_XY = [1.021e9, 1.6213e9]; K_TH = [3.1651e11, 5.0261e11]; EX = 6.0; EY = 2.0; ZETA = 0.02;
F1 = 0.3373; F2 = 1.0112;
M_RS = 694767.0; F0 = 0.3373; FR = [0.3204, 0.3542];
KAPPA0 = 0.4; KMIN = 0.1; KMAX = 0.8; LAM = 0.237;
DT_F = 2.6; DT_C = 1.0; DT_TH = 2.6; ROT = 30*pi/180;
% ---- 건물 (3N 자유도) ----
kxy = [K_XY(1), repmat(K_XY(2),1,N-1)]; kth = [K_TH(1), repmat(K_TH(2),1,N-1)];
Kx = shearK(kxy); Kt = shearK(kth); Ky = Kx; Z = zeros(N);
Ks = [Kx, Z, Kx*EY; Z, Ky, Ky*EX; Kx*EY, Ky*EX, Kt];
Ms = [repmat(M_ST,2*N,1); repmat(J_ST,N,1)];
w1 = 2*pi*F1; w2 = 2*pi*F2;
ab = [1/(2*w1), w1/2; 1/(2*w2), w2/2] \ [ZETA; ZETA];
Cs = ab(1)*diag(Ms) + ab(2)*Ks;
% ---- 전체 92 자유도: [x1..x30, xd, y1..y30, yd, th1..th30] ----
IX = 1:N; IDX = N+1; IY = N+2:2*N+1; IDY = 2*N+2; ITH = 2*N+3:3*N+2; ND = 3*N+2;
idx = [IX, IY, ITH];
K0 = zeros(ND); K0(idx,idx) = Ks; C0 = zeros(ND); C0(idx,idx) = Cs;
M0 = zeros(ND,1); M0(idx) = Ms;
E = zeros(ND,2); E([IX, IDX],1) = 1; E([IY, IDY],2) = 1;
tx = IX(end); ty = IY(end);
% 장치 상수
L0 = 2*G/(2*pi*F0)^2; Av = M_RS/(RHO*L0); Ah = Av/LAM;
dlt = @(kap) (1-LAM)^2 + 0.5*abs(1-LAM) + LAM^2*((1-kap) + 0.707*(1-kap)^0.375)^2/kap^2;
% 웨이블릿 (반쪽 Morlet, 과거 샘플만)
wf = exp(linspace(log(0.1), log(2.0), 80))'; sig = 6.0./(2*pi*wf);
nw = ceil(3*max(sig)/dt); tau = (0:nw-1)*dt;
gk = exp(-tau.^2./(2*sig.^2)); gk(tau > 3*sig) = 0;
W = gk .* exp(1i*2*pi*wf*tau) ./ sum(gk,2);
% ---- 상태 ----
nt = numel(agx); u = zeros(ND,1); v = zeros(ND,1); a = zeros(ND,1);
rs = strcmp(opt.case,'rstlcd');
r1 = 0; r2 = 0; rmax = 0; f = F0; kap = KAPPA0; theta = 0; th_tgt = 0;
ramp = []; % [t0, f0, f1]
nF = round(DT_F/dt); nC = round(DT_C/dt); nTH = round(DT_TH/dt);
ux = zeros(nt,1); uy = zeros(nt,1); th = zeros(nt,1); fd = zeros(nt,1); thd = zeros(nt,1); kd = zeros(nt,1);
f_cmd = zeros(0,2); th_cmd = zeros(0,2);
for i = 0:nt-2
    t = i*dt; ii = i+1;  % ii: MATLAB 1-기준 인덱스 (현재 스텝 i)
    if rs && i > 0
        if mod(i,nF) == 0
            if strcmp(opt.fpol,'law')
                fx = min(max(wid(ux(1:i)),FR(1)),FR(2)); fy = min(max(wid(uy(1:i)),FR(1)),FR(2));
                Dx = abs(ux(i)); Dy = abs(uy(i));
                if Dx+Dy > 0, ft = (Dy*fy + Dx*fx)/(Dx+Dy); else, ft = F0; end
            else
                ft = opt.fval;
            end
            f_cmd(end+1,:) = [i, ft]; %#ok<AGROW>
            ramp = [t, f, min(max(ft,FR(1)),FR(2))];
        end
        if mod(i,nTH) == 0 && ~strcmp(opt.thpol,'peak')
            usel = strcmp(opt.thpol,'law') || (strcmp(opt.thpol,'switch') && i < opt.i_d);
            if usel
                j0 = max(0, i-round(DT_TH/dt));
                th_tgt = atan2(max(abs(uy(j0+1:i))), max(abs(ux(j0+1:i))));
            else
                th_tgt = opt.thval;
            end
            th_cmd(end+1,:) = [i, th_tgt]; %#ok<AGROW>
        end
        if strcmp(opt.thpol,'peak')
            r_ = hypot(ux(ii), uy(ii));
            if i >= 2 && r1 > r2 && r_ < r1 && r1 >= 0.3*rmax
                phi = atan2(abs(uy(ii-1)), abs(ux(ii-1))); th_tgt = pi/4 + 0.5*(phi - pi/4);
            end
            rmax = max(rmax, r_); r2 = r1; r1 = r_;
        end
        if mod(i,nC) == 0
            accx = a(tx) + agx(ii); accy = a(ty) + agy(ii);
            sx = (v(IDX)-v(tx))*accx > 0; sy = (v(IDY)-v(ty))*accy > 0;
            if ~(sx || sy), kap = KMAX; elseif (sx && sy), kap = KMIN; else, kap = KAPPA0; end
        end
    end
    if ~isempty(ramp)
        r = min(1.0, (t-ramp(1))/DT_F); f = ramp(2) + (ramp(3)-ramp(2))*r;
        if r >= 1.0, ramp = []; end
    end
    if rs
        dth = min(max(th_tgt-theta, -ROT*dt), ROT*dt); theta = theta + dth;
    end
    % ---- 행렬 조립 ----
    Mv = M0; Mv(IDX) = 1; Mv(IDY) = 1; K = K0; K(IDX,IDX) = 1; K(IDY,IDY) = 1; C = C0;
    if rs
        c_ = abs(cos(theta)); s_ = abs(sin(theta));
        mx = M_RS*max(c_,1e-6); my = M_RS*max(s_,1e-6); w2d = (2*pi*f)^2;
        kx = mx*w2d*c_; ky = my*w2d*s_;
        cdx = opt.c_scale*0.5*RHO*Av^2/Ah*dlt(kap)*abs(v(IDX)-v(tx));
        cdy = opt.c_scale*0.5*RHO*Av^2/Ah*dlt(kap)*abs(v(IDY)-v(ty));
        Mv(IDX) = mx; Mv(IDY) = my;
        K([tx IDX],[tx IDX]) = K([tx IDX],[tx IDX]) + [kx, -kx; -kx, kx-1];
        K([ty IDY],[ty IDY]) = K([ty IDY],[ty IDY]) + [ky, -ky; -ky, ky-1];
        C([tx IDX],[tx IDX]) = C([tx IDX],[tx IDX]) + [cdx, -cdx; -cdx, cdx];
        C([ty IDY],[ty IDY]) = C([ty IDY],[ty IDY]) + [cdy, -cdy; -cdy, cdy];
    end
    p = -Mv .* (E*[agx(ii+1); agy(ii+1)]);
    A = diag(Mv) + 0.5*dt*C + 0.25*dt^2*K;
    rhs = p - C*(v + 0.5*dt*a) - K*(u + dt*v + 0.25*dt^2*a);
    a1 = A \ rhs;
    u = u + dt*v + 0.25*dt^2*(a + a1); v = v + 0.5*dt*(a + a1); a = a1;
    ux(ii+1) = u(tx); uy(ii+1) = u(ty); th(ii+1) = u(ITH(end));
    if rs, fd(ii+1) = f; kd(ii+1) = kap; thd(ii+1) = theta; end
end
out = struct('ux',ux,'uy',uy,'th',th,'f_dev',fd,'theta',thd,'kappa',kd,'f_cmd',f_cmd,'th_cmd',th_cmd);
[~,D] = eig(Ks, diag(Ms)); fn = sort(sqrt(abs(diag(D))))/2/pi;
out.params = struct('f123', fn(1:3)', 'rayleigh_a', ab(1), 'rayleigh_b', ab(2), 'Av', Av, 'Ah', Ah, 'L0', L0, 'delta', [dlt(0.1), dlt(0.4), dlt(0.8)]);

    function fr = wid(hist)
        seg = zeros(nw,1); m = min(nw, numel(hist));
        if m > 0, h = flipud(hist(:)); seg(1:m) = h(1:m); end
        [~, k] = max(abs(W*seg)); fr = wf(k);
    end
end

function K = shearK(k)
n = numel(k); K = zeros(n);
for i = 1:n
    K(i,i) = K(i,i) + k(i);
    if i < n
        K(i,i) = K(i,i) + k(i+1); K(i,i+1) = -k(i+1); K(i+1,i) = -k(i+1);
    end
end
end
