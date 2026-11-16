function out = run_closed_loop(agx, agy, cfg, M, opt)
% RUN_CLOSED_LOOP  한 기록의 폐루프 모의 (Simulink 모델과 같은 스텝 함수·같은 순서).
%  스텝 i 순서: 플랜트 출력 → SensorAndLatency → ObservationBuffer → Forecaster → StateEstimator
%               → CommandSelector → CommandQueue → Actuators → Plant30Story(i → i+1)
%  agx, agy : 지반가속도 (m/s², 플랜트 dt 간격). 전체 미래는 이 함수(=GroundMotion)와 PREVIEW 예측기만 접근.
%  M        : pc_method 결과
%  opt.dt (기본 cfg.plant.dt), opt.model (예측기 모델 struct), opt.record_id
if nargin < 5, opt = struct(); end
if ~isfield(opt, 'dt'), opt.dt = cfg.plant.dt; end
if ~isfield(opt, 'model'), opt.model = []; end
if ~isfield(opt, 'record_id'), opt.record_id = ''; end
if ~isfield(opt, 'diag_true'), opt.diag_true = false; end
if ~isfield(opt, 'force_reject'), opt.force_reject = false; end   % 시험용: C1 제안 모두 거부
if ~isfield(opt, 'shadow_monitor'), opt.shadow_monitor = false; end % 그림자 R을 감시 전용으로 함께 계산
if ~isfield(opt, 'scorer'), opt.scorer = []; end                  % J-AI: 공동 후보 점수망 (load_scorer)
if ~isfield(opt, 'jpolicy'), opt.jpolicy = 'eval'; end            % J teacher rollout: 'R' | 'explore'
if ~isfield(opt, 'explore_seed'), opt.explore_seed = 1; end
if ~isfield(opt, 'teach_g'), opt.teach_g = []; end                % J teacher 라벨 격자 (실제 미래는 라벨에만 사용)
if strcmp(M.timing_mode, 'actual') && ~isempty(M.unmeasured) && ~strcmp(M.select, 'U')
    % 계산 예산 0(미측정)으로 actual 시간축을 돌리면 모든 지령이 '늦음'이 된다 → 실측(measure_runtime) 또는 nominal 필요
    error('run_closed_loop: %s 계산시간 미측정(%s)인데 timing_mode=actual — measure_runtime을 먼저 하거나 nominal로', M.name, strjoin(M.unmeasured, ','));
end
agx = agx(:); agy = agy(:); nt = numel(agx);
[P, S] = plant_init(cfg, opt.dt);
P.rt = pc_runtime(cfg, P, M, nt);
has_dev = ~strcmp(M.select, 'U');
c1o = strcmp(M.select, 'C1') && isfield(cfg.controller.C1, 'default_path') && strcmp(cfg.controller.C1.default_path, 'ontime');
if c1o && P.rt.d_cmd < P.rt.d_cmd_R
    error('run_closed_loop: ontime 경로에서 C1 결정 앞당김 d_cmd(%d)가 R의 d_cmd_R(%d)보다 작아 제안이 쓰이지 않음 — 선택 예산을 R 이상으로', P.rt.d_cmd, P.rt.d_cmd_R);
end
isJ = strcmp(M.select, 'J');
if isJ && (P.rt.d_cmd < P.rt.d_cmd_R || P.rt.d_cmd_V < P.rt.d_cmd_R || P.rt.d_cmd > 150 || P.rt.d_cmd_V >= P.nC)
    error('run_closed_loop: J 앞당김 조건 위반 (d_cmd_R %d ≤ d_cmd %d ≤ 150, d_cmd_R ≤ d_cmd_V %d < %d)', P.rt.d_cmd_R, P.rt.d_cmd, P.rt.d_cmd_V, P.nC);
end
use_fc = ~strcmp(M.forecaster, 'none');
SS = sensor_step([], [], [], [], [], P);
BS = obsbuffer_step([], [], P);
FS = struct('kind', M.forecaster, 'model', opt.model, 'preview', []);
if strcmp(M.forecaster, 'preview'), FS.preview = struct('agx', agx, 'agy', agy); end
[FS, fcv] = forecaster_step(FS, [], [], P);
CS = selector_init(cfg, P, M, nt);
if opt.diag_true, CS.diag_on = true; CS.diag = struct('agx', agx, 'agy', agy); end   % 평가 전용 (제어에 쓰지 않음)
CS.force_reject = opt.force_reject;
if isJ
    if isfield(M, 'jscorer') && M.jscorer
        if isempty(opt.scorer), error('run_closed_loop: %s에는 opt.scorer 필요', M.name); end
        CS.scorer = opt.scorer;
    end
    CS.policy = opt.jpolicy; CS.lcg = opt.explore_seed; CS.teach_g = opt.teach_g;
    if ~isempty(opt.teach_g), CS.tdiag = struct('agx', agx, 'agy', agy); end   % 라벨 전용 (선택에 쓰지 않음)
end
QS = command_queue_step([], [], []);
A = actuator_step([], [], [], P);
ux = zeros(nt,1); uy = ux; th = ux; fd = ux; thd = ux; kd = ux;
% ---- 그림자 R (report/design_shadowR.md 3절): 같은 건물·같은 지반입력에 원래 R만 적용한 독립 실행 ----
% 제어기에는 도착한 관측 시각 s까지의 그림자 상태·누적 비틀림만 넘긴다(결정 시각에만 사본 전달).
do_sh = (strcmp(M.select, 'C1') && (strcmp(CS.constraint, 'shadow') || opt.shadow_monitor)) || isJ;
th_sh = []; Qsh = []; Msh = [];
if do_sh
    MR = pc_method(cfg, 'R', struct('select_s', M.R_s, 'sensor_s', M.sensor_s, 'comm_s', M.comm_s, 'extra_info_s', M.extra_info_s, ...
                                    'timing_mode', M.timing_mode, 'inject_select_s', 0));
    P2 = P; P2.rt = pc_runtime(cfg, P, MR, nt);
    [~, S2] = plant_init(cfg, opt.dt);
    SS2 = sensor_step([], [], [], [], [], P2); CS2 = selector_init(cfg, P2, MR, nt);
    QS2 = command_queue_step([], [], []); A2 = actuator_step([], [], [], P2);
    th_sh = zeros(nt,1); Qsh = zeros(nt,1); Msh = zeros(nt,1);
end
t_run = tic;
for i = 0:nt-2
    if has_dev
        Avec = act_pack(A);
        [SS, obsv] = sensor_step(SS, S, Avec, [agx(i+1); agy(i+1)], i, P);
        if use_fc
            [BS, bufv] = obsbuffer_step(BS, obsv, P);
            [FS, fcv] = forecaster_step(FS, bufv, i, P);
        end
        estv = state_estimator_step(obsv, 'ideal');
        if do_sh
            [SS2, obsv2] = sensor_step(SS2, S2, act_pack(A2), [agx(i+1); agy(i+1)], i, P2);
            [CS2, cmdv2] = selector_step(CS2, state_estimator_step(obsv2, 'ideal'), [], i, P2);
            [QS2, relv2] = command_queue_step(QS2, cmdv2, i);
            [A2, dev2] = actuator_step(A2, relv2, i, P2);
            gC = i + P.rt.d_cmd; gJ = i + P.rt.d_cmd_V;
            if CS2.s >= 0 && ((gC > 0 && mod(gC, P.nF) == 0) || (isJ && gJ > 0 && mod(gJ, P.nC) == 0))   % 결정 시각: 관측 시각 s의 그림자 사본
                sh = struct('Hm', CS2.Hm, 's', CS2.s, 'issued', CS2.issued, 'xs', CS2.xs, 'As', CS2.As);
                CS.shadow = struct('cs', sh, 'Q', Qsh(CS2.s+1), 'M', Msh(CS2.s+1));
            end
        end
        [CS, cmdv] = selector_step(CS, estv, fcv, i, P);
        [QS, relv] = command_queue_step(QS, cmdv, i);
        [A, dev] = actuator_step(A, relv, i, P);
    else
        dev = [0; 0; 0];
    end
    S = plant_step(S, [agx(i+2); agy(i+2)], dev, P, has_dev);
    ux(i+2) = S.u(P.tx); uy(i+2) = S.u(P.ty); th(i+2) = S.u(P.tth);
    if has_dev, fd(i+2) = dev(1); thd(i+2) = dev(2); kd(i+2) = dev(3); end
    if do_sh
        S2 = plant_step(S2, [agx(i+2); agy(i+2)], dev2, P2, true);
        th_sh(i+2) = S2.u(P.tth);
        Qsh(i+2) = Qsh(i+1) + th_sh(i+2)^2; Msh(i+2) = max(Msh(i+1), abs(th_sh(i+2)));
    end
end
out = struct('record_id', opt.record_id, 'method', M.name, 'dt', opt.dt, 'ux', ux, 'uy', uy, 'th', th, ...
             'f_dev', fd, 'theta', thd, 'kappa', kd, 'wall_s', toc(t_run), 'rt', rmfield(P.rt, 'noise'), 'M', M);
out.metrics = response_metrics(ux, uy, th);
out.timeline = CS.log(1:CS.nlog, :);
out.clog = CS.clog;
out.queue = struct('n_expired', QS.n_expired, 'n_applied', QS.n_applied);
out.forecast = struct('log', FS.log, 'miss_busy', FS.miss_busy, 'miss_deadline', FS.miss_deadline, 'n_run', FS.n_run);
if ~isfield(FS, 'miss_busy'), out.forecast = struct('log', zeros(0,5), 'miss_busy', 0, 'miss_deadline', 0, 'n_run', 0); end
out.trigger_stamp = BS.trig;
out.shadow = struct('on', do_sh, 'th', th_sh, 'Q', Qsh, 'M', Msh);
out.jlog = CS.jlog; out.tlog = CS.tlog;
end
