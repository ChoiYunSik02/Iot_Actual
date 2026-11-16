function R = diagnose_D(opt)
% DIAGNOSE_D  D 단계 개발 진단 (사용자 요청 2026-10-28, 계획서 11·13절). 시험 기준·자료는 바꾸지 않는다.
%  진입 조건: 관문 A·B·SL(Simulink 대조)·C가 모두 MATLAB에서 통과하고, 그 뒤 코드가 바뀌지 않았을 것 (gate.m).
%  실행 내용 (모두 개발 사건 El Centro·포항·고베, 실측 계산시간·timing_mode='actual'):
%   D_main     : R, FIX, SIMPLE-zero, SIMPLE-persistence, PREVIEW-C1 (+ 후보별 참 미래 평가 기록, 제어에 쓰지 않음)
%   D_nominal0 : 같은 방식, 계산 지연 0·nominal (지연·계산시간이 결과에 주는 영향 분리)
%   D_ofat_*   : 후보 폭·예측 지평을 한 요소씩 바꾼 변형 (SIMPLE-persistence, PREVIEW-C1)
%  분석:
%   1) SIMPLE-persistence 대 PREVIEW-C1: 예측 구간 목적함수 / 전체 지표 / 비틀림 제한 / 후보 선택 분해
%   2) 예측 준비 → 지령 적용 경과 시간, 남은 예측 구간, 늦은 지령
%   3) 포항 비틀림 RMS 악화 구간·지령 (시계열)
%   4) 한 요소씩 진단 (±Δf, ±Δθ, 지평 H)
%   5) AI 학습 근거·예상 비용
%  결과: report/D_diagnosis<tag>.md, results/D_*.csv, results/fig_D_pohang_torsion<tag>.png
%  opt.allow_prelim = true : Octave 예비 실행 허용 (관문 검사 생략, 결과에 _octave)
%  opt.skip_ofat = true    : 4)를 건너뜀
%  opt.max_seconds         : 기록을 앞 N초로 자름 (스크립트 기능 점검 전용, 꼬리표 _trunc)
%  Octave 예비 실행은 계산시간이 노트북과 달라 timing_mode='nominal', 계산 지연 0으로 돈다.
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'allow_prelim'), opt.allow_prelim = false; end
if ~isfield(opt, 'skip_ofat'), opt.skip_ofat = false; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
if ~isfield(opt, 'reuse'), opt.reuse = false; end   % true: 이미 저장된 results/benchmarks_<tag>.mat을 다시 씀 (분석만 다시)
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct && ~opt.allow_prelim, error('diagnose_D: MATLAB에서 실행 (Octave 예비는 opt.allow_prelim)'); end
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg = pc_config(); tag = out_tag(); sfx = '';
if isfinite(opt.max_seconds), sfx = '_trunc'; tag = [tag sfx]; end
if isoct, cfg.latency.timing_mode = 'nominal'; end           % Octave 계산시간은 노트북을 대표하지 않음
if ~cfg.latency.compute_measured && ~isoct
    error('diagnose_D: config/latency_measured.json 없음 — measure_runtime 먼저 (run_week08_laptop D가 자동 실행)');
end
dev = cfg.data.dev_events_control;
sc = jsondecode(fileread(fullfile(root, cfg.controller.scales_file)));
C1m = {'SIMPLE-zero', 'SIMPLE-persistence', 'PREVIEW-C1'};
% ---------------- 실행 ----------------
B0 = rb(opt, root, ['D_main' sfx], [{'R', 'FIX'}, C1m], dev, struct('cfg', cfg, 'diag_true', true, 'max_seconds', opt.max_seconds));
cn = cfg; cn.latency.timing_mode = 'nominal';
z = struct('select_s', 0, 'forecast_s', 0);
Bn = rb(opt, root, ['D_nominal0_diag' sfx], [{'R'}, C1m], dev, struct('cfg', cn, 'override', z, 'diag_true', true, 'max_seconds', opt.max_seconds));   % 지연 0: SIMPLE-persistence > PREVIEW가 관찰된 조건
V = {};
if ~opt.skip_ofat
    V = ofat_variants(cfg);
    for v = 1:size(V, 1)
        tg = ['D_ofat_' V{v,1} sfx];
        if strncmp(V{v,1}, 'H', 1)                  % 지평을 바꾸면 후보 모의 길이가 달라지므로 그 지평의 선택 계산시간을 다시 재서 예산으로 쓴다
            [V{v,3}, b] = remeasure_select(V{v,3}, root);
            V{v,2} = sprintf('%s, 선택 예산 재측정 %.3f s', V{v,2}, b); tg = [tg '_tb'];
        end
        V{v,4} = rb(opt, root, tg, {'R', 'SIMPLE-persistence', 'PREVIEW-C1'}, dev, struct('cfg', V{v,3}, 'max_seconds', opt.max_seconds));
    end
end
% ---------------- 분석 ----------------
T1 = analyze_decomposition(B0, sc, cfg, C1m, tag);
T1n = analyze_decomposition(Bn, sc, cn, C1m, [tag '_nominal0']);
T2 = analyze_timing(B0, Bn, cfg, C1m, tag);
rids = {'Pohang_2017_BUS2', 'ElCentro_1940', 'PEER14'};          % 포항(요청) + 실제로 비틀림이 나빠진 사건들
T3 = cell(1, numel(rids));
for k = 1:numel(rids), T3{k} = analyze_torsion(B0, cfg, root, tag, rids{k}); end
T4 = analyze_ofat(B0, V, tag);
Cst = analyze_cost(B0, V, root);
R = struct('T1', T1, 'T1n', T1n, 'T2', T2, 'T3', {T3}, 'T4', {T4}, 'cost', Cst, 'provenance', pv);
save(fullfile(root, 'results', ['D_diagnosis' tag '.mat']), 'R', '-v7');
write_report(R, cfg, root, tag, pv);
fprintf('D 진단 완료 → report/D_diagnosis%s.md\n', tag);
end

% =====================================================================
function B = rb(opt, root, tag, methods, dev, o)
f = fullfile(root, 'results', ['benchmarks_' tag out_tag() '.mat']);
if opt.reuse && exist(f, 'file')
    L = load(f); B = L.out; fprintf('재사용: %s\n', f);
else
    B = run_benchmarks(tag, methods, dev, o);
end
end

% =====================================================================
function [c, b] = remeasure_select(c, ~)
[c, b] = measure_select_budget(c);
end

% =====================================================================
function V = ofat_variants(cfg)
% {이름, 설명, 설정} — 기본값에서 한 요소만 바꾼다. 기본: Δf = ±0.005 Hz, Δθ = ±15°, H = 4 s, 최소 평가 2 s
V = {};
for df = [0.0025, 0.01, 0.017]
    c = cfg; c.controller.C1.df_hz = [-df; 0; df];
    V(end+1,:) = {sprintf('df%.4f', df), sprintf('진동수 후보 ±%.4f Hz', df), c}; %#ok<AGROW>
end
for dth = [7.5, 30, 45]
    c = cfg; c.controller.C1.dtheta_deg = [-dth; 0; dth];
    V(end+1,:) = {sprintf('dth%g', dth), sprintf('각도 후보 ±%g°', dth), c}; %#ok<AGROW>
end
for H = [3, 6, 8]
    c = cfg; c.forecast.horizon_s = H;
    V(end+1,:) = {sprintf('H%g', H), sprintf('예측 지평 %g s (최소 평가 2 s 유지)', H), c}; %#ok<AGROW>
end
% 원인 확인 전용: 예측 구간 비틀림 제한을 끔. 합의된 0 %p 허용 기준을 바꾸는 후보가 아니다(채택 대상 아님).
c = cfg; c.controller.torsion_rel_tol = 1e9;
V(end+1,:) = {'torOFF', '[진단 전용] 예측 비틀림 제한 끔 (채택 대상 아님)', c};
end

% =====================================================================
function T = analyze_decomposition(B, sc, cfg, C1m, tag)
% 1) 방식별: 전체 6지표 / 최대·RMS 분리 / 전체 기록 J / 예측 구간 J(참 미래) / 비틀림 제한 / 후보 선택
recs = B.recs; ev = B.S.events; mt = B.S.methods; iR = find(strcmp(mt, 'R'));
T = struct('method', {}, 'S', {}, 'dS', {}, 'dS_max', {}, 'dS_rms', {}, 'dS_ind', {}, 'Jtot_gain', {}, ...
           'win_gain_chosen', {}, 'win_gain_oracle_feas', {}, 'win_gain_oracle_free', {}, 'rank_corr', {}, ...
           'n_dec', {}, 'frac_R', {}, 'frac_binding', {}, 'frac_true_tor_worse', {}, 'mean_df', {}, 'mean_dth', {}, 'binding_cost', {});
for m = 1:numel(mt)
    if any(strcmp(mt{m}, {'U'})), continue; end
    t = struct();
    t.method = mt{m}; t.S = B.S.S(m); t.dS = B.S.dS(m);
    re = B.S.red_event(:, :, m) - B.S.red_event(:, :, iR);
    t.dS_max = mean(mean(re(:, [1 3 5]), 2)); t.dS_rms = mean(mean(re(:, [2 4 6]), 2)); t.dS_ind = mean(re, 1);
    % 전체 기록 J (사건 평균, R 대비 감소율 %)
    g = zeros(numel(ev), 1);
    for e = 1:numel(ev)
        jm = [recs(strcmp({recs.method}, mt{m}) & strcmp({recs.event_id}, ev{e})).Jtot];
        jr = [recs(strcmp({recs.method}, 'R') & strcmp({recs.event_id}, ev{e})).Jtot];
        g(e) = 100*(1 - mean(jm)/mean(jr));
    end
    t.Jtot_gain = mean(g);
    % 예측 구간 (후보 기록이 있는 C1 방식만)
    t.win_gain_chosen = NaN; t.win_gain_oracle_feas = NaN; t.win_gain_oracle_free = NaN; t.rank_corr = NaN;
    t.n_dec = 0; t.frac_R = NaN; t.frac_binding = NaN; t.frac_true_tor_worse = NaN; t.mean_df = NaN; t.mean_dth = NaN; t.binding_cost = NaN;
    if any(strcmp(mt{m}, C1m))
        ss = B.series(strcmp({B.series.method}, mt{m}));
        G = [];
        for k = 1:numel(ss)
            cl = ss(k).clog; if isempty(cl), continue; end
            ids = unique(cl(:,1))';
            for d = ids
                c = cl(cl(:,1) == d, :);
                if all(isnan(c(:,13))) || ~any(c(:,12) == 1), continue; end
                jR = c(1,13); ch = find(c(:,12) == 1, 1);
                feasT = c(:,14) <= c(1,14)*(1+1e-12) & c(:,15) <= c(1,15)*(1+1e-12);
                [~, ifree] = min(c(:,8));                           % 제한 없이 예측 J 최소
                G(end+1,:) = [100*(1 - c(ch,13)/jR), 100*(1 - min(c(feasT,13))/jR), 100*(1 - min(c(:,13))/jR), ...
                              rankcorr(c(:,8), c(:,13)), ch == 1, ~c(ifree,11), c(ch,15) > c(1,15)*(1+1e-12), ...
                              abs(c(ch,5) - c(1,5)), abs(c(ch,6) - c(1,6))*180/pi, ...
                              100*(1 - c(ifree,13)/jR) - 100*(1 - c(ch,13)/jR)]; %#ok<AGROW>
            end
        end
        if ~isempty(G)
            t.win_gain_chosen = mean(G(:,1)); t.win_gain_oracle_feas = mean(G(:,2)); t.win_gain_oracle_free = mean(G(:,3));
            t.rank_corr = mean(G(~isnan(G(:,4)),4)); t.n_dec = size(G,1); t.frac_R = mean(G(:,5));
            t.frac_binding = mean(G(:,6)); t.frac_true_tor_worse = mean(G(:,7)); t.mean_df = mean(G(:,8)); t.mean_dth = mean(G(:,9));
            if any(G(:,6)), t.binding_cost = mean(G(G(:,6) == 1, 10)); end   % 제한이 걸린 결정에서 '제한 없는 예측 최선'의 참 J 이득 − 선택안
        end
    end
    T(end+1) = t; %#ok<AGROW>
end
f = fopen(fullfile(pc_root(), 'results', ['D_decomposition' tag '.csv']), 'w');
fprintf(f, 'env,method,S,dS_vs_R,dS_max3,dS_rms3,dS_uxmax,dS_uxrms,dS_uymax,dS_uyrms,dS_thmax,dS_thrms,Jtot_gain_pct,win_gain_chosen_pct,win_gain_oracle_feasible_pct,win_gain_oracle_free_pct,rank_corr_Jpred_Jtrue,n_decisions,frac_choose_R,frac_torsion_binding,frac_true_torsion_worse,mean_abs_df_vs_R_hz,mean_abs_dth_vs_R_deg,binding_cost_pct\n');
for k = 1:numel(T)
    t = T(k);
    fprintf(f, '%s,%s,%.4f,%.4f,%.4f,%.4f,%s,%.4f,%.4f,%.4f,%.4f,%.4f,%d,%.4f,%.4f,%.4f,%.5f,%.3f,%.4f\n', env_string(), t.method, t.S, t.dS, t.dS_max, t.dS_rms, ...
            sprintf('%.4f,', t.dS_ind(1:5)), t.dS_ind(6), t.Jtot_gain, t.win_gain_chosen, t.win_gain_oracle_feas, t.win_gain_oracle_free, ...
            t.rank_corr, t.n_dec, t.frac_R, t.frac_binding, t.frac_true_tor_worse, t.mean_df, t.mean_dth, t.binding_cost);
end
fclose(f);
end

function r = rankcorr(a, b)
ok = isfinite(a) & isfinite(b); a = a(ok); b = b(ok);
if numel(a) < 3, r = NaN; return; end
ra = rnk(a); rb = rnk(b);
c = corrcoef(ra, rb); r = c(1,2);
end

function r = rnk(x)
[~, i] = sort(x); r = zeros(size(x)); r(i) = 1:numel(x);
u = unique(x);
for k = 1:numel(u), m = x == u(k); if sum(m) > 1, r(m) = mean(r(m)); end, end
end

% =====================================================================
function T = analyze_timing(B, Bn, cfg, C1m, tag)
% 2) 예측 준비 → 적용, 기준시각 → 적용, 남은 예측 구간, 선택·예측 계산시간, 늦은 지령, 지평 부족 복귀
T = struct('method', {}, 'd_s', {}, 'd_cmd', {}, 'd_fc', {}, 'sel_p50', {}, 'sel_p95', {}, 'sel_max', {}, 'fc_p50', {}, 'fc_p95', {}, ...
           'n_pa', {}, 'n_late', {}, 'n_horizon', {}, 'n_noforecast', {}, 'ready2apply', {}, 'origin2apply', {}, 'remain', {}, ...
           'fc_busy', {}, 'fc_deadline', {}, 'S_actual', {}, 'S_nominal0', {}, 'dS_actual', {}, 'dS_nominal0', {});
for m = 1:numel(C1m)
    ss = B.series(strcmp({B.series.method}, C1m{m}));
    A = []; F = []; busy = 0; dl = 0;
    for k = 1:numel(ss)
        tl = ss(k).timeline; tl = tl(tl(:,4) == 1, :); rt = ss(k).rt; Hs = rt.Hn*rt.r; dt = ss(k).rt.update_period_s/rt.nupd;
        A = [A; tl(:,18), tl(:,19), tl(:,20), (tl(:,3) - tl(:,13))*dt, (tl(:,3) - tl(:,12))*dt, (tl(:,12) + Hs - tl(:,3))*dt]; %#ok<AGROW>
        fl = ss(k).forecast_log; F = [F; fl(fl(:,5) == 1, 4)]; %#ok<AGROW>
        busy = busy + sum(fl(:,5) == -1); dl = dl + sum(fl(fl(:,5) == 1, 4) > rt.update_period_s);
        d = [rt.d_s, rt.d_cmd, rt.d_fc];
    end
    t = struct('method', C1m{m}, 'd_s', d(1), 'd_cmd', d(2), 'd_fc', d(3));
    q = sort(A(:,1)); t.sel_p50 = q(ceil(0.5*end)); t.sel_p95 = q(ceil(0.95*end)); t.sel_max = q(end);
    if isempty(F), t.fc_p50 = NaN; t.fc_p95 = NaN; else, q = sort(F); t.fc_p50 = q(ceil(0.5*end)); t.fc_p95 = q(ceil(0.95*end)); end
    t.n_pa = size(A,1); t.n_late = sum(A(:,2) == 1); t.n_horizon = sum(A(:,3) == 4); t.n_noforecast = sum(A(:,3) == 3);
    u = ~isnan(A(:,4));
    t.ready2apply = qstats(A(u,4)); t.origin2apply = qstats(A(u,5)); t.remain = qstats(A(u,6));
    t.fc_busy = busy; t.fc_deadline = dl;
    i1 = strcmp(B.S.methods, C1m{m}); i2 = strcmp(Bn.S.methods, C1m{m});
    t.S_actual = B.S.S(i1); t.S_nominal0 = Bn.S.S(i2); t.dS_actual = B.S.dS(i1); t.dS_nominal0 = Bn.S.dS(i2);
    T(end+1) = t; %#ok<AGROW>
end
f = fopen(fullfile(pc_root(), 'results', ['D_timing' tag '.csv']), 'w');
fprintf(f, 'env,method,d_s,d_cmd,d_fc,select_s_p50,select_s_p95,select_s_max,forecast_s_p50,forecast_s_p95,n_pump_angle_decisions,n_late,n_horizon_fallback,n_no_forecast,ready_to_apply_s_min,ready_to_apply_s_med,ready_to_apply_s_max,origin_to_apply_s_med,remaining_horizon_s_min,remaining_horizon_s_med,forecast_busy_skips,forecast_over_0.2s,S_actual,S_nominal0,dS_actual,dS_nominal0\n');
for k = 1:numel(T)
    t = T(k);
    fprintf(f, '%s,%s,%d,%d,%d,%.4g,%.4g,%.4g,%.4g,%.4g,%d,%d,%d,%d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d,%.4f,%.4f,%.4f,%.4f\n', env_string(), t.method, ...
            t.d_s, t.d_cmd, t.d_fc, t.sel_p50, t.sel_p95, t.sel_max, t.fc_p50, t.fc_p95, t.n_pa, t.n_late, t.n_horizon, t.n_noforecast, ...
            t.ready2apply(1), t.ready2apply(2), t.ready2apply(3), t.origin2apply(2), t.remain(1), t.remain(2), t.fc_busy, t.fc_deadline, ...
            t.S_actual, t.S_nominal0, t.dS_actual, t.dS_nominal0);
end
fclose(f);
end

function q = qstats(v)
if isempty(v), q = [NaN NaN NaN]; return; end
v = sort(v); q = [v(1), v(ceil(0.5*end)), v(end)];
end

% =====================================================================
function T = analyze_torsion(B, cfg, root, tag, rid)
% 3) 한 기록에서 SIMPLE-persistence와 R의 비틀림 제곱 차를 2.6 s 갱신 구간별로 나눠, 기여가 큰 구간과 그때의 지령을 찾는다.
mA = 'SIMPLE-persistence';
pick = @(m) B.series(strcmp({B.series.record_id}, rid) & strcmp({B.series.method}, m));
sU = pick('U'); sR = pick('R'); sA = pick(mA); sP = pick('PREVIEW-C1');
dt = cfg.plant.dt; n = numel(sR.th); t = (0:n-1)'*dt; nF = round(cfg.device.grid_pump_s/dt);
d2 = (sA.th.^2 - sR.th.^2)/n;                                 % 합 = RMS_A² − RMS_R²
tot = sum(d2);
rmsU = sqrt(mean(sU.th.^2)); T = struct('rid', rid, 'rms_R', sqrt(mean(sR.th.^2)), 'rms_A', sqrt(mean(sA.th.^2)), 'rms_U', rmsU);
T.red_R = 100*(1 - T.rms_R/rmsU); T.red_A = 100*(1 - T.rms_A/rmsU); T.dpp = T.red_A - T.red_R;
nb = ceil(n/nF); contrib = zeros(nb, 1);
for b = 1:nb, k = (b-1)*nF+1:min(b*nF, n); contrib(b) = sum(d2(k)); end
sg = sign(tot); if sg == 0, sg = 1; end                   % 악화(+)면 증가 기여가 큰 순, 개선(−)이면 감소 기여가 큰 순
[~, ord] = sort(sg*contrib, 'descend');
top = ord(1:min(5, nb)); T.worse = tot > 0;
tlA = sA.timeline(sA.timeline(:,4) == 1, :); tlR = sR.timeline(sR.timeline(:,4) == 1, :);
rows = {};
for j = 1:numel(top)
    b = top(j); g = (b-1)*nF;                                 % 이 구간 시작 = 갱신 격자 g (그 직전 결정이 적용됨)
    ia = find(tlA(:,3) == g, 1); ir = find(tlR(:,3) == g, 1);
    k = g+1:min(g+nF, n);
    r = {sprintf('%.1f-%.1f', g*dt, min(g+nF, n)*dt), 100*contrib(b)/tot, NaN, NaN, NaN, NaN, NaN, NaN, '', ...
         mean(sA.theta(k))*180/pi, mean(sR.theta(k))*180/pi, sqrt(mean(sA.th(k).^2)), sqrt(mean(sR.th(k).^2))};
    if ~isempty(ia)
        r([3 5]) = {tlA(ia,7)*180/pi, tlA(ia,6)};
        codes = {'', 'chose_R', 'chose_cand', 'no_forecast', 'horizon', 'nan', 'no_feasible', 'deadline', 'deadline_hold'};
        r{9} = codes{tlA(ia,20) + 1};
        cl = sA.clog; c = cl(cl(:,3) == g, :);
        if ~isempty(c) && any(c(:,12) == 1)
            ch = find(c(:,12) == 1, 1); r(6:8) = {c(ch,10)/c(1,10), c(ch,15)/c(1,15), c(ch,13)/c(1,13)};
        end
    end
    if ~isempty(ir), r{4} = tlR(ir,7)*180/pi; else, r{4} = NaN; end   % 같은 격자에서 R 실행의 각도 지령
    rows(end+1,:) = r; %#ok<AGROW>
end
T.top = rows; T.share_top5 = sum([rows{:,2}]);
f = fopen(fullfile(root, 'results', ['D_torsion_intervals_' rid tag '.csv']), 'w');
fprintf(f, 'env,interval_s,share_of_rms2_increase_pct,theta_cmd_deg,R_theta_cmd_deg,f_cmd_hz,pred_thrms_ratio_vs_Rcand,true_thrms_ratio_vs_Rcand,true_J_ratio_vs_Rcand,reason,mean_theta_A_deg,mean_theta_R_deg,th_rms_A_interval,th_rms_R_interval\n');
for j = 1:size(rows,1)
    fprintf(f, '%s,%s,%.2f,%.3f,%.3f,%.5f,%.4f,%.4f,%.4f,%s,%.3f,%.3f,%.4e,%.4e\n', env_string(), rows{j,:});
end
fclose(f);
f = fopen(fullfile(root, 'results', ['D_torsion_series_' rid tag '.csv']), 'w');
fprintf(f, 't_s,th_U,th_R,th_SIMPLEpersist,th_PREVIEW,theta_R_deg,theta_SIMPLEpersist_deg,f_R,f_SIMPLEpersist,cum_d_ms\n');
cd2 = cumsum(d2);
for k = 1:2:n
    fprintf(f, '%.2f,%.5e,%.5e,%.5e,%.5e,%.3f,%.3f,%.5f,%.5f,%.5e\n', t(k), sU.th(k), sR.th(k), sA.th(k), sP.th(k), sR.theta(k)*180/pi, sA.theta(k)*180/pi, sR.f_dev(k), sA.f_dev(k), cd2(k));
end
fclose(f);
try
    h = figure('Visible', 'off', 'Position', [100 100 1100 800]);
    subplot(4,1,1); plot(t, sR.th*1e3, 'k', t, sA.th*1e3, 'r'); ylabel('\theta_{top} [mrad]'); legend('R', mA); title([strrep(rid, '_', ' ') ' — 최상층 비틀림']);
    subplot(4,1,2); y2 = cd2/(T.rms_R^2)*100; plot(t, y2, 'r'); ylabel('누적 \Delta MS / MS_R [%]');
    yl = [min([y2; 0]) max([y2; 0])] + [-1 1]*0.05*max(1e-9, max([y2; 0]) - min([y2; 0])); ylim(yl); hold on;
    for j = 1:numel(top)                                   % 상위 기여 구간 표시
        g = (top(j)-1)*nF*dt; g2 = min((top(j))*nF*dt, t(end));
        patch([g g2 g2 g], [yl(1) yl(1) yl(2) yl(2)], [1 0.85 0.85], 'EdgeColor', 'none', 'FaceAlpha', 0.4);
    end
    plot(t, y2, 'r'); hold off;
    subplot(4,1,3); plot(t, sR.theta*180/pi, 'k', t, sA.theta*180/pi, 'r'); ylabel('회전각 [deg]');
    subplot(4,1,4); plot(t, sR.f_dev, 'k', t, sA.f_dev, 'r'); ylabel('f [Hz]'); xlabel('t [s]');
    for sp = 1:4, subplot(4,1,sp); xlim([0 t(end)]); end
    print(h, fullfile(root, 'results', ['fig_D_torsion_' rid tag '.png']), '-dpng', '-r110'); close(h);
    T.figure = ['results/fig_D_torsion_' rid tag '.png'];
catch err
    T.figure = ['그림 실패: ' err.message];
end
end

% =====================================================================
function T = analyze_ofat(B0, V, tag)
% 4) 기본 + 변형별 SIMPLE-persistence·PREVIEW-C1 결과
T = {};
base = {'기본 (±0.005 Hz, ±15°, H 4 s)', B0};
L = {base{1}, base{2}};
if ~isempty(V), L = [L; V(:, [2 4])]; end
for v = 1:size(L, 1)
    S = L{v,2}.S; rc = L{v,2}.recs;
    for mm = {'SIMPLE-persistence', 'PREVIEW-C1'}
        i = find(strcmp(S.methods, mm{1}));
        rs = reshape([rc(strcmp({rc.method}, mm{1})).reasons], 8, [])';
        n = sum(rs(:)) ; if n == 0, n = 1; end
        T(end+1,:) = {L{v,1}, mm{1}, S.S(i), S.dS(i), S.n_better(i), S.tor_worse_events(i), S.tor_worst_pp(i), ...
                      sum(rs(:,4))/n, sum(rs(:,1))/n, sum(rs(:,7))/n}; %#ok<AGROW>
    end
end
f = fopen(fullfile(pc_root(), 'results', ['D_ofat' tag '.csv']), 'w');
fprintf(f, 'env,variant,method,S,dS_vs_R,n_better_events,torsion_worse_events,torsion_worst_pp,frac_horizon_fallback,frac_choose_R,frac_deadline\n');
for k = 1:size(T,1), fprintf(f, '%s,%s,%s,%.4f,%.4f,%d,%d,%.4f,%.3f,%.3f,%.3f\n', env_string(), T{k,:}); end
fclose(f);
end

% =====================================================================
function C = analyze_cost(B0, V, root)
% 5) 비용: C1 폐루프 1회 시간(진단 기록 없는 실행 기준)과 학습 비용 추정
src = B0; if ~isempty(V), src = V{1,4}; end
rc = src.recs; w = [rc(strcmp({rc.method}, 'SIMPLE-persistence')).wall_s];
C = struct('c1_run_s_mean', mean(w), 'c1_run_s_max', max(w));
C.n_c1_runs_F = 6*3 + 3*3 + 4*2*3 + 2*3;     % F_pilot C1형 6방식, 시드 3, 추가지연 4×2, 공통지연 2 (각 개발 기록 3개)
C.F_closed_loop_s = C.n_c1_runs_F*C.c1_run_s_mean;
try
    C.train = estimate_training_cost();
catch err
    C.train = struct('available', false, 'note', err.message);
end
end

% =====================================================================
function write_report(R, cfg, root, tag, pv)
f = fopen(fullfile(root, 'report', ['D_diagnosis' tag '.md']), 'w');
p = @(varargin) fprintf(f, varargin{:});
p('# D 단계 개발 진단 결과\n\n');
p('- 실행: %s, 브랜치 `%s`, 커밋 `%s`, 작업트리 변경 %s, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.branch, pv.commit, mat2str(pv.dirty), pv.digest, pv.config_hash);
p('- 사건: %s (개발 자료, **시험 아님**). timing_mode=%s, 계산 지연 실측값 %s\n', strjoin(cfg.data.dev_events_control', ', '), cfg.latency.timing_mode, mat2str(cfg.latency.compute_measured));
p('- 사건 3개라 구간 추정은 의미가 작습니다. 아래는 원인 진단용이며 성능 주장에 쓰지 않습니다.\n\n');
p('## 1. SIMPLE-persistence 대 PREVIEW-C1 분해 (R 대비)\n\n');
p('예측 구간 값은 각 결정에서 같은 후보를 **실제 미래 입력**으로 다시 모의한 J(진단 전용)의 R 후보 대비 감소율 평균입니다. 방식마다 지나온 상태가 달라 결정 집합이 다릅니다.\n\n');
p('| 방식 | 6지표 ΔS | 최대 3지표 | RMS 3지표 | 전체 기록 J 감소 | 예측구간 J 감소: 선택안 | 참 최선(실제 비틀림 만족) | 참 최선(제한 없음) | 순위 상관 J예측·J참 | R 선택 | 비틀림 제한이 최선안을 막음 | 선택안이 실제로는 R후보보다 비틀림 RMS 큼 | 선택 θ와 R θ 차 평균 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n');
for k = 1:numel(R.T1)
    t = R.T1(k);
    if ~any(strcmp(t.method, {'SIMPLE-zero', 'SIMPLE-persistence', 'PREVIEW-C1'}))
        p('| %s | %+.2f | %+.2f | %+.2f | %+.2f %% | — | — | — | — | — | — | — | — |\n', t.method, t.dS, t.dS_max, t.dS_rms, t.Jtot_gain); continue;
    end
    p('| %s | %+.2f | %+.2f | %+.2f | %+.2f %% | %+.2f %% | %+.2f %% | %+.2f %% | %.2f | %.0f %% | %.0f %% | %.0f %% | %.1f° |\n', t.method, t.dS, t.dS_max, t.dS_rms, t.Jtot_gain, ...
      t.win_gain_chosen, t.win_gain_oracle_feas, t.win_gain_oracle_free, t.rank_corr, 100*t.frac_R, 100*t.frac_binding, 100*t.frac_true_tor_worse, t.mean_dth);
end
p('\n지표별 ΔS(%%p, ux최대·ux RMS·uy최대·uy RMS·θ최대·θ RMS):\n\n');
for k = 1:numel(R.T1), p('- %s: %s\n', R.T1(k).method, sprintf('%+.2f ', R.T1(k).dS_ind)); end
p('\n### 1-2. 같은 분해, 계산 지연 0 (nominal) — SIMPLE-persistence가 PREVIEW보다 높았던 조건\n\n');
p('| 방식 | 6지표 ΔS | 최대 3지표 | RMS 3지표 | 전체 기록 J 감소 | 예측구간 J 감소: 선택안 | 참 최선(실제 비틀림 만족) | 참 최선(제한 없음) | 순위 상관 | R 선택 | 제한이 최선안을 막음 | 선택안 실제 비틀림 RMS > R후보 | 지표별 ΔS (ux최대 ux RMS uy최대 uy RMS θ최대 θ RMS) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n');
for k = 1:numel(R.T1n)
    t = R.T1n(k); if ~any(strcmp(t.method, {'SIMPLE-zero', 'SIMPLE-persistence', 'PREVIEW-C1'})), continue; end
    p('| %s | %+.2f | %+.2f | %+.2f | %+.2f %% | %+.2f %% | %+.2f %% | %+.2f %% | %.2f | %.0f %% | %.0f %% | %.0f %% | %s|\n', t.method, t.dS, t.dS_max, t.dS_rms, t.Jtot_gain, ...
      t.win_gain_chosen, t.win_gain_oracle_feas, t.win_gain_oracle_free, t.rank_corr, 100*t.frac_R, 100*t.frac_binding, 100*t.frac_true_tor_worse, sprintf('%+.2f ', t.dS_ind));
end
p('\n읽는 법: 예측 구간 J(제어기가 최소화하는 양)에서 PREVIEW가 앞서는데 전체 6지표에서 뒤지면, 원인은 예측 정확도가 아니라 목적함수(4 s 구간 제곱평균, 최대값 미포함)와 전체 지표의 불일치입니다. 비틀림 제한이 걸린 비율이 높으면 제한이 후보를 많이 잘라낸 것입니다.\n\n');
p('## 2. 시간: 예측 준비 → 지령 적용, 남은 예측 구간\n\n| 방식 | d_s / d_cmd / d_fc (스텝) | 선택 계산 p50 / p95 (s) | 예측 계산 p50 / p95 (s) | 펌프·각도 결정 | 늦음 | 지평 부족 | 예측 준비→적용 최소/중앙/최대 (s) | 기준시각→적용 중앙 (s) | 남은 예측 구간 최소/중앙 (s) | S 실측지연 / 지연0 |\n|---|---|---|---|---|---|---|---|---|---|---|\n');
for k = 1:numel(R.T2)
    t = R.T2(k);
    p('| %s | %d / %d / %d | %.3f / %.3f | %.4f / %.4f | %d | %d | %d | %.2f / %.2f / %.2f | %.2f | %.2f / %.2f | %.2f / %.2f |\n', t.method, t.d_s, t.d_cmd, t.d_fc, ...
      t.sel_p50, t.sel_p95, t.fc_p50, t.fc_p95, t.n_pa, t.n_late, t.n_horizon, t.ready2apply, t.origin2apply(2), t.remain(1), t.remain(2), t.S_actual, t.S_nominal0);
end
p('\n## 3. 비틀림 RMS 변화 구간 (SIMPLE-persistence 대 R, 기록별)\n\n');
for q = 1:numel(R.T3)
    T3 = R.T3{q};
    p('### %s\n\n- 비틀림 RMS 저감률: R %.2f %%, SIMPLE-persistence %.2f %% (차 %+.2f %%p). 그림: `%s`\n', T3.rid, T3.red_R, T3.red_A, T3.dpp, T3.figure);
    if T3.worse
        p('- **악화**: 2.6 s 갱신 구간별 기여 상위 5개가 RMS² 증가분의 %.0f %%\n\n', T3.share_top5);
    else
        p('- 악화 없음: 아래는 감소 기여가 큰 구간 (상위 5개 = 감소분의 %.0f %%)\n\n', T3.share_top5);
    end
    p('| 구간 (s) | 기여 | 지령 θ (deg) | R 지령 θ | 지령 f (Hz) | 예측 θRMS/R후보 | 실제 θRMS/R후보 | 실제 J/R후보 | 사유 | 평균 θ 실제 (A / R) |\n|---|---|---|---|---|---|---|---|---|---|\n');
    for j = 1:size(T3.top, 1)
        r = T3.top(j,:);
        p('| %s | %.0f %% | %.1f | %.1f | %.4f | %.3f | %.3f | %.3f | %s | %.1f / %.1f |\n', r{1}, r{2}, r{3}, r{4}, r{5}, r{6}, r{7}, r{8}, r{9}, r{10}, r{11});
    end
    p('\n');
end
p('\n예측 비율이 1 이하인데 실제 비율이 1보다 크면, 비틀림 제한은 예측상 만족했지만 실제 입력에서는 깨진 경우입니다(제한이 예측에만 걸림).\n\n');
p('## 4. 한 요소씩 진단 (개발 자료, 설정 파일은 바꾸지 않음)\n\n| 변형 | 방식 | S | ΔS | 나아진 사건 | 비틀림 악화 사건 | 비틀림 최악 | 지평 부족 비율 | R 선택 비율 | 늦음 비율 |\n|---|---|---|---|---|---|---|---|---|---|\n');
for k = 1:size(R.T4, 1)
    p('| %s | %s | %.2f | %+.2f | %d/3 | %d | %+.2f | %.2f | %.2f | %.2f |\n', R.T4{k,:});
end
p('\n## 5. AI 학습으로 넘어갈 근거와 예상 비용\n\n');
pr = R.T1(strcmp({R.T1.method}, 'PREVIEW-C1')); sp = R.T1(strncmp({R.T1.method}, 'SIMPLE', 6));
best_simple = max([sp.dS]); best_prev = pr.dS;
if ~isempty(R.T4), ii = strcmp(R.T4(:,2), 'PREVIEW-C1') & ~strncmp(R.T4(:,1), '[진단 전용]', 7); best_prev_any = max([R.T4{ii,4}]); else, best_prev_any = best_prev; end   % 진단 전용 변형(비틀림 제한 끔)은 제외
p('사전 등록 8절 판단 기준(목표 수치를 맞추려고 바꾸지 않음):\n\n');
if isempty(out_tag()), p('- G1 관문 A·B·SL·C: 통과 (D는 관문 확인 뒤에만 시작)\n'); else, p('- G1: **판단 불가** — Octave 예비 실행이라 관문을 확인하지 않음\n'); end
p('- G2 제어 여지: PREVIEW-C1 기본 설정 ΔS = %+.2f %%p, 한 요소 변형 중 최대 %+.2f %%p (기준 +2 %%p) → %s\n', best_prev, best_prev_any, ...
  yesno(best_prev_any >= 2, '충족', '미충족: 예측이 완벽해도 현 후보 구조로는 목표에 닿기 어려움 → 제어기 구조 수정이 AI 학습보다 먼저'));
[~, ib] = max([sp.dS]);
p('- G3 예측 개선 여지: PREVIEW − 최선 SIMPLE(%s) = %+.4f − %+.4f = %+.4f %%p (기준 +0.5 %%p) → %s\n', sp(ib).method, best_prev, best_simple, best_prev - best_simple, yesno(best_prev - best_simple >= 0.5, '충족', '미충족: 더 좋은 예측(AI)이 줄 수 있는 이득이 작음'));
for q = 1:numel(sp), p('  - 참고: PREVIEW − %s = %+.4f %%p\n', sp(q).method, best_prev - sp(q).dS); end
tm = R.T2(strcmp({R.T2.method}, 'PREVIEW-C1'));
fr = (tm.n_late + tm.n_horizon)/max(tm.n_pa, 1);
if strcmp(cfg.latency.timing_mode, 'actual') && cfg.latency.compute_measured
    p('- G4 시간: PREVIEW-C1 펌프·각도 결정 중 늦음·지평 부족 비율 %.0f %% (기준 ≤ 20 %%) → %s\n\n', 100*fr, yesno(fr <= 0.2, '충족', '미충족: 계산시간 단축이 먼저'));
else
    p('- G4 시간: **판단 불가** — 실측 계산시간·actual 시간축이 아님\n\n');
end
p('예상 비용:\n\n- C1 폐루프 1회(SIMPLE-persistence, 진단 기록 없음) 평균 %.1f s, 최대 %.1f s\n', R.cost.c1_run_s_mean, R.cost.c1_run_s_max);
p('- F 단계 C1형 폐루프 %d회 → 약 %.0f 분 (예측기 계산시간 추가 전)\n', R.cost.n_c1_runs_F, R.cost.F_closed_loop_s/60);
if isfield(R.cost.train, 'available') && R.cost.train.available
    tr = R.cost.train;
    p('- LSTM 반복 1회(batch 32) %.1f ms, 단건 추론 %.2f ms (학습 전 같은 구조, 시간 측정 전용)\n', 1e3*tr.s_per_iter, 1e3*tr.predict_s);
    for k = 1:size(tr.rows,1), p('- %s: 학습 창 %d, epoch당 약 %.0f s, 상한(최대 epoch × 시드) 약 %.1f 시간\n', tr.rows{k,1}, tr.rows{k,2}, tr.rows{k,6}, tr.rows{k,7}/3600); end
else
    p('- 학습 비용: %s\n', R.cost.train.note);
end
p('\n이 진단으로 개발 설정을 바꾸면 `config/CHANGELOG.md`에 이유·이전·이후 결과를 적고, A~C 관문과 D를 다시 돌린 뒤 F 전에 `config/frozen/`으로 다시 고정합니다.\n');
fclose(f);
end

function s = yesno(c, a, b)
if c, s = a; else, s = b; end
end
