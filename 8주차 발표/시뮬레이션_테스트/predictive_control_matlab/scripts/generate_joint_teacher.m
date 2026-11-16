function T = generate_joint_teacher(opt)
% GENERATE_JOINT_TEACHER  공동 후보 점수망 teacher 자료 (계획 §6.2).
%  기록: 합성 1,000 원천의 800/200 분할(build_forecast_dataset과 같은 생성 시드·분할 시드)에서 고정 시드로 train 80, val 20
%  rollout: (1) R rollout (항상 R)  (2) 고정 시드 탐색 rollout (후보 무작위 적용, 물리 검사 없음)
%  상태: 기록당 최대 8 (느린 4 + 빠른 4), 진동 구간(R 응답 직전 2.6 s 정규화 에너지 ≥ 최대의 25 %)에서 고정 시드로 고르고 두 rollout에 반씩 배정
%  라벨: 각 상태의 모든 후보를 실제 미래 지반입력으로 모의 (비인과 teacher). 입력 특징은 그 시각에 준비된 인과 예측(AI)으로 만든다.
%  처리량: opt.n_records(예 2)로 먼저 재고, 100 기록 추정이 6 h를 넘으면 상태를 8 → 4로 줄인다(성능 평가 전, 계획 §6.2).
%  opt.method ('J-AIF'), opt.model (LSTM 경로), opt.budget [slow fast] s, opt.n_records (Inf), opt.states (8), opt.out (data/joint_teacher)
%  결과: <out>.csv (행 = 상태×후보), <out>_meta.json, report/JT_teacher<tag>.md
if nargin < 1, opt = struct(); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
cfg = pc_config(); jt = cfg.joint_scorer.teacher;
if ~isfield(opt, 'method'), opt.method = 'J-AIF'; end
if ~isfield(opt, 'n_records'), opt.n_records = inf; end
if ~isfield(opt, 'states'), opt.states = jt.states_per_record; end
if ~isfield(opt, 'out'), opt.out = fullfile(root, 'data', 'joint_teacher'); end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
if ~isfield(opt, 'budget'), error('generate_joint_teacher: opt.budget [느린 빠른] (s) 필요 — run_week08_laptop JB 결과'); end
c = joint_timeline(cfg, opt.budget);
M = pc_method(c, opt.method);
mdl = [];
if strcmp(M.forecaster, 'lstmnat')
    if ~isfield(opt, 'model'), opt.model = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', cfg.lstm.pilot8_seed)); end
    mdl = load_torch_model(opt.model, false);
end
% ---- 기록 선택 (성능을 보지 않고 고정 시드) ----
sc = cfg.data.pilot; seeds = sc.seed0 + (0:sc.n_sources-1);
rng(cfg.data.split_seed, 'twister'); perm = randperm(sc.n_sources);
tr = sort(perm(1:sc.n_train)); va = sort(perm(sc.n_train+1:end));
rng(jt.select_seed, 'twister');
tr = tr(randperm(numel(tr), jt.n_train_records)); va = va(randperm(numel(va), jt.n_val_records));
L = [tr(:), ones(numel(tr), 1); va(:), 2*ones(numel(va), 1)];      % [원천 번호, 1 train / 2 val]
nrec = min(size(L, 1), opt.n_records);
if isfinite(opt.n_records)                                         % 처리량 측정: train·val에서 하나씩
    L = [L(find(L(:,2) == 1, ceil(nrec/2)), :); L(find(L(:,2) == 2, floor(nrec/2)), :)];
end
sc_ = jsondecode(fileread(fullfile(root, cfg.controller.scales_file)));
rows = zeros(0, 4 + 110); t_rec = zeros(size(L, 1), 1); nst = zeros(size(L, 1), 2);
for k = 1:size(L, 1)
    t0 = tic; sd = seeds(L(k, 1));
    [ax, ay] = gen_synthetic(sd, 0.01);
    ax = ax/max(abs(ax))*cfg.data.pga_const_mps2; ay = ay/max(abs(ay))*cfg.data.pga_const_mps2;
    if isfinite(opt.max_seconds), n = min(numel(ax), round(opt.max_seconds/0.01) + 1); ax = ax(1:n); ay = ay(1:n); end
    % (0) 진동 구간 선택용 R 응답 (예측기 없이)
    o0 = run_closed_loop(ax, ay, c, pc_method(c, 'R'), struct('dt', 0.01));
    e = ((o0.ux/sc_.sx).^2 + (o0.uy/sc_.sy).^2 + (o0.th/sc_.st).^2)/3;
    ce = [0; cumsum(e)]; nt = numel(ax);
    tg = find(max(abs(ax), abs(ay)) > cfg.sensor.trigger_mps2, 1) - 1;
    gmin = tg + round((cfg.forecast.first_after_trigger_s + 0.5)/0.01) + M.R_s/0.01;   % 예측이 준비된 뒤
    gmax = nt - 1 - round(cfg.forecast.min_eval_s/0.01) - 50;
    G1 = (P_nF():P_nF():nt)'; G2 = (100:100:nt)'; G2 = G2(mod(G2, P_nF()) ~= 0);
    pick = @(G) G(G >= gmin & G <= gmax);
    G1 = pick(G1); G2 = pick(G2);
    en = @(G) arrayfun(@(g) (ce(g+1) - ce(max(1, g - 259)))/260, G);
    G1 = G1(en(G1) >= 0.25*max(en([G1; G2]))); G2 = G2(en(G2) >= 0.25*max(en([G1; G2])));
    rng(jt.select_seed + sd, 'twister');
    ns = opt.states/2;
    G1 = G1(sort(randperm(numel(G1), min(ns, numel(G1))))); G2 = G2(sort(randperm(numel(G2), min(ns, numel(G2)))));
    gR = sort([G1(1:2:end); G2(1:2:end)]); gE = sort([G1(2:2:end); G2(2:2:end)]);
    % (1) R rollout, (2) 탐색 rollout — 같은 방식·같은 시간축, 라벨 격자만 다름
    oR = run_closed_loop(ax, ay, c, M, struct('dt', 0.01, 'model', mdl, 'jpolicy', 'R', 'teach_g', gR));
    oE = run_closed_loop(ax, ay, c, M, struct('dt', 0.01, 'model', mdl, 'jpolicy', 'explore', 'explore_seed', jt.explore_seed0 + sd, 'teach_g', gE));
    tl = [oR.tlog; oE.tlog]; ro = [ones(size(oR.tlog, 1), 1); 2*ones(size(oE.tlog, 1), 1)];
    rows = [rows; repmat([sd, L(k, 2)], size(tl, 1), 1), ro, zeros(size(tl, 1), 1), tl]; %#ok<AGROW>
    t_rec(k) = toc(t0); nst(k, :) = [numel(unique(tl(tl(:,2) == 1, 1))), numel(unique(tl(tl(:,2) == 2, 1)))];
    fprintf('teacher %3d/%d syn%05d (%s) 상태 느린 %d 빠른 %d, 행 %d, %.1f s\n', k, size(L, 1), sd, sp(L(k, 2)), nst(k, 1), nst(k, 2), size(tl, 1), t_rec(k));
end
% 상태 번호 (기록·rollout·격자)
if ~isempty(rows), [~, ~, rows(:, 4)] = unique(rows(:, [1 3 5]), 'rows'); end
est_h = mean(t_rec)*(jt.n_train_records + jt.n_val_records)/3600;
hdr = [{'source_seed', 'split', 'rollout', 'state', 'g', 'kind', 'cid', 'isR', 'isHold'}, arrayfun(@(j) sprintf('x%02d', j), 1:98, 'UniformOutput', false), ...
       {'J_true', 'Qc_true', 'Mc_true', 'QR_true', 'MR_true', 'J_pred', 'feas_pred'}];
f = fopen([opt.out '.csv'], 'w'); fprintf(f, '%s\n', strjoin(hdr, ','));
fmt = [repmat('%.10g,', 1, numel(hdr) - 1) '%.10g\n'];
fprintf(f, fmt, rows'); fclose(f);
pv = run_provenance();
meta = struct('provenance', pv, 'method', M.name, 'budget_s', opt.budget, 'd_cmd', [o0.rt.d_cmd_R, oR.rt.d_cmd, oR.rt.d_cmd_V], ...
              'n_records', size(L, 1), 'states_per_record', opt.states, 'rows', size(rows, 1), 'n_states', max(rows(:, 4)), ...
              'sec_per_record', mean(t_rec), 'est_hours_100', est_h, 'records', L(:, 1)' + sc.seed0 - 1, 'split', L(:, 2)', ...
              'label', '실제 미래 지반입력으로 모든 후보 모의 (비인과 teacher). 특징은 인과 예측.', 'model', opt_model(opt));
fj = fopen([opt.out '_meta.json'], 'w'); fprintf(fj, '%s', jsonencode(meta)); fclose(fj);
T = meta;
fprintf('teacher: 기록 %d, 상태 %d, 행 %d, 기록당 %.1f s → 100 기록 추정 %.2f h → %s.csv\n', size(L, 1), meta.n_states, meta.rows, meta.sec_per_record, est_h, opt.out);
end

function n = P_nF(), n = 260; end
function s = sp(v), if v == 1, s = 'train'; else, s = 'val'; end, end
function m = opt_model(o), if isfield(o, 'model'), m = o.model; else, m = ''; end, end
