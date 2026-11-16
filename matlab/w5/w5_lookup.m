function LT = w5_lookup(p, tl, recs, scenario)
%W5_LOOKUP  예측 PGA → 최적 (기준 손실계수 xib, 튜닝비 gamma) 설정표.
%
%   경보가 오면 제어기는 "예측 PGA" 하나만 압니다(어느 지진인지는 모름).
%   그래서 설정표는 기록 여러 개 평균으로 만듭니다.
%     목적   평균 RMS 변위 저감률 최대
%     제약   모든 기록에서 스트로크 이용률 <= 1 (물기둥 한계 이내)
%            만족하는 조합이 없으면 최대 스트로크가 가장 작은 조합

LT.pga   = 0.1:0.1:1.2;             % 예보 2배 과대(0.6g → 1.2g)까지 포함
LT.xi    = 2.^(-2:6);              % 0.25 ~ 64
LT.gamma = p.gamma_range(1):0.02:p.gamma_range(2);

nP = numel(LT.pga); nX = numel(LT.xi); nG = numel(LT.gamma); nR = numel(recs);
LT.red    = zeros(nP,nX,nG);       % 평균 저감률 [%]
LT.stroke = zeros(nP,nX,nG);       % 기록 중 최대 스트로크 이용률

LT.scenario = scenario;
for ip = 1:nP
    b = w5_building(p, LT.pga(ip), scenario);
    U = zeros(1,nR);  AG = cell(1,nR);
    for r = 1:nR
        [AG{r}, t] = w5_record(recs{r}, LT.pga(ip), p.dt, p.T, p.axes);  t = t(:)';
        U(r) = w5_simulate(p,b,tl,t,AG{r},[],[],false).rms_disp;
    end
    N = numel(t);
    for ix = 1:nX
        for ig = 1:nG
            red = zeros(1,nR);  su = zeros(1,nR);
            for r = 1:nR
                o = w5_simulate(p,b,tl,t,AG{r}, LT.gamma(ig)*ones(1,N), LT.xi(ix)*ones(1,N), true);
                red(r) = 100*(1 - o.rms_disp/U(r));  su(r) = o.stroke_use;
            end
            LT.red(ip,ix,ig) = mean(red);  LT.stroke(ip,ix,ig) = max(su);
        end
    end
    R = squeeze(LT.red(ip,:,:));  S = squeeze(LT.stroke(ip,:,:));
    if any(S(:) <= 1), R(S > 1) = -Inf; [~,k] = max(R(:)); else, [~,k] = min(S(:)); end
    [ix, ig] = ind2sub([nX nG], k);
    LT.best_xi(ip) = LT.xi(ix);  LT.best_gamma(ip) = LT.gamma(ig);
    LT.best_red(ip) = LT.red(ip,ix,ig);  LT.best_stroke(ip) = LT.stroke(ip,ix,ig);
    fprintf('PGA %.1fg : xi=%5.2f gamma=%.2f  red=%5.1f%%  stroke=%.2f\n', ...
        LT.pga(ip), LT.best_xi(ip), LT.best_gamma(ip), LT.best_red(ip), LT.best_stroke(ip));
end
end
