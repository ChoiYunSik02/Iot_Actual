function R = run_joint_comparison(opt)
% RUN_JOINT_COMPARISON  8주차 v2 비교 (계획 §8): 펌프·회전판·밸브 공동 선택
%  비교군: U, R, J-zero, J-persistence (전체 후보 + 단순 예측), J-AIF (전체 후보 + AI 예측),
%          J-AI (주 실험: AI 예측 + 점수망 top 3 + 유지 + R 물리 확인), C1J-AI (밸브 R, 펌프·각도 전체 후보 + AI 예측),
%          J-PREVIEW (전체 후보 + 실제 미래 입력, 엄밀한 상한 아님)
%  주 비교: 공통 고정 시간축 (모든 방식에 J-AI 실측 예산, 이상화 알고리즘 비교 — 전체 후보 방식은 실시간 불가할 수 있음)
%  보조: J-AI 실측 지연 1회 (late·fallback ≥ 90 %면 계산 예산 부적합), 전체 후보 방식은 실측 계산시간으로 실행 가능성만 판정
%  사건: opt.events 'dev'(El Centro·고베·포항, 기본) | 'all'(기존 11개 기록) — 모두 개발 평가
%  opt.budget [느린 빠른] (기본 results/joint_budget<tag>.json), opt.scorer, opt.model, opt.max_seconds, opt.allow_prelim, opt.methods
%  결과: week08_submission/results/JC_*.csv, report/JC_summary<tag>.md, results/JC<tag>.mat
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'allow_prelim'), opt.allow_prelim = false; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
if ~isfield(opt, 'events'), opt.events = 'dev'; end
if ~isfield(opt, 'actual'), opt.actual = true; end
if ~isfield(opt, 'fixed'), opt.fixed = true; end
if ~isfield(opt, 'label'), opt.label = ''; end   % 결과 파일 이름 꼬리표 (기존 결과를 덮어쓰지 않게)
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct && ~opt.allow_prelim, error('run_joint_comparison: MATLAB에서 실행'); end
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg = pc_config();
sfx = ''; if isfinite(opt.max_seconds), sfx = '_trunc'; end
if strcmp(opt.events, 'all'), sfx = [sfx '_all']; end
sfx = [sfx opt.label];
tag = [out_tag() sfx];
od = fullfile(root, 'week08_submission', 'results'); if ~exist(od, 'dir'), mkdir(od); end
if ~isfield(opt, 'budget')
    fb = fullfile(root, 'results', ['joint_budget' out_tag() '.json']);
    if ~exist(fb, 'file'), error('run_joint_comparison: %s 없음 (run_week08_laptop JB 먼저)', fb); end
    jb = jsondecode(fileread(fb)); opt.budget = jb.budget_s(:)';
end
if ~isfield(opt, 'model'), opt.model = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', cfg.lstm.pilot8_seed)); end
if ~isfield(opt, 'scorer'), opt.scorer = fullfile(root, 'models', sprintf('joint_scorer_seed%d', cfg.joint_scorer.seed)); end
if ~isfield(opt, 'methods'), opt.methods = {'R', 'J-zero', 'J-persistence', 'J-AIF', 'J-AI', 'C1J-AI', 'J-PREVIEW'}; end
M = opt.methods;
if strcmp(opt.events, 'all')
    man = read_manifest(fullfile(root, cfg.paths.record_manifest)); ev = unique(man.event_id, 'stable')';
else
    ev = cfg.data.dev_events_control(:)';
end
mo = struct('lstmnat', opt.model, 'scorer', opt.scorer);
c = joint_timeline(cfg, opt.budget);
E = {}; B = {}; nm = {};
if opt.fixed
    E{end+1} = struct('run', 'fixed', 't_start', datestr(now, 'yyyy-mm-dd HH:MM:SS'), 'env', env_string());
    B{end+1} = run_benchmarks(['JC_fixed' sfx], M, ev, struct('cfg', c, 'models', mo, 'keep_series', true, 'max_seconds', opt.max_seconds));
    E{end}.t_end = datestr(now, 'yyyy-mm-dd HH:MM:SS'); nm{end+1} = 'fixed';
end
if opt.actual
    ca = c; ca.latency.timing_mode = 'actual'; if isoct, ca.latency.timing_mode = 'nominal'; end
    E{end+1} = struct('run', 'actual', 't_start', datestr(now, 'yyyy-mm-dd HH:MM:SS'), 'env', env_string());
    ma = {'R', 'J-AI'}; if ~opt.fixed && isfield(opt, 'methods'), ma = M; end
    B{end+1} = run_benchmarks(['JC_actual' sfx], ma, ev, struct('cfg', ca, 'models', mo, 'keep_series', true, 'max_seconds', opt.max_seconds));
    E{end}.t_end = datestr(now, 'yyyy-mm-dd HH:MM:SS'); nm{end+1} = 'actual';
end
S = cell(1, numel(B));
for k = 1:numel(B), S{k} = summarize(B{k}, nm{k}, B{k}.S.methods(~strcmp(B{k}.S.methods, 'U'))); end
sc = load_scorer(opt.scorer);
R = struct('provenance', pv, 'budget', opt.budget, 'runs', {S}, 'env', {E}, 'model', opt.model, 'scorer', opt.scorer, ...
           'scorer_metrics', sc.meta.metrics, 'events', {ev});
save(fullfile(root, 'results', ['JC' tag '.mat']), 'R', '-v7');
write_csv(od, tag, S);
export_series(od, tag, B{1});
write_report(root, tag, R);
fprintf('공동 선택 비교 완료 → report/JC_summary%s.md, week08_submission/results/JC_*%s.csv\n', tag, tag);
end

% =====================================================================
function T = summarize(B, name, M)
S = B.S; iR = find(strcmp(S.methods, 'R'));
T = struct('run', name, 'mode', B.cfg.latency.timing_mode, 'events', {S.events(:)'}, 'm', struct([]));
mm = struct([]);
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
    ss = B.series(strcmp({B.series.method}, M{q}));
    % 공동 결정 통계 (jlog: [i s g kind n_cand n_eval n_feas cid_sel isR isHold scorer f th k acc wall miss reason])
    J = zeros(0, 18); TL = zeros(0, 23); km = 0;
    for k = 1:numel(ss)
        if ~isempty(ss(k).jlog), J = [J; ss(k).jlog]; end %#ok<AGROW>
        TL = [TL; ss(k).timeline]; x.d_cmd = [ss(k).rt.d_cmd, ss(k).rt.d_cmd_V, ss(k).rt.d_cmd_R]; %#ok<AGROW>
        km = km + sum(abs(diff(ss(k).kappa(2:end))))/numel(ss);
    end
    x.kappa_move = km;
    x.n_slow = sum(J(:,4) == 1); x.n_fast = sum(J(:,4) == 2);
    j1 = J(J(:,4) == 1, :); j2 = J(J(:,4) == 2, :);
    if isempty(j1), j1 = nan(1, 18); j1(:, [9 10 11 15]) = 0; end   % R 방식: 공동 결정 없음
    if isempty(j2), j2 = nan(1, 18); j2(:, 15) = 0; end
    fr = @(v) mean(double(v));
    x.slow_hold = fr(j1(:,10) & j1(:,15)); x.slow_R = fr(j1(:,9) | ~j1(:,15)); x.slow_tuple = fr(~j1(:,9) & ~j1(:,10) & j1(:,15));
    x.slow_ai_applied = sum(~j1(:,9) & ~j1(:,10) & j1(:,15) & j1(:,11));   % 점수망 top 3 tuple이 실제 적용된 느린 결정 수
    x.fast_cand = fr(j2(:,15)); x.fast_R = fr(~j2(:,15));
    x.n_eval = [median(j1(:,6)), median(j2(:,6))]; x.n_cand = [min(j1(:,5)), median(j1(:,5)), max(j1(:,5))];
    x.no_feasible = fr(j1(:,18) == 6); x.late = fr(J(:,17));
    w1 = sort(j1(~isnan(j1(:,16)), 16)); w2 = sort(j2(~isnan(j2(:,16)), 16));
    pq = @(w, p) w(max(1, ceil(p*numel(w))));
    if isempty(w1), w1 = NaN; end, if isempty(w2), w2 = NaN; end
    x.wall_slow = [pq(w1, 0.5), pq(w1, 0.95), pq(w1, 0.99)]; x.wall_fast = [pq(w2, 0.5), pq(w2, 0.95), pq(w2, 0.99)];
    % 장치별 R과 다른 지령이 적용된 격자 비율 (timeline: 6 f 7 th 8 k 9 fR 10 thR 11 kR)
    p = TL(TL(:,4) == 1, :); v = TL(TL(:,5) == 1, :);
    if isempty(p), p = nan(1, 23); end, if isempty(v), v = nan(1, 23); end
    x.diff_f = fr(abs(p(:,6) - p(:,9)) > 1e-12); x.diff_th = fr(abs(p(:,7) - p(:,10)) > 1e-12); x.diff_k = fr(abs(v(:,8) - v(:,11)) > 1e-12 & ~isnan(v(:,8)));
    x.realtime_ok = double(x.wall_slow(3) <= 1.5 && (isnan(x.wall_fast(3)) || x.wall_fast(3) < 1.0));
    if all(isnan(x.wall_slow)), x.realtime_ok = NaN; end           % R: 공동 결정 없음 (판정 대상 아님)
    mm = [mm, x]; %#ok<AGROW>
end
T.m = mm;
g = @(n) mm(strcmp({mm.method}, n));
if any(strcmp(M, 'J-zero')) && any(strcmp(M, 'J-AI'))
    A = g('J-AI'); Z = g('J-zero'); Q = g('J-persistence'); F = g('J-AIF'); C = g('C1J-AI'); P = g('J-PREVIEW');
    [bs, ib] = max([Z.dS, Q.dS]); sn = {'J-zero', 'J-persistence'};
    T.best_simple = sn{ib}; T.ai_R = A.dS; T.ai_zero = A.dS - Z.dS; T.ai_pers = A.dS - Q.dS; T.ai_best = A.dS - bs;
    T.forecast_effect = F.dS - bs; T.scorer_effect = A.dS - F.dS; T.valve_effect = F.dS - C.dS; T.preview_R = P.dS;
end
end

function write_csv(od, tag, S)
f = fopen(fullfile(od, ['JC_runs' tag '.csv']), 'w');
fprintf(f, '# 평균 단위: 6지표 저감률(무제어 대비 %%) → 기록 평균 → 사건 내 평균 → 사건 동일 가중 평균. dS = 방식 − 원래 R (%%p). 개발 평가\n');
fprintf(f, ['run,timing_mode,method,S_pct,dS_vs_R_pp,dS_events,n_better,n_worse,thmax_margin_events,thrms_margin_events,violation_events,violation_records,worst_torsion_pp,' ...
            'rotation_deg_per_record,pump_hz_per_record,valve_switches_per_record,kappa_move_per_record,d_cmd_slow,d_cmd_fast,d_cmd_R,n_slow,n_fast,' ...
            'slow_frac_hold,slow_frac_R,slow_frac_tuple,slow_ai_tuple_applied,fast_frac_cand,fast_frac_R,frac_no_feasible,late_frac,' ...
            'grid_frac_f_not_R,grid_frac_theta_not_R,grid_frac_kappa_not_R,n_cand_min,n_cand_med,n_cand_max,n_eval_slow_med,n_eval_fast_med,' ...
            'wall_slow_p50,wall_slow_p95,wall_slow_p99,wall_fast_p50,wall_fast_p95,wall_fast_p99,realtime_feasible\n']);
for r = 1:numel(S)
    t = S{r};
    for q = 1:numel(t.m)
        x = t.m(q);
        fprintf(f, '%s,%s,%s,%.4f,%.4f,%s,%d,%d,%s,%s,%d,%d,%.4f,%.2f,%.5f,%.1f,%.3f,%d,%d,%d,%d,%d,%.4f,%.4f,%.4f,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%g,%g,%g,%g,%g,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%g\n', ...
            t.run, t.mode, x.method, x.S, x.dS, vs(x.dS_event), x.n_better, x.n_worse, vs(x.thmax), vs(x.thrms), x.viol_ev, x.viol_rec, x.worst_th, x.burden, x.kappa_move, ...
            x.d_cmd, x.n_slow, x.n_fast, x.slow_hold, x.slow_R, x.slow_tuple, x.slow_ai_applied, x.fast_cand, x.fast_R, x.no_feasible, x.late, ...
            x.diff_f, x.diff_th, x.diff_k, x.n_cand, x.n_eval, x.wall_slow, x.wall_fast, x.realtime_ok);
    end
end
fclose(f);
g = fopen(fullfile(od, ['JC_event_metrics' tag '.csv']), 'w');
fprintf(g, '# 6지표 저감률 %% (무제어 대비), 사건 내 기록 평균. 개발 평가\nrun,method,event,red_uxmax,red_uxrms,red_uymax,red_uyrms,red_thmax,red_thrms,mean6,dS_vs_R_pp\n');
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

function export_series(od, tag, B)
% 시간이력(0.02 s)과 공동 결정 기록 (느린·빠른 결정마다 선택 tuple·평가 수·적용 여부)
rids = unique({B.series.record_id}, 'stable'); dt = B.cfg.plant.dt;
for k = 1:numel(rids)
    f = fopen(fullfile(od, sprintf('JC_series_%s%s.csv', rids{k}, tag)), 'w');
    fprintf(f, 'method,t_s,ux_m,uy_m,th_rad,pump_f_dev_hz,rotation_rad,valve_kappa\n');
    ss = B.series(strcmp({B.series.record_id}, rids{k}));
    for q = 1:numel(ss)
        sr = ss(q);
        for j = 1:2:numel(sr.ux)
            fprintf(f, '%s,%.2f,%.6e,%.6e,%.6e,%.6f,%.5f,%.4f\n', sr.method, (j-1)*dt, sr.ux(j), sr.uy(j), sr.th(j), sr.f_dev(j), sr.theta(j), sr.kappa(j));
        end
    end
    fclose(f);
    f = fopen(fullfile(od, sprintf('JC_decisions_%s%s.csv', rids{k}, tag)), 'w');
    fprintf(f, 'method,decision_t_s,last_obs_t_s,apply_t_s,kind,n_cand,n_eval,n_feasible,cid_selected,is_R,is_hold,scorer_used,f_hz,theta_rad,kappa,accepted,select_wall_s,late,reason_code\n');
    for q = 1:numel(ss)
        J = ss(q).jlog;
        for j = 1:size(J, 1)
            fprintf(f, '%s,%.2f,%.2f,%.2f,%d,%d,%d,%g,%d,%d,%d,%d,%.6g,%.6g,%.6g,%d,%.4f,%d,%d\n', ss(q).method, J(j,1)*dt, J(j,2)*dt, J(j,3)*dt, J(j,4:11), J(j,12:14), J(j,15), J(j,16), J(j,17), J(j,18));
        end
    end
    fclose(f);
end
end

function write_report(root, tag, R)
f = fopen(fullfile(root, 'report', ['JC_summary' tag '.md']), 'w'); p = @(varargin) fprintf(f, varargin{:});
pv = R.provenance; S = R.runs;
p('# 8주차 v2: 펌프·회전판·밸브 공동 선택 비교 (탐색적, 개발 평가)\n\n');
p('- 실행: %s, 커밋 `%s`, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.commit, pv.digest, pv.config_hash);
p('- 사건: %s — 모두 이전 개발에 쓰인 기록이므로 **개발 평가**\n', strjoin(R.events, ', '));
p('- 파형 AI `%s`, 공동 후보 점수망 `%s` (합성 teacher 80/20 기록, 실제 기록 미사용)\n', R.model, R.scorer);
p('- 공통 고정 시간축: 느린 결정 %.2f s, 빠른 결정 %.2f s (J-AI 지속 부하 p99), 센서·통신 0, 예측 준비 1스텝, R 1스텝. 이상화 알고리즘 비교이며 전체 후보 방식의 실시간 가능성은 아래 계산시간으로 따로 판정\n', R.budget(1), R.budget(2));
p('- 이상적 상태정보 조건(플랜트 상태 사본). 그림자 R 제한은 예측에 의존하며 실제 무악화를 보장하지 않음\n\n');
if isfield(R.scorer_metrics, 'val')
    v = R.scorer_metrics.val; vr = R.scorer_metrics.val_random;
    p('점수망 검증(합성 val, 느린 결정, 실제 미래 teacher): top 3 적중 %.2f (무작위 %.2f), 검사 집합 최선 포함 %.2f, regret %.4f (무작위 %.4f), fallback %.2f\n\n', ...
      v.top3_hit, vr.top3_hit, v.eval_hit, v.regret, vr.regret, v.fallback);
end
for r = 1:numel(S)
    t = S{r};
    p('## %s (%s)\n\n사건 순서: %s. 평균 단위: 6지표 → 기록 → 사건 내 → 사건 동일 가중.\n\n', t.run, t.mode, strjoin(t.events, ', '));
    p('| 방식 | S %% | R 대비 %%p | 사건별 | 위반 사건/기록 | 최악 비틀림 | 느린: 유지/R/tuple | AI tuple 적용 | 빠른: 후보/R | no_feasible | 늦음 | 밸브 전환 | κ 이동 | 선택 p99 느린/빠른 s | 실시간 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n');
    for q = 1:numel(t.m)
        x = t.m(q);
        p('| %s | %.2f | %+.2f | %s | %d/%d | %+.2f | %.0f/%.0f/%.0f %% | %d | %.0f/%.0f %% | %.0f %% | %.0f %% | %.1f | %.2f | %.2f/%.2f | %s |\n', x.method, x.S, x.dS, vs(x.dS_event), ...
          x.viol_ev, x.viol_rec, x.worst_th, 100*x.slow_hold, 100*x.slow_R, 100*x.slow_tuple, x.slow_ai_applied, 100*x.fast_cand, 100*x.fast_R, 100*x.no_feasible, 100*x.late, ...
          x.burden(3), x.kappa_move, x.wall_slow(3), x.wall_fast(3), yn(x.realtime_ok));
    end
    if isfield(t, 'ai_R')
        p('\n- J-AI − R %+.2f · − J-zero %+.2f · − J-persistence %+.2f · − 최선 단순(%s) %+.2f %%p\n', t.ai_R, t.ai_zero, t.ai_pers, t.best_simple, t.ai_best);
        p('- 파형 예측 효과(J-AIF − 최선 단순) %+.2f · 점수망 효과(J-AI − J-AIF) %+.2f · 밸브 공동 선택 효과(J-AIF − C1J-AI) %+.2f · PREVIEW − R %+.2f\n', ...
          t.forecast_effect, t.scorer_effect, t.valve_effect, t.preview_R);
        a = t.m(strcmp({t.m.method}, 'J-AI'));
        p('\n## 판정 (각각 따로)\n- R 대비 +2~3 %%p: %+.2f → %s\n- 단순 예측 대비 AI 추가 기여: %+.2f → %s\n- 비틀림 허용 0 %%p: 위반 사건 %d, 최악 %+.2f → %s\n', ...
          t.ai_R, ok(t.ai_R >= 2), t.ai_best, ok(t.ai_best > 0), a.viol_ev, a.worst_th, ok(a.viol_ev == 0));
        if a.slow_ai_applied == 0, p('- 점수망 tuple이 한 번도 적용되지 않음 → 제어 효과 입증 아님\n'); end
    elseif strcmp(t.mode, 'actual')
        a = t.m(strcmp({t.m.method}, 'J-AI'));
        if ~isempty(a) && (a.late + a.slow_R) >= 0.9, p('\n- **계산 예산 부적합**: J-AI 느린 결정의 90 %% 이상이 R로 복귀 → AI 성능 근거로 쓰지 않음\n'); end
    end
    p('\n');
end
p('실행: '); for k = 1:numel(R.env), p('%s(%s~%s) ', R.env{k}.run, R.env{k}.t_start, R.env{k}.t_end); end
p('\n');
fclose(f);
end

function s = ok(c), if c, s = '달성'; else, s = '미달'; end, end
function s = yn(c), if isnan(c), s = '—'; elseif c, s = '가능'; else, s = '불가'; end, end
