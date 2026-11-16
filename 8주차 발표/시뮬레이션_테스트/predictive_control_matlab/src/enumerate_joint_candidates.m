function C = enumerate_joint_candidates(CS, kind, g, fR, thR, P)
% ENUMERATE_JOINT_CANDIDATES  8주차 v2 공동 선택(J) 후보 (계획 §4).
%  kind 1 느린 결정 (펌프·각도 격자 g, 2.6 s): 유지 + R + f {현재 목표 −0.005, 0, +0.005}(범위 제한) × θ {0,22.5,45,67.5,90}° × κ {0.1,0.4,0.8}
%         κ는 g 이후 첫 밸브 격자(g가 밸브 격자면 g)에 적용할 계획값. CS.valve_law(C1-AI 비교군)면 κ = 원문 법칙.
%  kind 2 빠른 결정 (밸브 격자 g, 1 s, 펌프 격자와 겹치지 않을 때): 유지 κ + R(법칙) + κ 3, f·θ 유지
%  동점 순서 = 생성 순서: 유지 → R → 고정 ID. 중복은 앞의 것을 남긴다.
%  필드: f th (NaN = 갱신 없음) k_mode('law' | 숫자) k_exec cid isR isHold
kx = mod(g, P.nC) == 0;
C = struct('f', {}, 'th', {}, 'k_mode', {}, 'k_exec', {}, 'cid', {}, 'isR', {}, 'isHold', {});
if kind == 1
    if CS.valve_law, kh = 'law'; else, kh = CS.k_last; end
    C(end+1) = mk(CS.f_last, CS.th_last, kh, kx, 1, false, true);
    C(end+1) = mk(fR, thR, 'law', false, 2, true, false);
    fset = min(max(CS.f_last + CS.df, CS.FR(1)), CS.FR(2));
    tset = min(max(CS.angle_grid, P.TH_RANGE(1)), P.TH_RANGE(2));
    if CS.valve_law, kset = {'law'}; else, kset = num2cell(CS.kset_j); end
    id = 2;
    for a = 1:numel(fset)
        for b = 1:numel(tset)
            for c = 1:numel(kset)
                id = id + 1;
                C(end+1) = mk(fset(a), tset(b), kset{c}, kx, id, false, false); %#ok<AGROW>
            end
        end
    end
else
    C(end+1) = mk(NaN, NaN, CS.k_last, true, 101, false, true);
    C(end+1) = mk(NaN, NaN, 'law', true, 102, true, false);
    for c = 1:numel(CS.kset_j)
        C(end+1) = mk(NaN, NaN, CS.kset_j(c), true, 102 + c, false, false); %#ok<AGROW>
    end
end
keep = true(1, numel(C));
for a = 2:numel(C)
    if C(a).isR, continue; end                     % R은 유지와 값이 같아도 따로 둔다 (법칙 대 고정값)
    for b = 1:a-1
        if keep(b) && ~C(b).isR && isequaln(C(a).f, C(b).f) && isequaln(C(a).th, C(b).th) && ...
                strcmp(class(C(a).k_mode), class(C(b).k_mode)) && isequal(C(a).k_mode, C(b).k_mode)
            keep(a) = false; break;
        end
    end
end
C = C(keep);
end

function c = mk(f, th, k, kx, id, isR, isHold)
c = struct('f', f, 'th', th, 'k_mode', k, 'k_exec', kx && ~ischar(k), 'cid', id, 'isR', isR, 'isHold', isHold);
end
