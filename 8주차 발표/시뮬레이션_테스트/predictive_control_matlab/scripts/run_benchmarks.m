function out = run_benchmarks(tag, methods, events, opt)
% RUN_BENCHMARKS  비교군 폐루프 모의 (계획서 11·12·13절 D/F/G).
%  tag     : 결과 꼬리표 (예 'D_dev', 'F_pilot')
%  methods : pc_method 이름 cell (U는 자동 포함)
%  events  : 사건 ID cell. 기본 cfg.data.dev_events_control (El Centro·포항·고베, 각 기록 1회). test 사건은 거부.
%  opt.dt (기본 cfg.plant.dt), opt.models (struct: var, lstm 모델 파일 경로), opt.override (pc_method 덮어쓰기 struct)
%  opt.cfg (개발 진단용 설정 변형; 없으면 config/experiment.json), opt.diag_true (후보별 참 미래 평가 기록, 제어에 쓰지 않음)
%  opt.keep_series (시계열·후보 기록을 results/benchmarks_<tag>.mat에 저장)
%  결과: results/control_metrics_record_<tag>.csv, control_metrics_event_<tag>.csv, comparison_summary_<tag>.csv,
%        logs/command_timeline_<tag>.csv, logs/runtime_<tag>.csv, logs/failures_<tag>.csv
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
if nargin >= 4 && isfield(opt, 'cfg'), cfg = opt.cfg; else, cfg = pc_config(); end
if nargin < 3 || isempty(events), events = cfg.data.dev_events_control; end
if nargin < 4, opt = struct(); end
if ~isfield(opt, 'dt'), opt.dt = cfg.plant.dt; end
if ~isfield(opt, 'override'), opt.override = struct(); end
if ~isfield(opt, 'diag_true'), opt.diag_true = false; end
if ~isfield(opt, 'keep_series'), opt.keep_series = opt.diag_true; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end   % 스크립트 기능 점검용 기록 자르기 (결과 해석에 쓰지 않음)
if any(ismember(events, cfg.data.test_events)) && ~isfield(opt, 'allow_test')
    error('run_benchmarks: 시험 사건은 evaluate_test.m에서만 한 번 평가한다');
end
tag = [tag out_tag()];
methods = [{'U'}, methods(~strcmp(methods, 'U'))];
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
rids = man.record_id(ismember(man.event_id, events));
models = struct();
if isfield(opt, 'models')
    fn = fieldnames(opt.models);
    for k = 1:numel(fn)
        if strcmp(fn{k}, 'torch')                   % PyTorch smoke 모델: 경로(확장자 없이) → Python 호출용·MATLAB 재구현용 둘 다
            models.torch = load_torch_model(opt.models.torch, true); models.lstmnat = load_torch_model(opt.models.torch, false);
        elseif strcmp(fn{k}, 'lstmnat')             % 같은 가중치의 MATLAB 재구현만 (Python 없이)
            models.lstmnat = load_torch_model(opt.models.lstmnat, false);
        elseif strcmp(fn{k}, 'scorer')              % 8주차 v2 공동 후보 점수망 (MATLAB 추론)
            models.scorer = load_scorer(opt.models.scorer);
        else
            models.(fn{k}) = load_model(opt.models.(fn{k}));
        end
    end
end
recs = struct('record_id', {}, 'event_id', {}, 'method', {}, 'metrics', {}, 'burden', {}, 'wall_s', {}, 'reasons', {}, 'Jtot', {});
series = struct('record_id', {}, 'method', {}, 'ux', {}, 'uy', {}, 'th', {}, 'f_dev', {}, 'theta', {}, 'kappa', {}, ...
                'timeline', {}, 'clog', {}, 'forecast_log', {}, 'rt', {}, 'jlog', {});
pv = run_provenance(); pv.tag = tag; pv.methods = methods; pv.events = events; pv.override = opt.override;
pv.timing_mode = cfg.latency.timing_mode; pv.compute_s = cfg.latency.compute_s; pv.compute_measured = cfg.latency.compute_measured;
fid = fopen(fullfile(root, 'logs', ['provenance_' tag '.json']), 'w'); fprintf(fid, '%s', jsonencode(pv)); fclose(fid);
ft = fopen(fullfile(root, 'logs', ['command_timeline_' tag '.csv']), 'w');
fprintf(ft, ['env,method,record_id,sim_time,newest_observation_time,forecast_origin,ready_time,arrival_time,actual_apply_step,' ...
             'commanded_f,commanded_theta,commanded_kappa,actual_f,actual_theta,actual_kappa,R_f,R_theta,R_kappa,n_candidates,n_feasible,' ...
             'J_best,J_R,calculation_seconds,deadline_miss,fallback_reason,R_calculation_seconds,apply_time,slack_s,' ...
             'forecast_ready_to_apply_s,origin_to_apply_s,remaining_horizon_s,is_pump_angle,is_valve\n']);
fr = fopen(fullfile(root, 'logs', ['runtime_' tag '.csv']), 'w');
fprintf(fr, 'env,method,record_id,n_steps,wall_s,n_decisions,select_s_median,select_s_p95,select_s_max,forecast_runs,forecast_s_median,forecast_s_p95,forecast_s_max,forecast_miss_busy,forecast_miss_deadline,d_s,d_cmd,d_fc,unmeasured\n');
ff = fopen(fullfile(root, 'logs', ['failures_' tag '.csv']), 'w');
fprintf(ff, 'env,method,record_id,chose_R,chose_cand,no_forecast,horizon,nan,no_feasible,deadline,deadline_hold,queue_expired\n');
codes = {'', 'chose_R', 'chose_cand', 'no_forecast', 'horizon', 'nan', 'no_feasible', 'deadline', 'deadline_hold'};
for k = 1:numel(rids)
    [ax, ay, meta] = load_record(cfg, rids{k}, opt.dt);
    if isfinite(opt.max_seconds), n = min(numel(ax), round(opt.max_seconds/opt.dt) + 1); ax = ax(1:n); ay = ay(1:n); end
    for m = 1:numel(methods)
        M = pc_method(cfg, methods{m}, opt.override);
        o2 = struct('dt', opt.dt, 'record_id', rids{k}, 'diag_true', opt.diag_true);
        if strcmp(M.forecaster, 'var'), o2.model = models.var; end
        if strcmp(M.forecaster, 'lstm'), o2.model = models.lstm; end
        if strcmp(M.forecaster, 'torch'), o2.model = models.torch; end
        if strcmp(M.forecaster, 'lstmnat'), o2.model = models.lstmnat; end
        if isfield(M, 'jscorer') && M.jscorer, o2.scorer = models.scorer; end
        o = run_closed_loop(ax, ay, cfg, M, o2);
        bur = burden(o);
        tlr = o.timeline; rs = zeros(1, 8); for c = 1:8, rs(c) = sum(tlr(:,20) == c & tlr(:,4) == 1); end   % 펌프·각도 결정의 사유별 수
        sc = jsondecode(fileread(fullfile(root, cfg.controller.scales_file)));
        Jt = mean(((o.ux/sc.sx).^2 + (o.uy/sc.sy).^2 + (o.th/sc.st).^2)/3);                        % 전체 기록 목적함수(이동 항 제외)
        recs(end+1) = struct('record_id', rids{k}, 'event_id', meta.event_id, 'method', methods{m}, ...
                             'metrics', o.metrics, 'burden', bur, 'wall_s', o.wall_s, 'reasons', rs, 'Jtot', Jt); %#ok<AGROW>
        tl = o.timeline; Hs = o.rt.Hn*o.rt.r;
        for j = 1:size(tl, 1)
            g = tl(j,3); ga = min(g + 2, numel(o.f_dev));
            rc = codes{tl(j,20) + 1};
            fprintf(ft, '%s,%s,%s,%.4f,%.4f,%.4f,%.4f,%.4f,%d,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%g,%g,%.6g,%.6g,%.6g,%d,%s,%.6g,%.4f,%.4f,%.4f,%.4f,%.4f,%d,%d\n', ...
                env_string(), methods{m}, rids{k}, tl(j,1)*opt.dt, tl(j,2)*opt.dt, tl(j,12)*opt.dt, tl(j,13)*opt.dt, tl(j,22)*opt.dt, g, ...
                tl(j,6), tl(j,7), tl(j,8), o.f_dev(ga), o.theta(ga), o.kappa(ga), tl(j,9), tl(j,10), tl(j,11), ...
                tl(j,14), tl(j,15), tl(j,16), tl(j,17), tl(j,18), tl(j,19), rc, tl(j,21), g*opt.dt, (g - tl(j,22))*opt.dt, ...
                (g - tl(j,13))*opt.dt, (g - tl(j,12))*opt.dt, (tl(j,12) + Hs - g)*opt.dt, tl(j,4), tl(j,5));
        end
        if opt.keep_series
            series(end+1) = struct('record_id', rids{k}, 'method', methods{m}, 'ux', o.ux, 'uy', o.uy, 'th', o.th, ...
                'f_dev', o.f_dev, 'theta', o.theta, 'kappa', o.kappa, 'timeline', tl, 'clog', o.clog, ...
                'forecast_log', o.forecast.log, 'rt', o.rt, 'jlog', o.jlog); %#ok<AGROW>
        end
        sw = tl(:,18); sw = sw(~isnan(sw)); fw = o.forecast.log(:,4); fw = fw(~isnan(fw));
        um = sprintf('%s;', M.unmeasured{:}); if ~isempty(um), um = um(1:end-1); end
        line = [sprintf('%s,%s,%s,%d,%.3f,%d,', env_string(), methods{m}, rids{k}, numel(ax), o.wall_s, size(tl,1)), qstr(sw), ...
                sprintf(',%d,', numel(fw)), qstr(fw), sprintf(',%d,%d,%d,%d,%d,', o.forecast.miss_busy, o.forecast.miss_deadline, o.rt.d_s, o.rt.d_cmd, o.rt.d_fc), um];
        fprintf(fr, '%s\n', line);
        cnt = zeros(1, 8);
        for c = 2:9, cnt(c-1) = sum(tl(:,20) == c - 1); end
        fprintf(ff, '%s\n', [sprintf('%s,%s,%s,', env_string(), methods{m}, rids{k}), sprintf('%d,', cnt), sprintf('%d', o.queue.n_expired)]);
        fprintf('%-20s %-20s 6지표=%s  %.1f s\n', rids{k}, methods{m}, sprintf('%.4g ', o.metrics), o.wall_s);
    end
end
fclose(ft); fclose(fr); fclose(ff);
S = compute_scores(recs, methods, cfg);
write_benchmark_tables(root, tag, recs, S, methods, cfg);
out = struct('recs', recs, 'S', S, 'series', series, 'provenance', pv, 'cfg', cfg);
save(fullfile(root, 'results', ['benchmarks_' tag '.mat']), 'out', '-v7');
end

function b = burden(o)
% 장치 동작량: [총 회전량 deg, 펌프 진동수 총변화 Hz, 밸브 전환 횟수]
b = [sum(abs(diff(o.theta)))*180/pi, sum(abs(diff(o.f_dev(2:end)))), sum(diff(o.kappa(2:end)) ~= 0)];
end

function s = qstr(v)
if isempty(v), s = 'NaN,NaN,NaN'; return; end
v = sort(v); s = sprintf('%.6g,%.6g,%.6g', median(v), v(max(1, ceil(0.95*numel(v)))), v(end));
end

function M = load_model(f)
S = load(f);
if isfield(S, 'model'), M = S.model; else, M = S; end
end
