function [ok, R] = predict_response(P, CS, cand, fcv, g)
% PREDICT_RESPONSE  후보 지령의 미래 응답 예측 (제어기 내부 모델, 도착한 정보만 사용).
%  시작 상태 : 가장 최근 도착 관측 시각 s의 상태 사본(이상적 상태정보)과 장치 상태
%  지반 입력 : s 이후는 예측 파형만 사용 (기준시각 o, o+r, …, o+Hn·r 사이 선형 보간; o 시점은 관측값)
%  지령      : 이미 보낸 지령(적용 스텝 ≥ s) + 후보 지령(스텝 g에 적용)
%             g 이후 밸브 격자: cand.k_mode='law'면 원문 밸브 법칙(모의 상태 즉시), 숫자면 그 κ 유지
%             g 이후 펌프·각도 격자: 후보 유지 (첫 지령만 실행하는 반복 구조)
%  출력 R.ux, R.uy, R.th : 평가 구간(스텝 g+1 … o+Hn·r) 최상층 응답
rt = P.rt; r = rt.r; Hn = rt.Hn;
ok = false; R = struct('ux', [], 'uy', [], 'th', [], 'th_all', [], 'reason', '');
o = fcv(2); tend = o + r*Hn; s = CS.s;
if (tend - g)*P.dt < rt.min_eval_s - 1e-9
    R.reason = 'horizon'; return;
end
% 지반 입력 (스텝 s+1 … tend)
Yx = fcv(4:3+Hn); Yy = fcv(4+Hn:3+2*Hn);
gx = [CS.Hm(1, o+1); Yx(:)]; gy = [CS.Hm(2, o+1); Yy(:)];
q = (s+1:tend)';
pos = (q - o)/r;                           % 0 … Hn (격자 단위)
j0 = floor(pos); fr = pos - j0; j1 = min(j0 + 1, Hn);
agx = gx(j0+1).*(1-fr) + gx(j1+1).*fr; agy = gy(j0+1).*(1-fr) + gy(j1+1).*fr;
ag_at = @(k) [agx(k - s); agy(k - s)];      % 스텝 k (> s)의 예측 지반가속도
% 이미 보낸 지령
pend = CS.issued(CS.issued(:,1) >= s, :);
S = CS.xs; A = CS.As;
n = tend - s; ux = zeros(n,1); uy = ux; th = ux;
for k = s:tend-1
    rel = zeros(6,1);
    hit = find(pend(:,1) == k);
    for h = hit(:)'
        c = pend(h, 2:7);
        if c(1) > 0.5, rel(1:2) = c(1:2)'; end
        if c(3) > 0.5, rel(3:4) = c(3:4)'; end
        if c(5) > 0.5, rel(5:6) = c(5:6)'; end
    end
    if k == g
        if ~isnan(cand.f),  rel(1:2) = [1; cand.f];  end
        if ~isnan(cand.th), rel(3:4) = [1; cand.th]; end
        if isnumeric(cand.k_mode) && cand.k_exec, rel(5:6) = [1; cand.k_mode]; end
    end
    if k >= g && mod(k, P.nC) == 0 && k > 0 && isempty(hit) && ~(k == g && rel(5) > 0.5)
        if isnumeric(cand.k_mode)
            rel(5:6) = [1; cand.k_mode];
        else
            if k == s, agk = CS.Hm(1:2, s+1); else, agk = ag_at(k); end
            accx = S.a(P.tx) + agk(1); accy = S.a(P.ty) + agk(2);
            sx = (S.v(P.IDX) - S.v(P.tx))*accx > 0; sy = (S.v(P.IDY) - S.v(P.ty))*accy > 0;
            if ~(sx || sy), kv = P.KMAX; elseif (sx && sy), kv = P.KMIN; else, kv = P.KAPPA0; end
            rel(5:6) = [1; kv];
        end
    end
    [A, dev] = actuator_step(A, rel, k, P);
    S = plant_step(S, ag_at(k+1), dev, P, true);
    ux(k-s+1) = S.u(P.tx); uy(k-s+1) = S.u(P.ty); th(k-s+1) = S.u(P.tth);
end
w = (g+1:tend) - s;                        % 평가 구간 인덱스
R.ux = ux(w); R.uy = uy(w); R.th = th(w);
R.th_all = th;                             % 스텝 s+1 … tend 전체 (그림자 R 누적 비틀림 제한용)
if any(~isfinite([R.ux; R.uy; R.th])), R.reason = 'nan'; return; end
ok = true;
end
