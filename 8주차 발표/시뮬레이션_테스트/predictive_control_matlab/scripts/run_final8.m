function R = run_final8(opt)
% RUN_FINAL8  8주차 탐색적 AI 실험 — 폐루프 비교 (사전 지정: report/prereg_week8_final.md, 계획 §5·§7·§8)
%  주 구조(개선안 1개, 고정): C1 + 원래 시각 R 경로 + 그림자 R 누적 비틀림 제한 + 절대 각도 {0,22.5,45,67.5,90}°
%  참고 구조: 현행 C1(±15°, 예측 구간 R 후보 비교) + 원래 시각 R 경로
%  방식: R(원래 R), SIMPLE-zero, SIMPLE-persistence, AINAT-C1(학습 AI seed 8401, MATLAB 재구현), PREVIEW-C1(실제 미래 입력 참고군)
%  사건: opt.events = 'dev'(기본, El Centro·고베·포항) | 'all'(기존 11개 기록 전체, 계산시간이 허락할 때만)
%  주 조건: 고정 시간축(nominal). 선택 예산 = 지속 부하 p99(0.01 s 올림)를 개발 결과를 보기 전에 측정. 센서·통신 0, 예측 준비 1스텝, R 1스텝.
%  보조: 주 구조 실측 지연 1회 (늦음·fallback ≥ 90 %면 '계산 예산 부적합'으로 표시)
%  결과: week08_submission/results/*.csv (평균 단위 표시), report/F8_summary*.md, 그림용 시간이력·예측 CSV
%  opt.allow_prelim, opt.max_seconds (기능 점검), opt.model (모델 경로), opt.seed_models (추가 시드 경로 cell, 있으면 AI만 추가 실행)
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'allow_prelim'), opt.allow_prelim = false; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
if ~isfield(opt, 'events'), opt.events = 'dev'; end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct && ~opt.allow_prelim, error('run_final8: MATLAB에서 실행'); end
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg = pc_config(); sfx = ''; if isfinite(opt.max_seconds), sfx = '_trunc'; end
if strcmp(opt.events, 'all'), sfx = [sfx '_all']; end
tag = [out_tag() sfx];
od = fullfile(root, 'week08_submission', 'results'); if ~exist(od, 'dir'), mkdir(od); end
tp = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', cfg.lstm.pilot8_seed));
if isfield(opt, 'model'), tp = opt.model; end
if ~exist([tp '_weights.mat'], 'file'), error('run_final8: 학습 모델 %s 없음 (run_week08_laptop P 먼저)', tp); end
if strcmp(opt.events, 'all')
    man = read_manifest(fullfile(root, cfg.paths.record_manifest)); ev = unique(man.event_id, 'stable')';
else
    ev = cfg.data.dev_events_control(:)';
end
M = {'R', 'SIMPLE-zero', 'SIMPLE-persistence', 'AINAT-C1', 'PREVIEW-C1'};
mo = struct('lstmnat', tp);
cS = cfg; c1 = cS.controller.C1; c1.default_path = 'ontime'; c1.constraint = 'shadow'; c1.angle_mode = 'absolute'; c1.angle_grid_deg = [0 22.5 45 67.5 90];
cS.controller.C1 = c1;
cC = cfg; c1 = cC.controller.C1; c1.default_path = 'ontime'; c1.constraint = 'window_R'; c1.angle_mode = 'relative'; cC.controller.C1 = c1;
% ---- 재사용: 폐루프 실행은 끝났고 내보내기·보고만 다시 할 때 (같은 커밋의 저장 결과) ----
if isfield(opt, 'reuse') && opt.reuse
    fR = fullfile(root, 'results', ['F8' tag '.mat']);
    if ~exist(fR, 'file'), error('run_final8: 재사용할 %s 없음', fR); end
    L = load(fR); R = L.R; B = cell(1, 3); nm = {'S_main', 'C_ref', 'S_actual'};
    for k = 1:3, Lb = load(fullfile(root, 'results', ['benchmarks_F8_' nm{k} sfx out_tag() '.mat'])); B{k} = Lb.out; end
    fprintf('재사용: %s (폐루프 다시 실행하지 않음)\n', fR);
    write_csv(od, tag, R.runs, B); export_series(od, tag, B{1}, M); export_forecasts(od, tag, cfg, R.model, B{1}, R.events);
    write_report(root, tag, R, cfg);
    fprintf('폐루프 비교 마무리 → report/F8_summary%s.md, week08_submission/results/\n', tag);
    return;
end
% ---- 시간 예산 (지속 부하, 결과를 보기 전에) ----
[bS, wS] = sustained_budget(cS, opt); [bC, wC] = sustained_budget(cC, opt);
% 계산량 규칙 (폐루프 결과를 보기 전에 정함, prereg §제어 구조): 남은 예측 구간이 최소 평가 2 s 이상이려면
% 결정 앞당김 ≤ 4 − 0.21 − 2 ≈ 1.79 s. 여유를 두어 주 구조 예산이 1.5 s를 넘으면 진동수 후보를 현재 값 하나로 줄이고 다시 잰다.
reduced = false;
if bS > 1.5 && isfinite(opt.max_seconds) == 0
    cS.controller.C1.df_hz = 0; reduced = true;
    [bS, wS] = sustained_budget(cS, opt);
    fprintf('주 구조 예산이 1.5 s 초과 → 진동수 후보를 현재 값으로 줄임, 다시 잰 예산 %.2f s\n', bS);
end
fprintf('선택 예산(지속 부하 p99): 주 구조 %.2f s, 현행 C1 %.2f s\n', bS, bC);
run = @(tg, c, mm, m_) run_benchmarks([tg sfx], mm, ev, struct('cfg', c, 'models', m_, 'keep_series', true, 'max_seconds', opt.max_seconds));
nm = {'S_main', 'C_ref', 'S_actual'}; cs = {fixed(cS, bS), fixed(cC, bC), actual_cfg(cS, bS, isoct)};
E = cell(1, numel(nm)); B = cell(1, numel(nm));
for k = 1:numel(nm)
    E{k} = struct('run', nm{k}, 't_start', datestr(now, 'yyyy-mm-dd HH:MM:SS'), 'env', env_string());
    B{k} = run(['F8_' nm{k}], cs{k}, M, mo);
    E{k}.t_end = datestr(now, 'yyyy-mm-dd HH:MM:SS'); E{k}.wall = sum([B{k}.recs.wall_s]);
end
S = cellfun(@(b, n) summarize(b, n, M), B, nm, 'UniformOutput', false);
% 추가 시드 (같은 설정, AI만): 성능을 보고 고르지 않고 모두 보고
SD = {};
if isfield(opt, 'seed_models')
    for q = 1:numel(opt.seed_models)
        Bq = run(sprintf('F8_S_main_seed%d', q), fixed(cS, bS), {'R', 'AINAT-C1'}, struct('lstmnat', opt.seed_models{q}));
        SD{end+1} = struct('model', opt.seed_models{q}, 'S', summarize(Bq, 'seed', {'R', 'AINAT-C1'})); %#ok<AGROW>
    end
end
R = struct('provenance', pv, 'budget', [bS bC], 'reduced_freq', reduced, 'budget_walls', {{wS, wC}}, 'runs', {S}, 'env', {E}, 'model', tp, 'events', {ev}, 'seeds', {SD});
save(fullfile(root, 'results', ['F8' tag '.mat']), 'R', '-v7');
write_csv(od, tag, S, B);
if ~isfinite(opt.max_seconds) || opt.max_seconds > 0, export_series(od, tag, B{1}, M); end
export_forecasts(od, tag, cfg, tp, B{1}, ev);
write_report(root, tag, R, cfg);
fprintf('폐루프 비교 완료 → report/F8_summary%s.md, week08_submission/results/\n', tag);
end

% =====================================================================
function [b, w] = sustained_budget(c, opt)
% 고베 1회를 워밍업으로 버리고, El Centro·포항·고베 SIMPLE-zero 펌프·각도 결정의 선택 계산 p99를 0.01 s 올림
cm = c; cm.latency.timing_mode = 'nominal';
% 원래 시각 R 경로에서는 C1 제안 결정이 R 지령 시각(적용 1스텝 전)보다 늦으면 쓰이지 않으므로 선택 예산을 1스텝으로 둔다(계산시간은 실측 기록만 사용)
z = struct('sensor_s', 0, 'comm_s', 0, 'extra_info_s', 0, 'select_s', 0.01, 'forecast_s', 0.01);
rec = {'PEER14', 'ElCentro_1940', 'Pohang_2017_BUS2', 'PEER14'}; w = [];
for k = 1:numel(rec)
    [ax, ay] = load_record(cm, rec{k}, cm.plant.dt);
    if isfinite(opt.max_seconds), n = min(numel(ax), round(opt.max_seconds/cm.plant.dt) + 1); ax = ax(1:n); ay = ay(1:n); end
    o = run_closed_loop(ax, ay, cm, pc_method(cm, 'SIMPLE-zero', z), struct('dt', cm.plant.dt));
    if k > 1, t = o.timeline(o.timeline(:,4) == 1, 18); w = [w; t(~isnan(t))]; end %#ok<AGROW>
end
w = sort(w);
if isempty(w)                                         % 기능 점검용으로 기록을 짧게 자르면 결정이 없을 수 있음
    if isfinite(opt.max_seconds), b = 0.51; return; end
    error('run_final8: 예산 측정용 C1 결정 기록이 없음');
end
b = ceil(w(max(1, ceil(0.99*numel(w))))/0.01 - 1e-9)*0.01;
end

function c = fixed(c, sel)
c.latency.timing_mode = 'nominal';
c.latency.sensor_s = 0; c.latency.comm_s = 0; c.latency.extra_info_s = 0;
c.latency.inject_select_s = 0; c.latency.inject_forecast_s = 0;
cs = c.latency.compute_s; cs.R = 0.01; cs.select_C1 = sel;
for f = {'forecast_zero', 'forecast_persistence', 'forecast_preview', 'forecast_lstmnat'}, cs.(f{1}) = 0.01; end
c.latency.compute_s = cs;
end

function c = actual_cfg(c, sel, isoct)
c.latency.timing_mode = 'actual'; if isoct, c.latency.timing_mode = 'nominal'; end
c.latency.compute_s.select_C1 = sel;
if ~isfield(c.latency.compute_s, 'forecast_lstmnat') || isempty(c.latency.compute_s.forecast_lstmnat), c.latency.compute_s.forecast_lstmnat = 0.01; end
end

% =====================================================================
function T = summarize(B, name, M)
S = B.S; iR = find(strcmp(S.methods, 'R')); iU = find(strcmp(S.methods, 'U'));
T = struct('run', name, 'mode', B.cfg.latency.timing_mode, 'events', {S.events(:)'}, 'm', struct([]));
mm = struct('method', {}, 'S', {}, 'dS', {}, 'dS_event', {}, 'red_event', {}, 'n_better', {}, 'n_worse', {}, 'thmax', {}, 'thrms', {}, ...
            'viol_ev', {}, 'viol_rec', {}, 'worst_th', {}, 'burden', {}, 'd_cmd', {}, 'late', {}, 'reasons', {}, 'sel_p50', {}, 'sel_p95', {}, 'n_cand', {});
for q = 1:numel(M)
    m = find(strcmp(S.methods, M{q}));
    d = (S.score_event(:, m) - S.score_event(:, iR))';
    x = struct('method', M{q}, 'S', S.S(m), 'dS', mean(d), 'dS_event', d, 'red_event', S.red_event(:, :, m), 'n_better', sum(d > 0), 'n_worse', sum(d < 0), ...
               'thmax', (S.red_event(:, 5, m) - S.red_event(:, 5, iR))', 'thrms', (S.red_event(:, 6, m) - S.red_event(:, 6, iR))');
    x.viol_ev = sum(x.thmax < 0 | x.thrms < 0); x.worst_th = min([x.thmax, x.thrms, 0]);
    rr = B.recs(strcmp({B.recs.method}, M{q})); nv = 0; bu = zeros(1, 3);
    for k = 1:numel(rr)
        u = B.recs(strcmp({B.recs.method}, 'U') & strcmp({B.recs.record_id}, rr(k).record_id)).metrics;
        b = B.recs(strcmp({B.recs.method}, 'R') & strcmp({B.recs.record_id}, rr(k).record_id)).metrics;
        nv = nv + any((1 - rr(k).metrics(5:6)./u(5:6)) < (1 - b(5:6)./u(5:6)));
        bu = bu + rr(k).burden/numel(rr);
    end
    x.viol_rec = nv; x.burden = bu;
    ss = B.series(strcmp({B.series.method}, M{q})); L = [];
    for k = 1:numel(ss)
        tl = ss(k).timeline; tl = tl(tl(:,4) == 1, :); L = [L; tl(:,19), tl(:,20), tl(:,18), tl(:,14)]; x.d_cmd = ss(k).rt.d_cmd; %#ok<AGROW>
    end
    x.late = mean(L(:,1)); x.reasons = arrayfun(@(c) mean(L(:,2) == c), 1:8);
    w = sort(L(~isnan(L(:,3)), 3)); if isempty(w), w = NaN; end
    x.sel_p50 = w(max(1, ceil(0.5*numel(w)))); x.sel_p95 = w(max(1, ceil(0.95*numel(w))));
    nc = L(~isnan(L(:,4)), 4); if isempty(nc), x.n_cand = [NaN NaN NaN]; else, x.n_cand = [min(nc), median(nc), max(nc)]; end
    mm(end+1) = x; %#ok<AGROW>
end
T.m = mm;
g = @(n) mm(strcmp({mm.method}, n));
if any(strcmp(M, 'SIMPLE-zero'))
    P = g('PREVIEW-C1'); A = g('AINAT-C1'); Z = g('SIMPLE-zero'); Q = g('SIMPLE-persistence');
    [bs, ib] = max([Z.dS, Q.dS]); sn = {'SIMPLE-zero', 'SIMPLE-persistence'};
    T.best_simple = sn{ib}; T.ai_R = A.dS; T.ai_zero = A.dS - Z.dS; T.ai_pers = A.dS - Q.dS; T.ai_best = A.dS - bs;
    T.preview_R = P.dS; T.G2 = P.dS; T.G3 = P.dS - bs;
    T.fallback = 1 - A.reasons(2);      % AI 결정 중 제안이 적용되지 않은 비율 (chose_cand 외 전부)
else
    T.ai_R = g('AINAT-C1').dS;
end
end

function write_csv(od, tag, S, B)
f = fopen(fullfile(od, ['F8_runs' tag '.csv']), 'w');
fprintf(f, '# 평균 단위: 6지표 저감률(무제어 대비 %%) → 기록 평균 → 사건 내 평균 → 사건 동일 가중 평균. dS = 방식 − 원래 R (%%p)\n');
fprintf(f, 'run,timing_mode,method,S_pct,dS_vs_R_pp,dS_events,n_better,n_worse,thmax_margin_events,thrms_margin_events,violation_events,violation_records,worst_torsion_pp,rotation_deg_per_record,pump_hz_per_record,valve_switches_per_record,d_cmd,late_frac,frac_chose_R,frac_chose_cand,frac_no_forecast,frac_horizon,frac_nan,frac_no_feasible,frac_deadline,frac_deadline_hold,select_s_p50,select_s_p95,n_cand_min,n_cand_med,n_cand_max\n');
for r = 1:numel(S)
    t = S{r};
    for q = 1:numel(t.m)
        x = t.m(q);
        fprintf(f, '%s,%s,%s,%.4f,%.4f,%s,%d,%d,%s,%s,%d,%d,%.4f,%.2f,%.5f,%.1f,%d,%.4f,%s,%.4f,%.4f,%g,%g,%g\n', t.run, t.mode, x.method, x.S, x.dS, vs(x.dS_event), ...
                x.n_better, x.n_worse, vs(x.thmax), vs(x.thrms), x.viol_ev, x.viol_rec, x.worst_th, x.burden, x.d_cmd, x.late, ...
                strjoin(arrayfun(@(v) sprintf('%.4f', v), x.reasons, 'UniformOutput', false), ','), x.sel_p50, x.sel_p95, x.n_cand);
    end
end
fclose(f);
g = fopen(fullfile(od, ['F8_event_metrics' tag '.csv']), 'w');
fprintf(g, '# 6지표 저감률 %% (무제어 대비), 사건 내 기록 평균\nrun,method,event,red_uxmax,red_uxrms,red_uymax,red_uyrms,red_thmax,red_thrms,mean6,dS_vs_R_pp\n');
for r = 1:numel(S)
    t = S{r};
    for q = 1:numel(t.m)
        x = t.m(q);
        for e = 1:numel(t.events)
            fprintf(g, '%s,%s,%s,%s,%.4f,%.4f\n', t.run, x.method, t.events{e}, strjoin(arrayfun(@(v) sprintf('%.4f', v), x.red_event(e,:), 'UniformOutput', false), ','), mean(x.red_event(e,:)), x.dS_event(e));
        end
    end
end
fclose(g);
end

function s = vs(v), s = strjoin(arrayfun(@(x) sprintf('%+.2f', x), v, 'UniformOutput', false), ' '); end

function export_series(od, tag, B, M)
% 그림용 시간이력: 사건별 무제어·R·AI·SIMPLE-zero·PREVIEW 응답과 장치 상태, AI 지령 목표
rids = unique({B.series.record_id}, 'stable');
for k = 1:numel(rids)
    f = fopen(fullfile(od, sprintf('F8_series_%s%s.csv', rids{k}, tag)), 'w');
    fprintf(f, 'method,t_s,ux_m,uy_m,th_rad,pump_f_dev_hz,rotation_rad,valve_kappa\n');
    for q = [{'U'}, M]
        sr = B.series(strcmp({B.series.record_id}, rids{k}) & strcmp({B.series.method}, q{1}));
        if isempty(sr), continue; end
        dt = B.cfg.plant.dt; n = numel(sr.ux);
        for j = 1:2:n                                  % 0.02 s 간격으로 줄여 저장
            fprintf(f, '%s,%.2f,%.6e,%.6e,%.6e,%.6f,%.5f,%.4f\n', q{1}, (j-1)*dt, sr.ux(j), sr.uy(j), sr.th(j), sr.f_dev(j), sr.theta(j), sr.kappa(j));
        end
    end
    fclose(f);
    f = fopen(fullfile(od, sprintf('F8_commands_%s%s.csv', rids{k}, tag)), 'w');
    fprintf(f, 'method,decision_t_s,last_obs_t_s,forecast_origin_t_s,apply_t_s,cmd_f_hz,cmd_theta_rad,R_f_hz,R_theta_rad,n_cand,n_feasible,select_wall_s,late,reason_code\n');
    for q = M
        sr = B.series(strcmp({B.series.record_id}, rids{k}) & strcmp({B.series.method}, q{1}));
        tl = sr.timeline(sr.timeline(:,4) == 1, :); dt = B.cfg.plant.dt;
        for j = 1:size(tl, 1)
            fprintf(f, '%s,%.2f,%.2f,%.2f,%.2f,%.6g,%.6g,%.6g,%.6g,%g,%g,%.4f,%g,%d\n', q{1}, tl(j,1)*dt, tl(j,2)*dt, tl(j,12)*dt, tl(j,3)*dt, tl(j,6), tl(j,7), tl(j,9), tl(j,10), tl(j,14), tl(j,15), tl(j,18), tl(j,19), tl(j,20));
        end
    end
    fclose(f);
end
end

function export_forecasts(od, tag, cfg, tp, B, ev)
% (1) 대표 예측: 사건마다 사전 규칙 = '지반가속도 크기(√(ax²+ay²)) 최대 시각 이후 첫 0.2 s 격자'에서 발행한 예측
% (2) 제어 시점 잔여 구간 오차: AI 폐루프(주 구조)의 각 펌프·각도 결정에서 예측 기준시각 o, 적용 g → [g, o+H] 구간 RMSE
mdl = load_torch_model(tp, false); Hn = mdl.Hn; Wn = round(cfg.forecast.window_s*100); r = 1;
man = read_manifest(fullfile(cfg.root, cfg.paths.record_manifest));
f1 = fopen(fullfile(od, ['F8_forecast_examples' tag '.csv']), 'w');
fprintf(f1, 'record_id,origin_t_s,lead_s,true_x,true_y,zero_x,zero_y,persistence_x,persistence_y,ai_x,ai_y\n');
f2 = fopen(fullfile(od, ['F8_forecast_remaining_error' tag '.csv']), 'w');
fprintf(f2, 'record_id,origin_t_s,apply_t_s,remaining_s,rmse_zero,rmse_persistence,rmse_ai\n');
for k = 1:numel(man.record_id)
    if ~any(strcmp(man.event_id{k}, ev)), continue; end
    rid = man.record_id{k};
    [x, y] = load_record(cfg, rid, 0.01);
    tg = trig100(x, y, cfg.sensor.trigger_mps2); if tg < 0, continue; end
    [~, im] = max(sqrt(x.^2 + y.^2)); q0 = max(ceil((tg + 100)/20)*20, ceil((im - 1)/20)*20);
    if q0 + Hn + 1 <= numel(x)
        [Y0, Yp, Ya] = three(x, y, q0, tg, r, Wn, Hn, mdl);
        for j = 1:Hn
            fprintf(f1, '%s,%.2f,%.2f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f\n', rid, q0*0.01, j*0.01, x(q0+1+j), y(q0+1+j), Y0(j,1), Y0(j,2), Yp(j,1), Yp(j,2), Ya(j,1), Ya(j,2));
        end
    end
    sr = B.series(strcmp({B.series.record_id}, rid) & strcmp({B.series.method}, 'AINAT-C1'));
    if isempty(sr), continue; end
    tl = sr.timeline(sr.timeline(:,4) == 1 & ~isnan(sr.timeline(:,12)), :);
    for j = 1:size(tl, 1)
        o = tl(j,12); g = tl(j,3); if o + Hn + 1 > numel(x) || g >= o + Hn, continue; end
        [Y0, Yp, Ya] = three(x, y, o, tg, r, Wn, Hn, mdl);
        idx = (g - o):Hn; tr = [x(o+1+idx), y(o+1+idx)];
        e = @(Yh) mean(sqrt(mean((Yh(idx,:) - tr).^2, 1)));
        fprintf(f2, '%s,%.2f,%.2f,%.2f,%.5f,%.5f,%.5f\n', rid, o*0.01, g*0.01, (o + Hn - g)*0.01, e(Y0), e(Yp), e(Ya));
    end
end
fclose(f1); fclose(f2);
end

function [Y0, Yp, Ya] = three(x, y, q, tg, r, Wn, Hn, mdl)
[wx, wy, mk] = make_window(x, y, q, tg, r, Wn);
Y0 = forecast_simple('zero', wx, wy, mk, [], Hn); Yp = forecast_simple('persistence', wx, wy, mk, [], Hn);
Ya = unpack_forecast_target(lstm_forward(mdl.W, forecast_input(wx, wy, mk, mdl.scaler)), mdl.scaler, Hn);
end

function write_report(root, tag, R, cfg)
f = fopen(fullfile(root, 'report', ['F8_summary' tag '.md']), 'w'); p = @(varargin) fprintf(f, varargin{:});
pv = R.provenance; S = R.runs;
p('# 8주차 폐루프 비교 (탐색적 AI 실험, 개발 평가)\n\n');
p('- 실행: %s, 브랜치 `%s`, 커밋 `%s`, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.branch, pv.commit, pv.digest, pv.config_hash);
p('- 사전 지정 `report/prereg_week8_final.md`. G2·G3 미충족 이후의 범위 제한 탐색 실험이며 기존 관문 통과를 뜻하지 않습니다.\n');
p('- 사건: %s — 모두 이전에 개발에 쓰인 기록이므로 **개발 평가**입니다.\n', strjoin(R.events, ', '));
p('- AI: `%s` (합성 자료로만 학습, 폐루프는 같은 가중치의 MATLAB 재구현). PREVIEW는 실제 미래 입력을 제공한 현재 제어기의 참고 성능입니다.\n', R.model);
p('- 선택 예산(지속 부하 p99): 주 구조 %.2f s, 현행 C1 %.2f s. 고정 시간축: 센서·통신 0, 예측 준비 1스텝, R 1스텝.\n', R.budget(1), R.budget(2));
if isfield(R, 'reduced_freq') && R.reduced_freq, p('- **계산량 규칙 적용**: 주 구조 예산이 1.5 s를 넘어 진동수 후보를 현재 값 하나로 줄였습니다(절대 각도 6개 + R).\n'); end
p('\n');
for r = 1:numel(S)
    t = S{r};
    p('## %s (%s)\n\n사건 순서: %s. 평균 단위: 6지표 → 기록 → 사건 내 → 사건 동일 가중.\n\n', t.run, t.mode, strjoin(t.events, ', '));
    p('| 방식 | S %% | R 대비 %%p | 사건별 | 개선/악화 | θ최대 여유 | θRMS 여유 | 위반 사건/기록 | 최악 | d_cmd | 늦음 | 제안 적용 | 후보 수 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n');
    for q = 1:numel(t.m)
        x = t.m(q);
        p('| %s | %.2f | %+.2f | %s | %d/%d | %s | %s | %d/%d | %+.2f | %d | %.0f %% | %.0f %% | %g/%g/%g |\n', x.method, x.S, x.dS, vs(x.dS_event), x.n_better, x.n_worse, ...
          vs(x.thmax), vs(x.thrms), x.viol_ev, x.viol_rec, x.worst_th, x.d_cmd, 100*x.late, 100*x.reasons(2), x.n_cand);
    end
    p('\n- AI − R %+.2f %%p · AI − SIMPLE-zero %+.2f · AI − SIMPLE-persistence %+.2f · AI − 최선 SIMPLE(%s) %+.2f\n', t.ai_R, t.ai_zero, t.ai_pers, t.best_simple, t.ai_best);
    p('- PREVIEW − R %+.2f (G2 기준 +2: %s) · G3 = PREVIEW − 최선 SIMPLE %+.2f (기준 +0.5: %s)\n', t.preview_R, ok(t.G2 >= 2), t.G3, ok(t.G3 >= 0.5));
    if strcmp(t.mode, 'actual') && t.fallback >= 0.9, p('- **계산 예산 부적합**: AI 결정의 %.0f %%에서 제안이 적용되지 않음 → AI 성능 근거로 쓰지 않음\n', 100*t.fallback); end
    p('\n');
end
if ~isempty(R.seeds)
    p('## 추가 시드 (같은 설정, 주 구조, 고정 시간축)\n\n| 모델 | AI − R %%p |\n|---|---|\n');
    for k = 1:numel(R.seeds), p('| `%s` | %+.2f |\n', R.seeds{k}.model, R.seeds{k}.S.ai_R); end
end
p('\n## 판정 (각각 따로)\n');
t = S{1};
p('- R 대비 +2~3 %%p 목표: AI %+.2f %%p → %s\n', t.ai_R, ok(t.ai_R >= 2));
p('- 단순 예측 대비 AI 추가 기여: AI − 최선 SIMPLE %+.2f %%p → %s\n', t.ai_best, ok(t.ai_best > 0));
a = t.m(strcmp({t.m.method}, 'AINAT-C1'));
p('- 비틀림 허용 0 %%p: AI 위반 사건 %d, 최악 %+.2f %%p → %s\n', a.viol_ev, a.worst_th, ok(a.viol_ev == 0));
p('\n실행 순서: '); for k = 1:numel(R.env), p('%s(%s~%s, %.0f s) ', R.env{k}.run, R.env{k}.t_start, R.env{k}.t_end, R.env{k}.wall); end
p('\n');
fclose(f);
end

function s = ok(c), if c, s = '달성'; else, s = '미달'; end, end

function tg = trig100(x, y, thr)
% build_forecast_dataset와 같은 트리거 규칙 (100 Hz 기록에서 처음 |a| > thr인 스텝)
tg = find(max(abs(x), abs(y)) > thr, 1) - 1;
if isempty(tg), tg = -1; end
end
