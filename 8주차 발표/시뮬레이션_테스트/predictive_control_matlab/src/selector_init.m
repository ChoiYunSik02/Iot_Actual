function CS = selector_init(cfg, P, M, nt)
% SELECTOR_INIT  selector_step 상태 초기화.
CS = struct();
CS.mode = M.select;
CS.Hm = nan(9, nt);
CS.s = -1; CS.xs = []; CS.As = [];
CS.issued = zeros(0, 7);
CS.FR = P.FR;
CS.f_last = P.F0; CS.th_last = 0; CS.k_last = P.KAPPA0;
CS.fix_f = cfg.fix.f_hz; CS.fix_th = cfg.fix.theta_deg*pi/180;
cc = cfg.controller;
if strcmp(M.select, 'C2'), cs = cc.C2; elseif strcmp(M.select, 'J'), cs = cc.J; else, cs = cc.C1; end
CS.df = cs.df_hz(:)'; CS.dth = gf(cs, 'dtheta_deg', 0); CS.dth = CS.dth(:)'*pi/180;
if isfield(cs, 'kappa'), CS.kset = cs.kappa(:)'; else, CS.kset = []; end
CS.w_move = cc.move_weight; CS.tor_tol = cc.torsion_rel_tol;
% 8주차 구조 선택 (C1): 기본 R 경로, 후보 제한, 각도 후보 (report/design_shadowR.md)
CS.dpath = gf(cs, 'default_path', 'lagged');       % 'lagged' 결정 시각 R 후보 적용(기존) | 'ontime' 원래 시각 R 법칙 적용
CS.constraint = gf(cs, 'constraint', 'window_R'); % 'window_R' 예측 구간 R 후보 비교(기존) | 'shadow' 그림자 R 누적 비교
CS.angle_mode = gf(cs, 'angle_mode', 'relative'); % 'relative' 현재 목표 + dtheta | 'absolute' 격자
CS.angle_grid = gf(cs, 'angle_grid_deg', [0 22.5 45 67.5 90]); CS.angle_grid = CS.angle_grid(:)'*pi/180;
CS.force_reject = false;                           % 시험용: 모든 제안 거부 (원래 R 재현 확인)
CS.prop = [];                                      % 대기 중인 C1 제안 (ontime 경로)
CS.Qa = 0; CS.Ma = 0; CS.qs_last = -1;             % 실제 최상층 비틀림 누적 제곱합·최대 (도착한 관측 s까지)
CS.shadow = [];                                    % 그림자 R 상태 사본 (run_closed_loop가 결정 시각에 넣음)
% ---- 8주차 v2 공동 선택(J): 펌프·회전판·밸브 ----
CS.kset_j = gf(cs, 'kappa', [0.1 0.4 0.8]); CS.kset_j = CS.kset_j(:)';
CS.propS = []; CS.propF = []; CS.planK = [];       % 느린 joint 제안, 빠른 밸브 제안, 느린 결정의 κ 계획
CS.Qx = 0; CS.Qy = 0; CS.Mx = 0; CS.My = 0;        % 실제 X·Y 누적 제곱합·최대 (도착한 관측까지, 상태 특징용)
CS.valve_law = isfield(M, 'jvalve') && strcmp(M.jvalve, 'law');   % C1-AI 비교군: 밸브는 원문 법칙, 펌프·각도만 선택
CS.scorer = [];                                    % 공동 후보 점수망 (load_scorer), 있으면 느린 결정에서 top_k만 물리 검사
CS.top_k = 3;
CS.policy = 'eval';                                % 'eval' 물리 검사 선택 | 'R' 항상 R(teacher 기준 rollout) | 'explore' 고정 시드 무작위(teacher)
CS.lcg = 1;                                        % explore 난수 상태 (Park–Miller)
CS.teach_g = [];                                   % teacher 상태를 저장할 적용 격자 목록 (generate_joint_teacher)
CS.tdiag = [];                                     % teacher 라벨용 실제 미래 지반입력 (라벨 전용, 선택에 쓰지 않음)
CS.tlog = zeros(0, 110);                           % teacher 행: [g kind cid isR isHold 특징(98) J_true Qc Mc QR MR J_pred feas_pred]
% J 기록: [i s g kind n_cand n_eval n_feas cid_sel sel_isR sel_isHold scorer_on f th k acc wall miss reason]
CS.jlog = zeros(0, 18);
CS.select_s = M.select_s;
sf = fullfile(cfg.root, cc.scales_file);
if exist(sf, 'file')
    sc = jsondecode(fileread(sf)); CS.sx = sc.sx; CS.sy = sc.sy; CS.st = sc.st; CS.scales_frozen = true;
else
    CS.sx = 1; CS.sy = 1; CS.st = 1; CS.scales_frozen = false;   % 스케일 미정 (C1/C2 실행 전 compute_scales 필요)
    if any(strcmp(M.select, {'C1', 'C2', 'J'}))
        error('selector_init: %s 없음 — scripts/compute_scales.m을 먼저 실행', sf);
    end
end
CS.log = nan(256, 23); CS.nlog = 0;
% 진단: 후보별 예측·실제 미래 평가 기록 (run_closed_loop opt.diag_true). 열:
% [log행 i g 후보번호 f th kappa(NaN=법칙) J_pred thmax_pred thrms_pred 만족 선택 J_true thmax_true thrms_true msX msY msTh max|u|/s jmove
%  구간끝0.5s잔여_참 구간끝0.5s잔여_예측]
CS.diag_on = false; CS.diag = []; CS.clog = zeros(0, 22);
end

function v = gf(s, f, d)
if isfield(s, f) && ~isempty(s.(f)), v = s.(f); else, v = d; end
end
