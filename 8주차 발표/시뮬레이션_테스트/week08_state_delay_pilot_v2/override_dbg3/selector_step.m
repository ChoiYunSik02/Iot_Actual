function [CS, cmdv] = selector_step(CS, estv, fcv, i, P)
persistent ss_; if isempty(ss_), ss_ = 1; fprintf('SS_LOADED_FROM=%s mode=%s\n', mfilename('fullpath'), CS.mode); end
% SELECTOR_STEP  지령 선택 (R / FIX / C1 / C2). 도착한 관측·준비된 예측·자신이 보낸 지령만 쓴다.
%  결정 시각: 장치 갱신 격자 g에 적용되도록 g − d_cmd 스텝에 결정한다(d_cmd = 연산·통신·추가 지연).
%  C1 : 펌프·회전판 후보(최대 9 + R) 비교, 밸브는 원문 법칙
%  C2 : 펌프·각도 갱신에서 (f,θ,κ) 최대 27 + R, 사이의 밸브 갱신에서 κ 3 + R
%  예측 없음·지평 부족·NaN·비틀림 만족 후보 없음·계산 기한 초과 → R 지령
%  cmdv = [has_any; has_f; f; has_th; th; has_k; kappa; apply_step]
%  estv : StateEstimator 출력 (sensor_step obsv와 같은 형식)
rt = P.rt;
cmdv = zeros(8,1);
% ---- 관측 반영 ----
if estv(1) > 0.5
    s = estv(2);
    CS.Hm(:, s+1) = estv(3:11);
    CS.s = s;
    CS.xs = struct('u', estv(12:103), 'v', estv(104:195), 'a', estv(196:287), 'i', s);
    CS.As = act_unpack(estv(288:296));
    if s > CS.qs_last                              % 실제 최상층 비틀림 누적 (도착한 관측 시각까지)
        tq = CS.xs.u(P.tth); CS.Qa = CS.Qa + tq^2; CS.Ma = max(CS.Ma, abs(tq)); CS.qs_last = s;
        ux_ = CS.xs.u(P.tx); uy_ = CS.xs.u(P.ty);  % X·Y 누적 (J 상태 특징용)
        CS.Qx = CS.Qx + ux_^2; CS.Mx = max(CS.Mx, abs(ux_)); CS.Qy = CS.Qy + uy_^2; CS.My = max(CS.My, abs(uy_));
    end
end
if strcmp(CS.mode, 'U') || CS.s < 1, return; end
if strcmp(CS.mode, 'J')
    [CS, cmdv] = j_ontime(CS, fcv, i, P);
    return;
end
if strcmp(CS.mode, 'C1') && strcmp(CS.dpath, 'ontime')
    [CS, cmdv] = c1_ontime(CS, fcv, i, P);
    return;
end
g = i + rt.d_cmd;
isP = g > 0 && mod(g, P.nF) == 0;
isV = g > 0 && mod(g, P.nC) == 0;
if ~(isP || isV), return; end
s = CS.s;
t0 = tic;
f = NaN; th = NaN; k = NaN; reason = ''; info = nan(1,6); Dg = [];   % info = [origin ready n_cand n_feasible J_best J_R]
% R 지령 (모든 방식의 기준·복귀값). 계산 시간을 따로 잰다(복귀 지령의 도착 시각 판단).
if isP, fR = reference_R_step('f', CS.Hm, s, P); thR = reference_R_step('th', CS.Hm, s, P); else, fR = NaN; thR = NaN; end
if isV, kR = reference_R_step('kappa', CS.Hm, s, P); else, kR = NaN; end
wall_R = toc(t0);
switch CS.mode
    case 'R'
        f = fR; th = thR; k = kR;
    case 'FIX'
        if isP, f = CS.fix_f; th = CS.fix_th; end
        k = kR;
    case {'C1', 'C2'}
        if strcmp(CS.mode, 'C1')
            k = kR;
            if isV, CS = issue(CS, NaN, NaN, kR, g); end     % 같은 격자의 밸브 지령을 먼저 등록 (예측에 반영)
        end
        doP = isP; doV = strcmp(CS.mode, 'C2') && isV;
        if doP || doV
            [sel, reason, info, Dg] = choose(CS, fcv, g, isP, isV, fR, thR, kR, P);
            if isempty(sel)
                if doP, f = fR; th = thR; end
                if doV, k = kR; end
            else
                if doP, f = sel.f; th = sel.th; end
                if doV, k = sel.k_mode; if ~isnumeric(k), k = kR; end, end
            end
        end
        if strcmp(CS.mode, 'C1') && isV
            k = NaN;   % 이미 등록함
        end
end
wall = toc(t0) + rt.inject_select_s;
% 도착 시각: 결정 시각 + 실측 계산시간 + 통신·추가 지연. 계산 중에도 플랜트는 진행한다(결정은 g - d_cmd에 시작).
t_arr = i*P.dt + wall + rt.comm_extra_s;
t_arrR = i*P.dt + wall_R + rt.inject_select_s*~any(strcmp(CS.mode, {'C1', 'C2'})) + rt.comm_extra_s;
late = t_arr > g*P.dt + 1e-12;
miss = double(late && strcmp(rt.timing_mode, 'actual'));   % nominal에서는 도착 시각만 기록하고 늦음으로 세지 않음
if late && strcmp(rt.timing_mode, 'actual')
    if any(strcmp(CS.mode, {'C1', 'C2'})) && t_arrR <= g*P.dt + 1e-12
        if isP, f = fR; th = thR; end                   % 늦은 후보 지령 대신 제때 도착한 R 지령
        if strcmp(CS.mode, 'C2') && isV, k = kR; end
        reason = 'deadline';
    else
        f = NaN; th = NaN;                              % R도 늦으면 이전 지령 유지
        if ~strcmp(CS.mode, 'C1'), k = NaN; end
        reason = 'deadline_hold';
    end
end
if ~(isnan(f) && isnan(th) && isnan(k))
    CS = issue(CS, f, th, k, g);
    cmdv = [1; ~isnan(f); nz(f); ~isnan(th); nz(th); ~isnan(k); nz(k); g];
end
if strcmp(CS.mode, 'C1') && isV       % 미리 등록한 밸브 지령도 내보냄
    kk = CS.issued(find(CS.issued(:,1) == g & CS.issued(:,6) > 0.5, 1, 'last'), 7);
    cmdv(1) = 1; cmdv(6) = 1; cmdv(7) = kk; cmdv(8) = g;
    k = kk;                           % 기록용
end
if CS.diag_on && ~isempty(Dg), CS = diag_true_eval(CS, Dg, fcv, i, g, P); end   % 계산시간 측정 뒤, 진단 전용
% 기록: [i s g isP isV f th k fR thR kR origin ready n_cand n_feas J_best J_R wall miss reason_code wall_R t_arr/dt t_arrR/dt]
CS.nlog = CS.nlog + 1;
if CS.nlog > size(CS.log, 1), CS.log = [CS.log; nan(256, 23)]; end
CS.log(CS.nlog, :) = [i, s, g, isP, isV, f, th, k, fR, thR, kR, info, wall, miss, reason_code(reason), wall_R, t_arr/P.dt, t_arrR/P.dt];
end

function v = nz(x)
if isnan(x), v = 0; else, v = x; end
end

function CS = issue(CS, f, th, k, g)
CS.issued(end+1,:) = [g, ~isnan(f), nz(f), ~isnan(th), nz(th), ~isnan(k), nz(k)];
if ~isnan(f), CS.f_last = min(max(f, CS.FR(1)), CS.FR(2)); end
if ~isnan(th), CS.th_last = th; end
if ~isnan(k), CS.k_last = k; end
% 오래된 지령 정리 (최근 관측 이전에 적용된 것)
CS.issued(CS.issued(:,1) < CS.s - 1, :) = [];
end

function [sel, reason, info, Dg] = choose(CS, fcv, g, isP, isV, fR, thR, kR, P)
sel = []; reason = ''; info = nan(1,6); Dg = [];
if fcv(1) < 0.5, reason = 'no_forecast'; return; end
info(1:2) = fcv(2:3)';
% ---- 후보 ----
C = struct('f', {}, 'th', {}, 'k_mode', {}, 'k_exec', {});
if strcmp(CS.mode, 'C1') || isP
    fset = unique(min(max(CS.f_last + CS.df, CS.FR(1)), CS.FR(2)), 'stable');
    if strcmp(CS.angle_mode, 'absolute')       % 절대 각도 격자 + 현재 유지
        tset = unique(min(max([CS.th_last, CS.angle_grid], P.TH_RANGE(1)), P.TH_RANGE(2)), 'stable');
    else
        tset = unique(min(max(CS.th_last + CS.dth, P.TH_RANGE(1)), P.TH_RANGE(2)), 'stable');
    end
    if strcmp(CS.mode, 'C1'), kset = {'law'}; else, kset = num2cell(CS.kset); end
    C(end+1) = struct('f', fR, 'th', thR, 'k_mode', 'law', 'k_exec', false);          % R 후보
    for a = 1:numel(kset)
        for b = [find(fset == CS.f_last, 1), setdiff(1:numel(fset), find(fset == CS.f_last, 1))]
            for c = [find(tset == CS.th_last, 1), setdiff(1:numel(tset), find(tset == CS.th_last, 1))]
                C(end+1) = struct('f', fset(b), 'th', tset(c), 'k_mode', kset{a}, 'k_exec', isV); %#ok<AGROW>
            end
        end
    end
else                                         % C2, 밸브만 갱신
    C(end+1) = struct('f', NaN, 'th', NaN, 'k_mode', 'law', 'k_exec', true);
    for a = 1:numel(CS.kset)
        C(end+1) = struct('f', NaN, 'th', NaN, 'k_mode', CS.kset(a), 'k_exec', true); %#ok<AGROW>
    end
end
% 중복 제거 (R 후보는 맨 앞 유지)
keep = true(1, numel(C));
for a = 2:numel(C)
    for b = 1:a-1
        if keep(b) && same(C(a), C(b)), keep(a) = false; break; end
    end
end
C = C(keep);
nC = numel(C); info(3) = nC;
J = inf(1, nC); thm = inf(1, nC); thr = inf(1, nC); jm = nan(1, nC); tl = nan(1, nC); Qc = inf(1, nC); Mc = inf(1, nC);
for a = 1:nC
    [ok, R] = predict_response(P, CS, C(a), fcv, g);
    if ~ok
        if a == 1, reason = R.reason; return; end
        continue;
    end
    e = mean(((R.ux/CS.sx).^2 + (R.uy/CS.sy).^2 + (R.th/CS.st).^2)/3);
    jm(a) = jmove(CS, C(a), P);
    J(a) = e + CS.w_move*jm(a);
    thm(a) = max(abs(R.th)); thr(a) = sqrt(mean(R.th.^2));
    tl(a) = tail_ms(R, CS);                       % 예측 구간 끝 0.5 s 잔여 진동 (기록용)
    Qc(a) = CS.Qa + sum(R.th_all.^2); Mc(a) = max(CS.Ma, max(abs(R.th_all)));
end
tol = 1 + CS.tor_tol;
if strcmp(CS.constraint, 'shadow')
    % 그림자 R 누적 제한 (report/design_shadowR.md 4절): 같은 예측 입력으로
    %   Q̂_c = Qa(s) + Σ θ̂_c²,  M̂_c = max(Ma(s), max|θ̂_c|)   (스텝 s+1 … 구간 끝)
    %   Q̂_R = Q_R(s) + Σ θ̂_R², M̂_R = max(M_R(s), max|θ̂_R|)  (그림자 R 상태에서 R 법칙 지령 유지)
    %   만족: Q̂_c ≤ Q̂_R(1+tol) 그리고 M̂_c ≤ M̂_R(1+tol). R 후보(=모든 제안 거부)는 항상 허용.
    %   R 외 만족 후보가 없으면 제안 없음 → 원래 시각 R (사유 no_feasible). 이미 뒤처졌으면(Qa > Q̂_R 등) 계속 R.
    if isempty(CS.shadow), reason = 'no_feasible'; return; end
    sh = CS.shadow.cs;
    cR = struct('f', reference_R_step('f', sh.Hm, sh.s, P), 'th', reference_R_step('th', sh.Hm, sh.s, P), 'k_mode', 'law', 'k_exec', false);
    [okS, RS] = predict_response(P, sh, cR, fcv, g);
    if ~okS, reason = RS.reason; return; end
    QR = CS.shadow.Q + sum(RS.th_all.^2); MR = max(CS.shadow.M, max(abs(RS.th_all)));
    feas = (Qc <= QR*tol) & (Mc <= MR*tol) & isfinite(J);
    feas(1) = isfinite(J(1));
    info(4) = sum(feas);
    Dg = struct('C', C, 'J', J, 'thm', thm, 'thr', thr, 'jm', jm, 'tl', tl, 'feas', feas, 'best', NaN); Dg.C = C;
    if ~any(feas(2:end)), reason = 'no_feasible'; return; end
else
feas = (thm <= thm(1)*tol) & (thr <= thr(1)*tol) & isfinite(J);
feas(1) = isfinite(J(1));
info(4) = sum(feas);
Dg = struct('C', C, 'J', J, 'thm', thm, 'thr', thr, 'jm', jm, 'tl', tl, 'feas', feas, 'best', NaN);
Dg.C = C;                                     % struct()가 배열로 펼치지 않도록 다시 대입
if ~any(feas), reason = 'no_feasible'; return; end
end
Jf = J; Jf(~feas) = inf;
[~, best] = min(Jf);                          % 동점이면 앞 순서(R → 유지 → 나머지)
sel = C(best); Dg.best = best;
info(5:6) = [J(best), J(1)];
if best == 1, reason = 'chose_R'; else, reason = 'chose_cand'; end
end

function CS = diag_true_eval(CS, Dg, fcv, i, g, P)
% 진단 전용: 같은 후보를 같은 기준시각의 '실제' 미래 입력으로 다시 모의해 기록한다.
% 계산시간(wall) 측정이 끝난 뒤에 실행하고, 결과는 지령 선택에 쓰지 않는다.
rt = P.rt; o = fcv(2); q = o + rt.r*(1:rt.Hn)'; ok = q + 1 <= numel(CS.diag.agx);
Yx = zeros(rt.Hn, 1); Yy = Yx; Yx(ok) = CS.diag.agx(q(ok)+1); Yy(ok) = CS.diag.agy(q(ok)+1);
ft = [1; o; fcv(3); Yx; Yy];
for a = 1:numel(Dg.C)
    c = Dg.C(a); kv = NaN; if isnumeric(c.k_mode), kv = c.k_mode; end
    row = [CS.nlog + 1, i, g, a, c.f, c.th, kv, Dg.J(a), Dg.thm(a), Dg.thr(a), Dg.feas(a), double(a == Dg.best), nan(1, 7), Dg.jm(a), NaN, Dg.tl(a)];
    [okk, R] = predict_response(P, CS, c, ft, g);
    if okk
        mx = mean((R.ux/CS.sx).^2); my = mean((R.uy/CS.sy).^2); mt = mean((R.th/CS.st).^2);
        row(13:19) = [(mx + my + mt)/3 + CS.w_move*Dg.jm(a), max(abs(R.th)), sqrt(mean(R.th.^2)), mx, my, mt, max(abs([R.ux/CS.sx; R.uy/CS.sy]))];
        row(21) = tail_ms(R, CS);
    end
    CS.clog(end+1, :) = row;
end
end

function v = tail_ms(R, CS)
% 평가 구간 마지막 0.5 s(50 스텝)의 정규화 제곱평균 — 구간 끝에 남는 진동
n = numel(R.ux); k = max(1, n - 49):n;
v = mean(((R.ux(k)/CS.sx).^2 + (R.uy(k)/CS.sy).^2 + (R.th(k)/CS.st).^2)/3);
end

function tf = same(a, b)
tf = isequaln(a.f, b.f) && isequaln(a.th, b.th) && isequal(class(a.k_mode), class(b.k_mode)) && isequal(a.k_mode, b.k_mode);
end

function v = jmove(CS, c, P)
A = CS.As;
tf = 0; tt = 0;
if ~isnan(c.f), tf = abs(c.f - A.f)/(CS.FR(2) - CS.FR(1)); end
if ~isnan(c.th), tt = abs(c.th - A.theta)/(P.TH_RANGE(2) - P.TH_RANGE(1)); end
if strcmp(CS.mode, 'C1')
    v = (tf + tt)/2;
else
    if isnumeric(c.k_mode), kc = double(c.k_mode ~= CS.k_last); else, kc = 0; end
    v = (tf + tt + kc)/3;
end
end

function c = reason_code(r)
codes = {'', 'chose_R', 'chose_cand', 'no_forecast', 'horizon', 'nan', 'no_feasible', 'deadline', 'deadline_hold', 'explore'};
c = find(strcmp(codes, r), 1) - 1;
if isempty(c), c = -1; end
end

function [CS, cmdv] = c1_ontime(CS, fcv, i, P)
% 원래 시각 R 경로 (report/design_shadowR.md 2절)
%  (a) 적용 격자 gC의 C1 제안은 gC − d_cmd에 계산만 하고 보내지 않는다.
%  (b) 각 격자 g의 g − d_cmd_R 스텝에 원래 R 법칙(진동수·각도·밸브)을 그 시각 관측으로 실행한다.
%      받아들여진 제안이 제때 도착했으면 펌프·각도는 제안, 아니면 원래 R. 밸브는 항상 원래 R.
%  모든 제안을 거부하면 R 방식과 같은 시각·같은 관측·같은 지령 → 원래 R 재현 (C 단계 T10).
%  제안이 한 번 적용되면 상태가 달라지므로, 그 뒤 R 지령을 써도 원래 R 응답으로 돌아간다는 보장은 없다.
rt = P.rt; cmdv = zeros(8,1); s = CS.s;
gC = i + rt.d_cmd;
if gC > 0 && mod(gC, P.nF) == 0
    t0 = tic;
    fRl = reference_R_step('f', CS.Hm, s, P); thRl = reference_R_step('th', CS.Hm, s, P);
    CSp = CS;
    if mod(gC, P.nC) == 0, CSp = issue(CSp, NaN, NaN, reference_R_step('kappa', CS.Hm, s, P), gC); end   % 예측용 가등록(보내지 않음)
    [sel, reason, info] = choose(CSp, fcv, gC, true, false, fRl, thRl, NaN, P);
    wall = toc(t0) + rt.inject_select_s;
    t_arr = i*P.dt + wall + rt.comm_extra_s;
    late = t_arr > gC*P.dt + 1e-12 && strcmp(rt.timing_mode, 'actual');
    acc = ~isempty(sel) && strcmp(reason, 'chose_cand') && ~late && ~CS.force_reject;
    if late && strcmp(reason, 'chose_cand'), reason = 'deadline'; end
    if CS.force_reject && strcmp(reason, 'chose_cand'), reason = 'chose_R'; end
    pf = NaN; pth = NaN; if acc, pf = sel.f; pth = sel.th; end
    CS.prop = struct('g', gC, 'acc', acc, 'f', pf, 'th', pth, 'reason', reason, 'info', info, 'wall', wall, ...
                     'miss', double(late), 't_arr', t_arr, 'i', i, 's', s);
end
g = i + rt.d_cmd_R;
isP = g > 0 && mod(g, P.nF) == 0;
isV = g > 0 && mod(g, P.nC) == 0;
if ~(isP || isV), return; end
t0 = tic;
if isP, fR = reference_R_step('f', CS.Hm, s, P); thR = reference_R_step('th', CS.Hm, s, P); else, fR = NaN; thR = NaN; end
if isV, kR = reference_R_step('kappa', CS.Hm, s, P); else, kR = NaN; end
wall_R = toc(t0);
t_arrR = i*P.dt + wall_R + rt.comm_extra_s;
f = NaN; th = NaN; k = kR; reason = ''; info = nan(1,6); wall = NaN; miss = 0; idec = i; sdec = s; t_arr = NaN; acc = false;
if isP
    f = fR; th = thR;
    pr = CS.prop;
    if ~isempty(pr) && pr.g == g
        acc = pr.acc; reason = pr.reason; info = pr.info; wall = pr.wall; miss = pr.miss; idec = pr.i; sdec = pr.s; t_arr = pr.t_arr;
        if acc, f = pr.f; th = pr.th; end
        CS.prop = [];
    else
        reason = 'no_forecast';                    % 제안 결정 시각이 관측 시작 전 등
    end
end
if t_arrR > g*P.dt + 1e-12 && strcmp(rt.timing_mode, 'actual')   % R 계산이 늦음: R 방식과 같게 보류 (제안 적용분은 유지)
    if ~acc, f = NaN; th = NaN; reason = 'deadline_hold'; end
    k = NaN;
end
if ~(isnan(f) && isnan(th) && isnan(k))
    CS = issue(CS, f, th, k, g);
    cmdv = [1; ~isnan(f); nz(f); ~isnan(th); nz(th); ~isnan(k); nz(k); g];
end
CS.nlog = CS.nlog + 1;
if CS.nlog > size(CS.log, 1), CS.log = [CS.log; nan(256, 23)]; end
CS.log(CS.nlog, :) = [idec, sdec, g, isP, isV, f, th, k, fR, thR, kR, info, wall, miss, reason_code(reason), wall_R, t_arr/P.dt, t_arrR/P.dt];
end

% =====================================================================
% 8주차 v2 공동 선택 (J): 펌프·회전판·밸브 (계획 §4)
function [CS, cmdv] = j_ontime(CS, fcv, i, P)
% 결정 (보내지 않고 제안만 저장):
%  느린 결정  gS = i + d_cmd  가 펌프·각도 격자 → (f,θ,κ) 공동 후보. κ는 gS 이후 첫 밸브 격자 gk의 계획값.
%  빠른 결정  gV = i + d_cmd_V가 밸브 격자(펌프 격자 아님) → κ만. 제때 준비되면 느린 결정의 κ 계획보다 우선(더 새 정보).
% 원래 시각 R 경로: 각 격자 g의 g − d_cmd_R에 원래 R 법칙을 그 시각 관측으로 실행하고,
%  펌프·각도 = 받아들여진 느린 제안 | R,  밸브 = 준비된 빠른 결정 | 느린 κ 계획 | R.
%  모든 제안을 거부하면 R 방식과 같은 시각·관측·지령 → 원래 R 재현 (C 단계 T12a).
rt = P.rt; cmdv = zeros(8,1); s = CS.s;
gS = i + rt.d_cmd;
if gS > 0 && mod(gS, P.nF) == 0, CS = j_decide(CS, fcv, i, gS, 1, P); end
gV = i + rt.d_cmd_V;
if ~CS.valve_law && gV > 0 && mod(gV, P.nC) == 0 && mod(gV, P.nF) ~= 0, CS = j_decide(CS, fcv, i, gV, 2, P); end
g = i + rt.d_cmd_R;
isP = g > 0 && mod(g, P.nF) == 0;
isV = g > 0 && mod(g, P.nC) == 0;
if ~(isP || isV), return; end
t0 = tic;
if isP, fR = reference_R_step('f', CS.Hm, s, P); thR = reference_R_step('th', CS.Hm, s, P); else, fR = NaN; thR = NaN; end
if isV, kR = reference_R_step('kappa', CS.Hm, s, P); else, kR = NaN; end
wall_R = toc(t0);
t_arrR = i*P.dt + wall_R + rt.comm_extra_s;
f = fR; th = thR; k = kR; reason = ''; info = nan(1,6); wall = NaN; miss = 0; idec = i; sdec = s; t_arr = NaN; acc = false; kacc = false;
if isP
    pr = CS.propS;
    if ~isempty(pr) && pr.g == g
        acc = pr.acc; reason = pr.reason; info = pr.info; wall = pr.wall; miss = pr.miss; idec = pr.i; sdec = pr.s; t_arr = pr.t_arr;
        if acc, f = pr.f; th = pr.th; end
        if acc && isV && ~isnan(pr.k), k = pr.k; kacc = true; end        % 격자가 겹치면 κ도 같은 결정
        if isfield(pr, 'di') && pr.di <= size(CS.dlog,1), CS.dlog(pr.di, 18) = 1 + double(~pr.acc); end   % 1=적용(채택) 2=R(거부)
        CS.propS = [];
    else
        reason = 'no_forecast';
    end
elseif isV
    pf = CS.propF;
    if ~isempty(pf) && pf.g == g && pf.ready                             % 준비된 빠른 결정 (R 선택 포함)
        if pf.acc, k = pf.k; kacc = true; end
        reason = pf.reason; info = pf.info; wall = pf.wall; miss = pf.miss; idec = pf.i; sdec = pf.s; t_arr = pf.t_arr; acc = pf.acc;
        if isfield(pf, 'di') && pf.di <= size(CS.dlog,1), CS.dlog(pf.di, 18) = 1 + double(~pf.acc); end
    elseif ~isempty(CS.planK) && CS.planK.g == g                         % 빠른 결정이 없거나 늦음 → 느린 결정의 κ 계획
        k = CS.planK.k; kacc = true; acc = true; reason = 'chose_cand';
    end
    if ~isempty(pf) && pf.g == g && ~pf.ready && isfield(pf, 'di') && pf.di <= size(CS.dlog,1), CS.dlog(pf.di, 18) = 3; end   % 3=늦어서 폐기(R 또는 느린 계획으로 대체)
    if ~isempty(pf) && pf.g <= g, CS.propF = []; end
end
if ~isempty(CS.planK) && CS.planK.g <= g, CS.planK = []; end
if t_arrR > g*P.dt + 1e-12 && strcmp(rt.timing_mode, 'actual')         % R 계산이 늦음: R 방식과 같게 보류 (제안 적용분은 유지)
    if ~acc, f = NaN; th = NaN; reason = 'deadline_hold'; end
    if ~kacc, k = NaN; end
end
if ~isP, f = NaN; th = NaN; end
if ~(isnan(f) && isnan(th) && isnan(k))
    CS = issue(CS, f, th, k, g);
    cmdv = [1; ~isnan(f); nz(f); ~isnan(th); nz(th); ~isnan(k); nz(k); g];
end
CS.nlog = CS.nlog + 1;
if CS.nlog > size(CS.log, 1), CS.log = [CS.log; nan(256, 23)]; end
CS.log(CS.nlog, :) = [idec, sdec, g, isP, isV, f, th, k, fR, thR, kR, info, wall, miss, reason_code(reason), wall_R, t_arr/P.dt, t_arrR/P.dt];
end

function CS = j_decide(CS, fcv, i, g, kind, P)
persistent jd_; if isempty(jd_), jd_ = 0; end, jd_ = jd_ + 1; if jd_ <= 4, fprintf('J_DECIDE call %d: policy=[%s] class=%s kind=%d fcv1=%g scorer_empty=%d\n', jd_, CS.policy, class(CS.policy), kind, fcv(1), isempty(CS.scorer)); end
rt = P.rt; s = CS.s;
t0 = tic;
if kind == 1
    fRl = reference_R_step('f', CS.Hm, s, P); thRl = reference_R_step('th', CS.Hm, s, P);
else
    fRl = NaN; thRl = NaN;
end
kRl = reference_R_step('kappa', CS.Hm, s, P);
CSp = CS;                                          % 예측용 가등록 (보내지 않음): 아직 보내지 않은 이전 격자 지령
if kind == 2 && ~isempty(CS.propS) && CS.propS.g < g && ~any(CS.issued(:,1) == CS.propS.g)
    pr = CS.propS;
    if pr.acc, CSp = issue(CSp, pr.f, pr.th, NaN, pr.g); else, CSp = issue(CSp, fRl_now(CS, 'f', P), fRl_now(CS, 'th', P), NaN, pr.g); end
end
if kind == 1 && mod(g, P.nC) ~= 0 && ~isempty(CS.propF) && CS.propF.g < g && ~any(CS.issued(:,1) == CS.propF.g)
    pf = CS.propF; kv = kRl; if pf.acc, kv = pf.k; end
    CSp = issue(CSp, NaN, NaN, kv, pf.g);
end
C = enumerate_joint_candidates(CSp, kind, g, fRl, thRl, P);
n = numel(C); iR = find([C.isR], 1); scorer_on = false; neval = 0; X = [];
switch CS.policy
    case 'R'
        sel = iR; reason = 'chose_R'; info = [fcv(2:3)', n, 1, NaN, NaN];
    case 'explore'
        CS.lcg = mod(16807*CS.lcg, 2147483647);
        sel = 1 + floor(CS.lcg/2147483647*n); reason = 'explore'; info = [fcv(2:3)', n, NaN, NaN, NaN];
        if C(sel).isR, reason = 'chose_R'; end
    otherwise
        idx = 1:n;
        if kind == 1 && strcmp(CS.policy, 'rand3') && fcv(1) > 0.5                % 비학습 대조: 점수망 대신 고정 시드 무작위 top-3 (같은 후보 집합·물리 필터)
            pool = find(~[C.isR] & ~[C.isHold]); top = zeros(1, 0);
            for q = 1:min(CS.top_k, numel(pool))
                CS.lcg = mod(16807*CS.lcg, 2147483647); r = 1 + floor(CS.lcg/2147483647*numel(pool));
                top(end+1) = pool(r); pool(r) = []; %#ok<AGROW>
            end
            idx = sort([find([C.isHold]), iR, top]); scorer_on = true;
        elseif kind == 1 && strcmp(CS.policy, 'det3') && fcv(1) > 0.5                % 비학습 대조(v5): 이동 비용이 가장 작은 3개 (결정론). 미래 정보·예측 파형·학습 모델 미사용
            error('DET3_BRANCH_REACHED');
            pool = find(~[C.isR] & ~[C.isHold]);
            mv = arrayfun(@(q) jmove_det3(CSp, C(q), P), pool);
            [~, o] = sort(mv, 'ascend');                                              % MATLAB sort는 안정 정렬: 동점은 후보 생성 순서
            top = pool(o(1:min(CS.top_k, numel(pool))));
            idx = sort([find([C.isHold]), iR, top]); scorer_on = true;
        elseif kind == 1 && ~isempty(CS.scorer) && fcv(1) > 0.5
            X = build_state_features(CSp, C, fcv, i, g, kind, kRl, P);
            y = rank_joint_candidates(CS.scorer, X);
            pool = find(~[C.isR] & ~[C.isHold]);
            [~, o] = sort(y(pool)); top = pool(o(1:min(CS.top_k, numel(pool))));
            idx = sort([find([C.isHold]), iR, top]);
            scorer_on = true;
        end
        E = filter_and_apply_joint_action(CSp, C, idx, fcv, g, kind, P);
        neval = sum(~isnan(E.J)); info = E.info;
        reason = E.reason; sel = E.sel; if isempty(sel), sel = iR; end
end
wall = toc(t0) + rt.inject_select_s;
t_arr = i*P.dt + wall + rt.comm_extra_s;
late = t_arr > g*P.dt + 1e-12 && strcmp(rt.timing_mode, 'actual');
c = C(sel);
acc = ~c.isR && ~late && ~CS.force_reject && any(strcmp(reason, {'chose_cand', 'explore'}));
if late && ~c.isR, reason = 'deadline'; end
if CS.force_reject && ~c.isR, reason = 'chose_R'; end
kv = NaN; if isnumeric(c.k_mode), kv = c.k_mode; end
if kind == 1
    pf = NaN; pth = NaN; if acc, pf = c.f; pth = c.th; end
    CS.propS = struct('g', g, 'acc', acc, 'f', pf, 'th', pth, 'k', kv, 'reason', reason, 'info', info, 'wall', wall, ...
                      'miss', double(late), 't_arr', t_arr, 'i', i, 's', s, 'cid', c.cid, 'di', size(CS.dlog,1)+1);
    gk = ceil(g/P.nC)*P.nC;
    if acc && ~isnan(kv) && gk > g, CS.planK = struct('g', gk, 'k', kv); end   % 이전 계획은 그 격자에서 소비됨 (d_cmd ≤ 150 보장)
else
    CS.propF = struct('g', g, 'acc', acc, 'k', kv, 'ready', ~late, 'reason', reason, 'info', info, 'wall', wall, ...
                      'miss', double(late), 't_arr', t_arr, 'i', i, 's', s, 'cid', c.cid, 'di', size(CS.dlog,1)+1);
end
% A1 진단 로그(제어 무관): [결정번호 i s g kind 관측시각 예측원점 계산시작 계산종료(도착) 적용시각 지연슬롯 측정시간 늦음 cid isR acc reason적용구분(후에 채움) 예산초과여유]
CS.dlog(end+1, :) = [size(CS.dlog,1)+1, i, s, g, kind, i*P.dt, fcv(2)*P.dt, i*P.dt, t_arr, g*P.dt, g-i, wall, double(late), c.cid, c.isR, double(acc), reason_code(reason), 0, g*P.dt - t_arr];
CS.jlog(end+1, :) = [i, s, g, kind, n, neval, info(4), c.cid, c.isR, c.isHold, scorer_on, c.f, c.th, kv, acc, wall, double(late), reason_code(reason)];
% teacher 라벨 (계산시간 측정 뒤, 라벨 전용): 모든 후보를 실제 미래 지반입력으로 평가 (비인과 teacher), 입력 특징은 인과 예측
if ~isempty(CS.teach_g) && any(CS.teach_g == g) && fcv(1) > 0.5 && ~isempty(CS.tdiag)
    if isempty(X) || size(X, 1) ~= n, X = build_state_features(CSp, C, fcv, i, g, kind, kRl, P); end
    o = fcv(2); q = o + rt.r*(1:rt.Hn)'; okq = q + 1 <= numel(CS.tdiag.agx);
    Yx = zeros(rt.Hn, 1); Yy = Yx; Yx(okq) = CS.tdiag.agx(q(okq)+1); Yy(okq) = CS.tdiag.agy(q(okq)+1);
    ft = [1; o; fcv(3); Yx; Yy];
    Et = filter_and_apply_joint_action(CSp, C, 1:n, ft, g, kind, P);
    for a = 1:n
        jp = NaN; fp = NaN;                        % 예측 기반 전체 평가는 저장하지 않음 (라벨 시간 절약)
        CS.tlog(end+1, :) = [g, kind, C(a).cid, C(a).isR, C(a).isHold, X(a, :), Et.J(a), Et.Qc(a), Et.Mc(a), Et.QR, Et.MR, jp, fp];
    end
end
end

function v = fRl_now(CS, kind, P)
v = reference_R_step(kind, CS.Hm, CS.s, P);
end

function v = jmove_det3(CS, c, P)
% det3 순위 키: filter_and_apply_joint_action.jmove_c1과 같은 식 (현재 장치 상태 대비 펌프·각도 목표 변화, 범위 정규화 평균)
A = CS.As; tf = 0; tt = 0;
if ~isnan(c.f), tf = abs(c.f - A.f)/(CS.FR(2) - CS.FR(1)); end
if ~isnan(c.th), tt = abs(c.th - A.theta)/(P.TH_RANGE(2) - P.TH_RANGE(1)); end
v = (tf + tt)/2;
end
