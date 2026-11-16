function out = tlcd_sim(agx, agy, dt, opt)
% TLCD_SIM  Fu et al. (2025) 30층 양방향 편심 건물 + 수동 TLCD / S-TLCD / RS-TLCD — MATLAB 구현 (Python rstlcd.py 대조용).
%  opt.case  : 'none' | 'passive' | 'stlcd' | 'rstlcd'   (현재 'none','passive','stlcd','rstlcd')
%  opt.damp  : 'D0' (0.5*rho*Av^2/Ah, 식 24·8) | 'D3' (0.5*rho*Ah, 식 7) | 'D4' (0.5*rho*Av, 가정 하 유도 대안식)  -- c = 계수*delta(kappa,lam)*|dd|
%  opt.cos_twice : RS 전용. true=RA(식 20 문자 그대로, 강성에도 cosθ), false=RB(cosθ 한 번). 주파수 조절은 강성 변경을 통한 등가 구현(수위 물리 모델 아님).
%  감쇠 속도 dd = u_dx' - u_top' (장치 DOF 지반기준 좌표 미분 - 최상층 속도). 탱크 대비 수직관 액체 속도 D'와 같다고 "가정"한 것 (미검증).
%  출력: ux, uy, th (최상층)
G = 9.81; RHO = 1000;
N = 30; M_ST = 9.216e5; J_ST = 2.797e8;
K_XY = [1.021e9, 1.6213e9]; K_TH = [3.1651e11, 5.0261e11]; EX = 6.0; EY = 2.0; ZETA = 0.02;
F1 = 0.3373; F2 = 1.0112; F0 = 0.3373; KAPPA0 = 0.4; M_P = 463178.0; LAM_P = 0.231;
kxy = [K_XY(1), repmat(K_XY(2),1,N-1)]; kth = [K_TH(1), repmat(K_TH(2),1,N-1)];
Kx = shearK(kxy); Kt = shearK(kth); Ky = Kx; Z = zeros(N);
Ks = [Kx, Z, Kx*EY; Z, Ky, Ky*EX; Kx*EY, Ky*EX, Kt];
Ms = [repmat(M_ST,2*N,1); repmat(J_ST,N,1)];
w1 = 2*pi*F1; w2 = 2*pi*F2;
ab = [1/(2*w1), w1/2; 1/(2*w2), w2/2] \ [ZETA; ZETA];
Cs = ab(1)*diag(Ms) + ab(2)*Ks;
IX = 1:N; IDX = N+1; IY = N+2:2*N+1; IDY = 2*N+2; ITH = 2*N+3:3*N+2; ND = 3*N+2;
idx = [IX, IY, ITH];
K0 = zeros(ND); K0(idx,idx) = Ks; C0 = zeros(ND); C0(idx,idx) = Cs;
M0 = zeros(ND,1); M0(idx) = Ms;
E = zeros(ND,2); E([IX, IDX],1) = 1; E([IY, IDY],2) = 1;
tx = IX(end); ty = IY(end);
rs = strcmp(opt.case,'rstlcd');
if rs, MD = 694767.0; LAMD = 0.237; else, MD = M_P; LAMD = LAM_P; end
L0 = 2*G/(2*pi*F0)^2; Av = MD/(RHO*L0); Ah = Av/LAMD;
dlt = @(kap,lam) (1-lam)^2 + 0.5*abs(1-lam) + lam^2*((1-kap) + 0.707*(1-kap)^0.375)^2/kap^2;
switch opt.damp
    case 'D0', ccoef = 0.5*RHO*Av^2/Ah;
    case 'D3', ccoef = 0.5*RHO*Ah;
    case 'D4', ccoef = 0.5*RHO*Av;
    otherwise, error('unknown damp');
end
pas = strcmp(opt.case,'passive'); stl = strcmp(opt.case,'stlcd'); dev = pas || stl || rs;
if ~any(strcmp(opt.case,{'none','passive','stlcd','rstlcd'})), error('unknown case'); end
% S-TLCD 제어 상수 (원문 2.3절 설정, Python rstlcd.py와 동일 값)
FR = [0.3204, 0.3542]; KMIN = 0.1; KMAX = 0.8; DT_F = 2.6; DT_C = 1.0;
nF = round(DT_F/dt); nC = round(DT_C/dt);
wf = exp(linspace(log(0.1), log(2.0), 80))'; sig = 6.0./(2*pi*wf);   % 웨이블릿: 과거 샘플만 쓰는 반쪽 Morlet
nw = ceil(3*max(sig)/dt); tau = (0:nw-1)*dt;
gk = exp(-tau.^2./(2*sig.^2)); gk(tau > 3*sig) = 0;
Wm = gk .* exp(1i*2*pi*wf*tau) ./ sum(gk,2);
fx_ = F0; fy_ = F0; kx_ = KAPPA0; ky_ = KAPPA0; rampx = []; rampy = [];
f_cmd = zeros(0,3); k_cmd = zeros(0,3); minmargin = inf; th_cmd = zeros(0,2); fr_ = F0; kr_ = KAPPA0; rampr = []; theta = 0; th_tgt = 0; ROT = 30*pi/180; DT_TH = 2.6; nTH = round(DT_TH/dt); thetas = zeros(numel(agx),1);
FXd = zeros(0,1); 
nt = numel(agx); u = zeros(ND,1); v = zeros(ND,1); a = zeros(ND,1);
ux = zeros(nt,1); uy = zeros(nt,1); th = zeros(nt,1);
fxs = zeros(nt,1); fys = zeros(nt,1); kxs = zeros(nt,1); kys = zeros(nt,1);
for i = 0:nt-2
    ii = i+1; t = i*dt;
    if stl && i > 0
        % 적용 순서(Python과 동일): 진동수 명령 -> κ 갱신 -> 진동수 이동(램프) -> 행렬 조립
        if mod(i,nF) == 0
            [fxc, m1] = widf(ux(1:i)); [fyc, m2] = widf(uy(1:i)); minmargin = min([minmargin, m1, m2]);
            fxc = min(max(fxc,FR(1)),FR(2)); fyc = min(max(fyc,FR(1)),FR(2));
            f_cmd(end+1,:) = [i, fxc, fyc]; %#ok<AGROW>
            rampx = [t, fx_, fxc]; rampy = [t, fy_, fyc];
        end
        if mod(i,nC) == 0
            accx = a(tx) + agx(ii); accy = a(ty) + agy(ii);
            sx = (v(IDX)-v(tx))*accx > 0; sy = (v(IDY)-v(ty))*accy > 0;
            if sx, kx_ = KMIN; else, kx_ = KMAX; end
            if sy, ky_ = KMIN; else, ky_ = KMAX; end
            k_cmd(end+1,:) = [i, kx_, ky_]; %#ok<AGROW>
        end
    end
    if rs && i > 0
        if mod(i,nF) == 0
            [fxc, m1] = widf(ux(1:i)); [fyc, m2] = widf(uy(1:i)); minmargin = min([minmargin, m1, m2]);
            fxc = min(max(fxc,FR(1)),FR(2)); fyc = min(max(fyc,FR(1)),FR(2));
            Dx = abs(ux(i)); Dy = abs(uy(i));
            if Dx+Dy > 0, ft = (Dy*fyc + Dx*fxc)/(Dx+Dy); else, ft = F0; end
            ftc = min(max(ft,FR(1)),FR(2)); f_cmd(end+1,:) = [i, ft, ftc]; %#ok<AGROW>
            rampr = [t, fr_, ftc];
        end
        if mod(i,nTH) == 0
            j0 = max(0, i-nTH);
            th_tgt = atan2(max(abs(uy(j0+1:i))), max(abs(ux(j0+1:i)))); th_cmd(end+1,:) = [i, th_tgt]; %#ok<AGROW>
        end
        if mod(i,nC) == 0
            accx = a(tx) + agx(ii); accy = a(ty) + agy(ii);
            sx = (v(IDX)-v(tx))*accx > 0; sy = (v(IDY)-v(ty))*accy > 0;
            if ~(sx || sy), kr_ = KMAX; elseif (sx && sy), kr_ = KMIN; else, kr_ = KAPPA0; end
            k_cmd(end+1,:) = [i, kr_, 0]; %#ok<AGROW>
        end
    end
    if rs
        if ~isempty(rampr), r = min(1.0,(t-rampr(1))/DT_F); fr_ = rampr(2)+(rampr(3)-rampr(2))*r; if r >= 1.0, rampr = []; end, end
        theta = theta + min(max(th_tgt-theta, -ROT*dt), ROT*dt);
    end
    if stl
        if ~isempty(rampx), r = min(1.0,(t-rampx(1))/DT_F); fx_ = rampx(2)+(rampx(3)-rampx(2))*r; if r >= 1.0, rampx = []; end, end
        if ~isempty(rampy), r = min(1.0,(t-rampy(1))/DT_F); fy_ = rampy(2)+(rampy(3)-rampy(2))*r; if r >= 1.0, rampy = []; end, end
    end
    Mv = M0; Mv(IDX) = 1; Mv(IDY) = 1; K = K0; K(IDX,IDX) = 1; K(IDY,IDY) = 1; C = C0;
    if rs
        c_ = abs(cos(theta)); s_ = abs(sin(theta)); mxx = MD*max(c_,1e-6); myy = MD*max(s_,1e-6); w2d = (2*pi*fr_)^2;
        if opt.cos_twice, kdx = mxx*w2d*c_; kdy = myy*w2d*s_; else, kdx = mxx*w2d; kdy = myy*w2d; end
        cdx = ccoef*dlt(kr_,LAMD)*abs(v(IDX)-v(tx)); cdy = ccoef*dlt(kr_,LAMD)*abs(v(IDY)-v(ty)); Mv(IDX) = mxx; Mv(IDY) = myy;
    elseif dev
        if pas, fx_ = F0; fy_ = F0; kx_ = KAPPA0; ky_ = KAPPA0; end
        kdx = M_P*(2*pi*fx_)^2; kdy = M_P*(2*pi*fy_)^2;   % k = m*(2*pi*f)^2, 질량·Av·Ah·유효길이는 f 변경과 무관하게 고정
        cdx = ccoef*dlt(kx_,LAM_P)*abs(v(IDX)-v(tx)); cdy = ccoef*dlt(ky_,LAM_P)*abs(v(IDY)-v(ty));
        Mv(IDX) = M_P; Mv(IDY) = M_P;
    end
    if dev
        K([tx IDX],[tx IDX]) = K([tx IDX],[tx IDX]) + [kdx, -kdx; -kdx, kdx-1];
        K([ty IDY],[ty IDY]) = K([ty IDY],[ty IDY]) + [kdy, -kdy; -kdy, kdy-1];
        C([tx IDX],[tx IDX]) = C([tx IDX],[tx IDX]) + [cdx, -cdx; -cdx, cdx];
        C([ty IDY],[ty IDY]) = C([ty IDY],[ty IDY]) + [cdy, -cdy; -cdy, cdy];
    end
    p = -Mv .* (E*[agx(ii+1); agy(ii+1)]);
    A = diag(Mv) + 0.5*dt*C + 0.25*dt^2*K;
    rhs = p - C*(v + 0.5*dt*a) - K*(u + dt*v + 0.25*dt^2*a);
    a1 = A \ rhs;
    u = u + dt*v + 0.25*dt^2*(a + a1); v = v + 0.5*dt*(a + a1); a = a1;
    ux(ii+1) = u(tx); uy(ii+1) = u(ty); th(ii+1) = u(ITH(end));
    if rs, fxs(ii+1) = fr_; kxs(ii+1) = kr_; thetas(ii+1) = theta; else, fxs(ii+1) = fx_; fys(ii+1) = fy_; kxs(ii+1) = kx_; kys(ii+1) = ky_; end
end
out = struct('ux',ux,'uy',uy,'th',th,'fx',fxs,'fy',fys,'kx',kxs,'ky',kys,'f_cmd',f_cmd,'k_cmd',k_cmd,'th_cmd',th_cmd,'theta',thetas,'minmargin',minmargin);

    function [fr, margin] = widf(hist)
        seg = zeros(nw,1); m = min(nw, numel(hist));
        if m > 0, h = flipud(hist(:)); seg(1:m) = h(1:m); end
        mag = abs(Wm*seg); [srt, ord] = sort(mag,'descend'); fr = wf(ord(1));
        margin = (srt(1)-srt(2))/max(srt(1),realmin);
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
