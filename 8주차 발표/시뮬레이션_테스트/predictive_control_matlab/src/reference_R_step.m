function val = reference_R_step(kind, Hm, s, P)
% REFERENCE_R_STEP  기존 응답 기반 제어 R (원문 식 10-13), 도착한 관측만 사용.
%  kind : 'f' (펌프 진동수, 식 10-11) | 'th' (회전각, 식 13) | 'kappa' (밸브, 식 12)
%  Hm   : 관측 이력 (9 x nmax), 열 j = 측정 시각 스텝 j-1 (plant_measure 순서). 도착하지 않은 열은 NaN.
%  s    : 결정 시점에 도착한 가장 최근 측정 스텝
%  rstlcd_sim.m과 같은 인덱스를 쓴다: 진동수·각도 법칙은 스텝 s-1까지, 밸브 법칙은 스텝 s의 값.
%  (지연 0이면 s = 결정 스텝 i이고 rstlcd_sim.m과 같은 계산이 된다.)
switch kind
    case 'f'
        ux = Hm(3, 1:s); uy = Hm(4, 1:s);           % 스텝 0..s-1
        fx = min(max(wid(ux, P), P.FR(1)), P.FR(2)); fy = min(max(wid(uy, P), P.FR(1)), P.FR(2));
        Dx = abs(ux(end)); Dy = abs(uy(end));
        if Dx + Dy > 0, val = (Dy*fy + Dx*fx)/(Dx + Dy); else, val = P.F0; end
    case 'th'
        j0 = max(0, s - P.nTH);
        val = atan2(max(abs(Hm(4, j0+1:s))), max(abs(Hm(3, j0+1:s))));
    case 'kappa'
        m = Hm(:, s+1);
        sx = m(8)*m(6) > 0; sy = m(9)*m(7) > 0;
        if ~(sx || sy), val = P.KMAX; elseif (sx && sy), val = P.KMIN; else, val = P.KAPPA0; end
    otherwise
        error('reference_R_step: kind %s', kind);
end
end

function fr = wid(hist, P)
seg = zeros(P.nw,1); m = min(P.nw, numel(hist));
if m > 0, h = flipud(hist(:)); seg(1:m) = h(1:m); end
[~, k] = max(abs(P.W*seg)); fr = P.wf(k);
end
