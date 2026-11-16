function R = diagnose_RP(opt)
% DIAGNOSE_RP  재현성 진단 (2026-10-29 요청). 현행 ±15°만, 사전 기준 G2·G3·비틀림 허용 0 %p 그대로.
%  ±45°·지평·목적함수 변경과 AI 학습은 넣지 않는다. 5회 반복은 계산시간 민감성 평가이며 지진 표본을 늘리는 것이 아니다.
%  1) 완전 고정 2회 (fixed51_a, fixed51_b)
%     timing_mode=nominal: 센서 0, 통신·추가 0, 예측 준비 d_fc=1, R d_cmd=1, C1 d_cmd=51 (D_main과 같은 값)
%     실측 계산시간은 기록만 하고 제어에 쓰지 않는다(nominal에서는 늦음 판정·준비 시각이 계산시간과 무관).
%     코드 digest·입력 파일 해시·난수 상태·스레드 수·후보 순서(R → 유지 → 나머지)·동점 규칙(앞 순서)을 기록·고정한다.
%     두 실행의 지령·응답이 한 비트라도 다르면 원인 기록을 남기고 멈춘다(2·3 진행 안 함).
%  2) d_cmd 50 대 51 (fixed50 대 fixed51_a): 나머지 조건 동일. 결정·마지막 관측·예측 기준·준비·적용 시각을 함께 기록.
%  3) 실측 지연 5회 (actual_1..5): 시작 시 config/latency_measured.json을 한 번 읽어 고정(재측정 안 함).
%     R, SIMPLE-zero, SIMPLE-persistence, PREVIEW-C1. 실행 순서·시각·환경을 기록. 모든 실행을 보존하고 대표값을 고르지 않는다.
%  4) 실행별 G2·G3, 사건별 6지표 저감률, 비틀림 최대·RMS 여유(R 대비), 위반 기록·사건 수, 지령 지연·늦음 비율
%     G3 = PREVIEW-C1 − 최선 SIMPLE(이 실행의 SIMPLE-zero·SIMPLE-persistence 중 큰 값; SIMPLE-var는 모델 없음으로 제외, D와 같음)
%  결과: report/RP_summary.md, results/RP_*.csv, results/benchmarks_RP_*.mat
%  opt.allow_prelim (Octave 예비), opt.max_seconds (기능 점검용 자르기), opt.n_actual (기본 5), opt.reuse
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'allow_prelim'), opt.allow_prelim = false; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
if ~isfield(opt, 'n_actual'), opt.n_actual = 5; end
if ~isfield(opt, 'reuse'), opt.reuse = false; end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct && ~opt.allow_prelim, error('diagnose_RP: MATLAB에서 실행'); end
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg0 = pc_config(); tag = out_tag(); sfx = '';
if isfinite(opt.max_seconds), sfx = '_trunc'; tag = [tag sfx]; end
if ~cfg0.latency.compute_measured && ~isoct, error('diagnose_RP: config/latency_measured.json 없음'); end
if any(abs(cfg0.controller.C1.dtheta_deg(:)' - [-15 0 15]) > 0), error('diagnose_RP: 현행 ±15° 설정이 아님'); end
dev = cfg0.data.dev_events_control;
M4 = {'R', 'SIMPLE-zero', 'SIMPLE-persistence', 'PREVIEW-C1'};
inp = input_hashes(cfg0, dev);
% ---------------- 1) 완전 고정 2회 ----------------
cf51 = fixed_cfg(cfg0, 0.51); cf50 = fixed_cfg(cfg0, 0.50);
E = {};
[F51a, E{end+1}] = run_one(opt, root, ['RP_fixed51_a' sfx], M4, dev, cf51, pv, inp, 'fixed51_a');
[F51b, E{end+1}] = run_one(opt, root, ['RP_fixed51_b' sfx], M4, dev, cf51, pv, inp, 'fixed51_b');
Cmp = compare_runs(F51a, F51b);
write_compare(root, tag, Cmp);
R = struct('provenance', pv, 'inputs', inp, 'fixed_identical', all([Cmp.identical]), 'compare', Cmp);
if ~R.fixed_identical
    R.env = E;
    save(fullfile(root, 'results', ['RP' tag '.mat']), 'R', '-v7');
    write_report(root, tag, R, cfg0, M4);
    fprintf(2, 'diagnose_RP: 완전 고정 2회의 지령·응답이 다름 → 원인 확인 먼저 (report/RP_summary%s.md). 2·3 단계는 진행하지 않음\n', tag);
    return;
end
fprintf('완전 고정 2회: 지령·응답 비트 단위 동일\n');
% ---------------- 2) d_cmd 50 대 51 ----------------
[F50, E{end+1}] = run_one(opt, root, ['RP_fixed50' sfx], M4, dev, cf50, pv, inp, 'fixed50');
Dc = compare_dcmd(F50, F51a, M4, root, tag);
% ---------------- 3) 실측 지연 5회 ----------------
ca = cfg0; ca.latency.timing_mode = 'actual';
if isoct, ca.latency.timing_mode = 'nominal'; end                % Octave 계산시간은 노트북을 대표하지 않음 (기능 점검만)
frozen = ca.latency;
fid = fopen(fullfile(root, 'results', ['RP_latency_frozen' tag '.json']), 'w'); fprintf(fid, '%s', jsonencode(frozen)); fclose(fid);
A = cell(1, opt.n_actual);
for r = 1:opt.n_actual
    [A{r}, E{end+1}] = run_one(opt, root, sprintf('RP_actual_%d%s', r, sfx), M4, dev, ca, pv, inp, sprintf('actual_%d', r)); %#ok<AGROW>
end
% ---------------- 4) 실행별 지표 ----------------
runs = [{F51a, F51b, F50}, A];
names = [{'fixed51_a', 'fixed51_b', 'fixed50'}, arrayfun(@(r) sprintf('actual_%d', r), 1:opt.n_actual, 'UniformOutput', false)];
T = cell(1, numel(runs));
for r = 1:numel(runs), T{r} = run_metrics(runs{r}, names{r}, M4); end
write_runs_csv(root, tag, T, M4);
R.dcmd = Dc; R.runs = T; R.env = E; R.frozen_latency = frozen;
save(fullfile(root, 'results', ['RP' tag '.mat']), 'R', '-v7');
write_report(root, tag, R, cfg0, M4);
fprintf('재현성 진단 완료 → report/RP_summary%s.md\n', tag);
end

% =====================================================================
function c = fixed_cfg(c, sel)
% 완전 고정: 계산시간 대신 고정 예산. nominal에서는 지령 도착·늦음·예측 준비가 실측 계산시간과 무관하다.
c.latency.timing_mode = 'nominal';
c.latency.sensor_s = 0; c.latency.comm_s = 0; c.latency.extra_info_s = 0;
c.latency.inject_select_s = 0; c.latency.inject_forecast_s = 0;
cs = c.latency.compute_s;
cs.R = 0.01; cs.select_C1 = sel;                                  % R d_cmd 1, C1 d_cmd = sel/dt
cs.forecast_zero = 0.01; cs.forecast_persistence = 0.01; cs.forecast_preview = 0.01;   % d_fc 1
c.latency.compute_s = cs;
end

function [B, env] = run_one(opt, root, tg, methods, dev, c, pv0, inp, label)
pv = run_provenance();
if ~strcmp(pv.digest, pv0.digest), error('diagnose_RP: 실행 중 코드 digest가 바뀜 (%s → %s)', pv0.digest, pv.digest); end
if ~isequal(input_hashes(c, dev), inp), error('diagnose_RP: 입력 기록 파일이 바뀜'); end
rng(8401, 'twister');                                             % 난수는 제어에 쓰이지 않지만 상태를 고정·기록
env = run_env(label, tg);
f = fullfile(root, 'results', ['benchmarks_' tg out_tag() '.mat']);
if opt.reuse && exist(f, 'file'), L = load(f); B = L.out; fprintf('재사용: %s\n', f);
else, B = run_benchmarks(tg, methods, dev, struct('cfg', c, 'keep_series', true, 'max_seconds', opt.max_seconds)); end
env.t_end = datestr(now, 'yyyy-mm-dd HH:MM:SS');
env.wall_total_s = sum([B.recs.wall_s]);
end

function e = run_env(label, tg)
e = struct('label', label, 'tag', tg, 't_start', datestr(now, 'yyyy-mm-dd HH:MM:SS'), 'env', env_string(), ...
           'threads', NaN, 'cores', NaN, 'computer', computer(), 'rng', 'twister 8401');
try, e.threads = maxNumCompThreads; catch, end %#ok<NOCOM>
try, e.cores = feature('numcores'); catch, try, e.cores = nproc(); catch, end, end %#ok<NOCOM>
end

function H = input_hashes(cfg, dev)
man = read_manifest(fullfile(cfg.root, cfg.paths.record_manifest));
rids = man.record_id(ismember(man.event_id, dev));
H = struct('record_id', {}, 'sha256', {});
for k = 1:numel(rids)
    f = fullfile(cfg.root, cfg.paths.records_dir, sprintf('dt%g', cfg.plant.dt), [rids{k} '.csv']);
    H(end+1) = struct('record_id', rids{k}, 'sha256', file_sha256(f)); %#ok<AGROW>
end
end

function h = file_sha256(f)
if exist('OCTAVE_VERSION', 'builtin') > 0, h = hash('sha256', fileread(f)); return; end
fid = fopen(f, 'r'); b = fread(fid, inf, '*uint8'); fclose(fid);
md = java.security.MessageDigest.getInstance('SHA-256'); md.update(b);
h = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'))', 1, []));
end

% =====================================================================
function C = compare_runs(A, B)
% 지령(시간축)·응답·장치·예측 기록을 비트 단위로 비교. 실측 계산시간 열(18, 21)과 그로부터 만든 도착 시각 열(22, 23), 예측 계산시간(4)은 제외.
C = struct('method', {}, 'record_id', {}, 'identical', {}, 'field', {}, 'first_step', {}, 'max_abs', {});
tcols = setdiff(1:23, [18 21 22 23]); fcols = [1 2 3 5];
for k = 1:numel(A.series)
    a = A.series(k);
    b = B.series(strcmp({B.series.method}, a.method) & strcmp({B.series.record_id}, a.record_id));
    c = struct('method', a.method, 'record_id', a.record_id, 'identical', true, 'field', '', 'first_step', NaN, 'max_abs', 0);
    if numel(b) ~= 1, c.identical = false; c.field = 'missing'; C(end+1) = c; continue; end %#ok<AGROW>
    flds = {'timeline', 'ux', 'uy', 'th', 'f_dev', 'theta', 'kappa', 'forecast_log'};
    for q = 1:numel(flds)
        x = a.(flds{q}); y = b.(flds{q});
        if strcmp(flds{q}, 'timeline'), x = x(:, tcols); y = y(:, tcols); end
        if strcmp(flds{q}, 'forecast_log') && ~isempty(x), x = x(:, fcols); y = y(:, fcols); end
        if ~isequal(size(x), size(y)), c.identical = false; c.field = [flds{q} ' (크기)']; break; end
        d = abs(x - y); d(isnan(x) & isnan(y)) = 0; d(xor(isnan(x), isnan(y))) = inf;
        if any(d(:) > 0)
            c.identical = false; c.field = flds{q}; c.max_abs = max(d(:));
            [rr, ~] = find(d > 0, 1);
            if any(strcmp(flds{q}, {'timeline', 'forecast_log'})), c.first_step = x(rr, 1); else, c.first_step = rr - 1; end
            break;
        end
    end
    C(end+1) = c; %#ok<AGROW>
end
end

function D = compare_dcmd(B50, B51, M4, root, tag)
% 같은 적용 격자 g에서 d_cmd 50과 51의 결정 시각·마지막 관측·예측 기준·준비·지령을 비교한다.
D = struct('method', {}, 'record_id', {}, 'n', {}, 'n_cmd_diff', {}, 'first_diff_t', {}, 'dS_event', {}, 'dth', {});
dt = B51.cfg.plant.dt;
f = fopen(fullfile(root, 'results', ['RP_dcmd_timeline' tag '.csv']), 'w');
fprintf(f, 'method,record_id,apply_time,decision_t_50,decision_t_51,last_obs_t_50,last_obs_t_51,origin_t_50,origin_t_51,ready_t_50,ready_t_51,f_50,f_51,theta_deg_50,theta_deg_51,reason_50,reason_51,same_command\n');
iR50 = find(strcmp(B50.S.methods, 'R')); iR51 = find(strcmp(B51.S.methods, 'R'));
for m = 1:numel(M4)
    for k = 1:numel(B51.series)
        s1 = B51.series(k); if ~strcmp(s1.method, M4{m}), continue; end
        s0 = B50.series(strcmp({B50.series.method}, M4{m}) & strcmp({B50.series.record_id}, s1.record_id));
        t1 = s1.timeline(s1.timeline(:,4) == 1, :); t0 = s0.timeline(s0.timeline(:,4) == 1, :);
        [g, i0, i1] = intersect(t0(:,3), t1(:,3));
        same = abs(t0(i0,6) - t1(i1,6)) < 1e-12 & abs(t0(i0,7) - t1(i1,7)) < 1e-12;
        for j = 1:numel(g)
            a = t0(i0(j), :); b = t1(i1(j), :);
            fprintf(f, '%s,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.6g,%.6g,%.3f,%.3f,%d,%d,%d\n', M4{m}, s1.record_id, g(j)*dt, ...
                    a(1)*dt, b(1)*dt, a(2)*dt, b(2)*dt, a(12)*dt, b(12)*dt, a(13)*dt, b(13)*dt, a(6), b(6), a(7)*180/pi, b(7)*180/pi, a(20), b(20), same(j));
        end
        fd = find(~same, 1); if isempty(fd), ft = NaN; else, ft = g(fd)*dt; end
        e = find(strcmp(B51.S.events, record_event(B51, s1.record_id)));
        m0 = strcmp(B50.S.methods, M4{m}); m1 = strcmp(B51.S.methods, M4{m});
        d50 = B50.S.score_event(e, m0) - B50.S.score_event(e, iR50); d51 = B51.S.score_event(e, m1) - B51.S.score_event(e, iR51);
        r50 = B50.S.red_event(e, 5:6, m0) - B50.S.red_event(e, 5:6, iR50); r51 = B51.S.red_event(e, 5:6, m1) - B51.S.red_event(e, 5:6, iR51);
        D(end+1) = struct('method', M4{m}, 'record_id', s1.record_id, 'n', numel(g), 'n_cmd_diff', sum(~same), 'first_diff_t', ft, ...
                          'dS_event', [d50, d51], 'dth', [r50, r51]); %#ok<AGROW>
    end
end
fclose(f);
end

function ev = record_event(B, rid)
r = B.recs(strcmp({B.recs.record_id}, rid)); ev = r(1).event_id;
end

% =====================================================================
function T = run_metrics(B, name, M4)
S = B.S; iR = find(strcmp(S.methods, 'R'));
T = struct('run', name, 'mode', B.cfg.latency.timing_mode, 'events', {S.events(:)'}, 'm', struct([]));
mm = struct('method', {}, 'S', {}, 'dS', {}, 'dS_event', {}, 'red', {}, 'thmax_margin', {}, 'thrms_margin', {}, ...
            'viol_events', {}, 'viol_records', {}, 'd_cmd', {}, 'late', {}, 'deadline', {}, 'deadline_hold', {}, 'sel_p50', {}, 'sel_p95', {}, 'would_late', {});
for q = 1:numel(M4)
    m = find(strcmp(S.methods, M4{q}));
    x = struct('method', M4{q}, 'S', S.S(m), 'dS', S.dS(m), 'dS_event', (S.score_event(:, m) - S.score_event(:, iR))', ...
               'red', S.red_event(:, :, m));
    x.thmax_margin = (S.red_event(:, 5, m) - S.red_event(:, 5, iR))';
    x.thrms_margin = (S.red_event(:, 6, m) - S.red_event(:, 6, iR))';
    x.viol_events = sum(x.thmax_margin < 0 | x.thrms_margin < 0);
    rr = B.recs(strcmp({B.recs.method}, M4{q})); rR = B.recs(strcmp({B.recs.method}, 'R')); nv = 0;
    for k = 1:numel(rr)
        u = B.recs(strcmp({B.recs.method}, 'U') & strcmp({B.recs.record_id}, rr(k).record_id)).metrics;
        b = rR(strcmp({rR.record_id}, rr(k).record_id)).metrics;
        a = rr(k).metrics;
        nv = nv + any((1 - a(5:6)./u(5:6)) < (1 - b(5:6)./u(5:6)));
    end
    x.viol_records = nv;
    ss = B.series(strcmp({B.series.method}, M4{q})); L = [];
    for k = 1:numel(ss)
        tl = ss(k).timeline; tl = tl(tl(:,4) == 1, :);
        L = [L; tl(:,19), tl(:,20) == 7, tl(:,20) == 8, tl(:,18), tl(:,22) > tl(:,3) + 1e-9]; %#ok<AGROW>
        x.d_cmd = ss(k).rt.d_cmd;
    end
    x.late = mean(L(:,1)); x.deadline = sum(L(:,2)); x.deadline_hold = sum(L(:,3));
    w = sort(L(~isnan(L(:,4)), 4)); x.sel_p50 = w(max(1, ceil(0.5*end))); x.sel_p95 = w(max(1, ceil(0.95*end)));
    x.would_late = mean(L(:,5));                                  % 실측 계산시간으로 보면 늦었을 비율 (nominal에서는 기록만)
    mm(end+1) = x; %#ok<AGROW>
end
T.m = mm;
iP = strcmp({mm.method}, 'PREVIEW-C1'); iS = strncmp({mm.method}, 'SIMPLE', 6);
[bs, ib] = max([mm(iS).dS]); sn = {mm(iS).method};
T.G2 = mm(iP).dS; T.G2_pass = T.G2 >= 2;
T.best_simple = sn{ib}; T.G3 = mm(iP).dS - bs; T.G3_pass = T.G3 >= 0.5;
end

% =====================================================================
function write_compare(root, tag, C)
f = fopen(fullfile(root, 'results', ['RP_fixed_compare' tag '.csv']), 'w');
fprintf(f, 'method,record_id,identical,first_field,first_step,max_abs_diff\n');
for k = 1:numel(C), fprintf(f, '%s,%s,%d,%s,%g,%.3e\n', C(k).method, C(k).record_id, C(k).identical, C(k).field, C(k).first_step, C(k).max_abs); end
fclose(f);
end

function write_runs_csv(root, tag, T, M4)
f = fopen(fullfile(root, 'results', ['RP_runs' tag '.csv']), 'w');
fprintf(f, 'run,timing_mode,method,S,dS_vs_R,dS_events,thmax_margin_events,thrms_margin_events,violation_events,violation_records,d_cmd,late_frac,deadline,deadline_hold,select_s_p50,select_s_p95,would_be_late_frac,G2_PREVIEW_dS,G2_pass,best_SIMPLE,G3,G3_pass\n');
g = fopen(fullfile(root, 'results', ['RP_event_metrics' tag '.csv']), 'w');
fprintf(g, 'run,method,event,red_uxmax,red_uxrms,red_uymax,red_uyrms,red_thmax,red_thrms,dS_vs_R,thmax_margin,thrms_margin\n');
for r = 1:numel(T)
    t = T{r};
    for q = 1:numel(t.m)
        x = t.m(q);
        fprintf(f, '%s,%s,%s,%.4f,%.4f,%s,%s,%s,%d,%d,%d,%.4f,%d,%d,%.4f,%.4f,%.4f,%.4f,%d,%s,%.4f,%d\n', t.run, t.mode, x.method, x.S, x.dS, ...
                vstr(x.dS_event), vstr(x.thmax_margin), vstr(x.thrms_margin), x.viol_events, x.viol_records, x.d_cmd, x.late, x.deadline, x.deadline_hold, ...
                x.sel_p50, x.sel_p95, x.would_late, t.G2, t.G2_pass, t.best_simple, t.G3, t.G3_pass);
        for e = 1:numel(t.events)
            fprintf(g, '%s,%s,%s,%s,%.4f,%.4f,%.4f\n', t.run, x.method, t.events{e}, strjoin(arrayfun(@(v) sprintf('%.4f', v), x.red(e,:), 'UniformOutput', false), ','), ...
                    x.dS_event(e), x.thmax_margin(e), x.thrms_margin(e));
        end
    end
end
fclose(f); fclose(g);
end

function s = vstr(v)
s = strjoin(arrayfun(@(x) sprintf('%+.2f', x), v, 'UniformOutput', false), ' ');
end

% =====================================================================
function write_report(root, tag, R, cfg, M4)
f = fopen(fullfile(root, 'report', ['RP_summary' tag '.md']), 'w');
p = @(varargin) fprintf(f, varargin{:});
pv = R.provenance;
p('# 재현성 진단 (현행 ±15°)\n\n');
p('- 실행: %s, 브랜치 `%s`, 커밋 `%s`, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.branch, pv.commit, pv.digest, pv.config_hash);
p('- 개발 사건 %s. **시험 결과 아님.** G2(≥ +2 %%p)·G3(≥ +0.5 %%p)·비틀림 허용 0 %%p는 사전 기준 그대로입니다.\n', strjoin(cfg.data.dev_events_control(:)', ', '));
p('- ±45°·예측 지평·목적함수 변경·AI 학습은 이번 진단에 넣지 않았습니다. 5회 반복은 계산시간 민감성 평가이며 지진 표본 수가 늘어난 것이 아닙니다.\n');
p('- 입력 기록 SHA-256: %s\n', strjoin(arrayfun(@(h) sprintf('%s `%s`', h.record_id, h.sha256(1:16)), R.inputs, 'UniformOutput', false), ', '));
p('- 고정 항목: 코드 digest(실행마다 확인), 입력 해시(실행마다 확인), 난수 twister 8401, 후보 순서 R → 현재 유지 → 나머지(selector_step), 동점이면 앞 순서\n\n');
p('## 1. 완전 고정 2회 (nominal, 센서 0·통신 0·예측 준비 1스텝·R 1스텝·C1 d_cmd 51)\n\n');
p('실측 계산시간은 기록만 하고 제어에 쓰지 않았습니다. 비교 대상: 지령 시간축(계산시간 열 제외), 응답 ux·uy·θ, 장치 f·회전각·κ, 예측 기록.\n\n');
C = R.compare;
p('| 방식 | 기록 | 동일 | 처음 다른 항목 | 처음 다른 스텝 | 최대 차 |\n|---|---|---|---|---|---|\n');
for k = 1:numel(C), p('| %s | %s | %s | %s | %g | %.2e |\n', C(k).method, C(k).record_id, yn(C(k).identical), C(k).field, C(k).first_step, C(k).max_abs); end
if ~R.fixed_identical
    p('\n**완전 고정 2회가 같지 않습니다.** 성능 비교(2·3단계)는 진행하지 않았습니다. 위 표의 처음 다른 항목·스텝부터 원인을 확인합니다.\n');
    write_env(p, R.env); fclose(f); return;
end
p('\n→ 두 실행의 지령·응답이 비트 단위로 같습니다. 고정 조건의 시뮬레이션은 결정적입니다.\n\n');
p('## 2. d_cmd 50 대 51 (그 밖의 조건 동일)\n\n');
p('결정 시각·마지막 관측·예측 기준·준비 시각은 `results/RP_dcmd_timeline%s.csv`에 결정마다 있습니다.\n\n', tag);
p('| 방식 | 기록 | 결정 수 | 지령이 다른 결정 | 처음 달라진 적용 시각 | ΔS(50) | ΔS(51) | θ최대 여유 50 / 51 | θRMS 여유 50 / 51 |\n|---|---|---|---|---|---|---|---|---|\n');
for k = 1:numel(R.dcmd)
    d = R.dcmd(k);
    p('| %s | %s | %d | %d | %s | %+.2f | %+.2f | %+.2f / %+.2f | %+.2f / %+.2f |\n', d.method, d.record_id, d.n, d.n_cmd_diff, tstr(d.first_diff_t), ...
      d.dS_event(1), d.dS_event(2), d.dth(1), d.dth(3), d.dth(2), d.dth(4));
end
T = R.runs;
p('\n## 3·4. 실행별 결과 (모든 실행 보존, 대표값 선택 없음)\n\n');
p('ΔS·여유는 R 대비 %%p, 사건 순서 %s. 여유 < 0이면 비틀림 허용 0 %%p 위반입니다.\n\n', strjoin(T{1}.events, ', '));
p('| 실행 | 시간축 | 방식 | ΔS | 사건별 ΔS | θ최대 여유 | θRMS 여유 | 위반 사건 / 기록 | d_cmd | 늦음 | 선택 계산 중앙 / p95 (s) |\n|---|---|---|---|---|---|---|---|---|---|---|\n');
for r = 1:numel(T)
    t = T{r};
    for q = 1:numel(t.m)
        x = t.m(q); if strcmp(x.method, 'R'), continue; end
        p('| %s | %s | %s | %+.3f | %s | %s | %s | %d / %d | %d | %.1f %% | %.3f / %.3f |\n', t.run, t.mode, x.method, x.dS, vstr(x.dS_event), ...
          vstr(x.thmax_margin), vstr(x.thrms_margin), x.viol_events, x.viol_records, x.d_cmd, 100*x.late, x.sel_p50, x.sel_p95);
    end
end
p('\n| 실행 | G2 (PREVIEW ΔS ≥ +2) | 최선 SIMPLE | G3 (PREVIEW − 최선 SIMPLE ≥ +0.5) |\n|---|---|---|---|\n');
for r = 1:numel(T), t = T{r}; p('| %s | %+.3f → %s | %s | %+.3f → %s |\n', t.run, t.G2, pf(t.G2_pass), t.best_simple, t.G3, pf(t.G3_pass)); end
ia = find(cellfun(@(t) strcmp(t.mode, 'actual'), T));
if ~isempty(ia)
    p('\n실측 지연 %d회 범위 (최소 / 중앙 / 최대):\n\n| 방식 | ΔS | 위반 사건 | 늦음 |\n|---|---|---|---|\n', numel(ia));
    for q = 2:numel(M4)
        v = cellfun(@(t) t.m(q).dS, T(ia)); w = cellfun(@(t) t.m(q).viol_events, T(ia)); l = cellfun(@(t) t.m(q).late, T(ia));
        p('| %s | %+.3f / %+.3f / %+.3f | %d / %d / %d | %.1f / %.1f / %.1f %% |\n', M4{q}, min(v), median(v), max(v), min(w), round(median(w)), max(w), 100*min(l), 100*median(l), 100*max(l));
    end
    g3 = cellfun(@(t) t.G3, T(ia)); g2 = cellfun(@(t) t.G2, T(ia));
    p('| G2 | %+.3f / %+.3f / %+.3f | | |\n| G3 | %+.3f / %+.3f / %+.3f | | |\n', min(g2), median(g2), max(g2), min(g3), median(g3), max(g3));
end
write_env(p, R.env);
p('\n## 결론 작성 원칙\n- 재현성(1·2·3절)과 비틀림 보호 문제(위반 사건·여유)는 따로 결론을 씁니다.\n- 실측 지연 5회는 같은 지진 3개를 계산시간만 달리해 다시 돌린 것입니다. 사건 수는 3개 그대로입니다.\n');
fclose(f);
end

function write_env(p, E)
p('\n## 실행 순서·환경\n\n| 순서 | 실행 | 시작 | 끝 | 폐루프 계산 합 (s) | 환경 | 스레드 / 코어 |\n|---|---|---|---|---|---|---|\n');
for k = 1:numel(E)
    e = E{k}; if ~isfield(e, 't_end'), e.t_end = ''; e.wall_total_s = NaN; end
    p('| %d | %s | %s | %s | %.0f | %s | %g / %g |\n', k, e.label, e.t_start, e.t_end, e.wall_total_s, e.env, e.threads, e.cores);
end
end

function s = yn(c), if c, s = '예'; else, s = '**아니오**'; end, end
function s = pf(c), if c, s = '충족'; else, s = '미충족'; end, end
function s = tstr(t), if isnan(t), s = '—'; else, s = sprintf('%.1f s', t); end, end
