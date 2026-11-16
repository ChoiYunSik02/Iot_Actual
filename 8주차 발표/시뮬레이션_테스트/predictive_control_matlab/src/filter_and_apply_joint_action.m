function E = filter_and_apply_joint_action(CS, C, idx, fcv, g, kind, P)
% FILTER_AND_APPLY_JOINT_ACTION  공동 후보 물리 검사·선택 (계획 §4.3·§4.4).
%  idx 후보만 내부 모델(predict_response)로 평가: 비용 J = 정규화 응답 제곱평균 + w_move·이동 항(기존 C1 식, f·θ)
%  그림자 R 제한: 같은 예측 입력으로 Q̂_c ≤ Q̂_R(1+tol), M̂_c ≤ M̂_R(1+tol). R 후보는 항상 허용.
%  선택: 만족 후보 중 J 최소, 동점은 idx 순서(유지 → R → 고정 ID). R 외 만족 후보 없음 → R (no_feasible).
%  E.sel (C의 번호, 비면 R 계산 실패), E.reason, E.info [origin ready n_cand n_feas J_best J_R], E.J/Qc/Mc/feas (C 길이, 미평가 NaN), E.QR/MR
n = numel(C); E = struct('sel', [], 'reason', '', 'info', nan(1, 6), 'J', nan(1, n), 'Qc', nan(1, n), 'Mc', nan(1, n), 'feas', false(1, n), 'QR', NaN, 'MR', NaN);
E.info(3) = n;
if fcv(1) < 0.5, E.reason = 'no_forecast'; return; end
E.info(1:2) = fcv(2:3)';
iR = find([C.isR], 1);
idx = sort(unique([idx(:)', iR]));             % C 순서 = 동점 순서 (유지 → R → 고정 ID)
for a = idx
    [ok, R] = predict_response(P, CS, C(a), fcv, g);
    if ~ok
        if a == iR, E.reason = R.reason; return; end
        continue;
    end
    e = mean(((R.ux/CS.sx).^2 + (R.uy/CS.sy).^2 + (R.th/CS.st).^2)/3);
    E.J(a) = e + CS.w_move*jmove_c1(CS, C(a), P);
    E.Qc(a) = CS.Qa + sum(R.th_all.^2); E.Mc(a) = max(CS.Ma, max(abs(R.th_all)));
end
if isnan(E.J(iR)), E.reason = 'nan'; return; end
if isempty(CS.shadow), E.reason = 'no_feasible'; E.sel = iR; E.feas(iR) = true; E.info(4:6) = [1, E.J(iR), E.J(iR)]; return; end
sh = CS.shadow.cs;
if kind == 1
    cR = struct('f', reference_R_step('f', sh.Hm, sh.s, P), 'th', reference_R_step('th', sh.Hm, sh.s, P), 'k_mode', 'law', 'k_exec', false);
else
    cR = struct('f', NaN, 'th', NaN, 'k_mode', 'law', 'k_exec', true);
end
[okS, RS] = predict_response(P, sh, cR, fcv, g);
if ~okS, E.reason = RS.reason; return; end
tol = 1 + CS.tor_tol;
E.QR = CS.shadow.Q + sum(RS.th_all.^2); E.MR = max(CS.shadow.M, max(abs(RS.th_all)));
E.feas = (E.Qc <= E.QR*tol) & (E.Mc <= E.MR*tol) & isfinite(E.J);
E.feas(iR) = true;
E.info(4) = sum(E.feas(idx));
Jf = inf(1, n); Jf(E.feas) = E.J(E.feas);
[~, b] = min(Jf(idx)); best = idx(b);
E.sel = best; E.info(5:6) = [E.J(best), E.J(iR)];
if ~any(E.feas(setdiff(idx, iR))), E.reason = 'no_feasible';
elseif best == iR, E.reason = 'chose_R';
else, E.reason = 'chose_cand';
end
end

function v = jmove_c1(CS, c, P)
% 이동 항 = 기존 C1 식 그대로 (계획 §5.5 '기존 비용 우선 유지'): 펌프·각도 목표 변화(실제 상태 대비, 범위 정규화)의 평균.
% 밸브 전환에는 별도 비용 weight를 두지 않고 전환 횟수·κ 이동량을 보고한다.
A = CS.As; tf = 0; tt = 0;
if ~isnan(c.f), tf = abs(c.f - A.f)/(CS.FR(2) - CS.FR(1)); end
if ~isnan(c.th), tt = abs(c.th - A.theta)/(P.TH_RANGE(2) - P.TH_RANGE(1)); end
v = (tf + tt)/2;
end
