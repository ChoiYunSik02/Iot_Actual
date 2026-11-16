function R = diagnose_D2(opt)
% DIAGNOSE_D2  D 단계 2차 개발 진단 (2026-10-28 요청). 사전 기준·시험 자료·허용 악화폭은 바꾸지 않는다.
%  관문: A·B·SL·C가 MATLAB에서 통과하고 그 뒤 코드가 바뀌지 않았을 것 (gate.m).
%  1) 후보 집합 비교 — ±45°는 채택하지 않고 개발 진단 후보로만 둔다.
%     base15 {−15,0,+15}° (현행) / d30 {−30,0,+30}° / d45 {−45,0,+45}° / ext {0,±15,±30,±45}°
%     모든 집합에 '현재 목표 유지'와 R 후보가 들어간다(selector_step). 진동수 후보는 현행 ±0.005 Hz.
%     후보 수가 바뀌면 계산시간이 달라지므로 집합마다 C1 선택 예산(p95)을 다시 재서 결정 앞당김(d_cmd)에 넣는다.
%     보고: 사건 평균 ΔS, 나아진 사건, 전체 기록 비틀림 최대·RMS가 R보다 나빠진 사건 수와 최악값, G3 근거
%  2) R 후보와 처음부터 실행한 R의 차이
%     R-lag : R 법칙을 C1과 같은 결정 앞당김(기본 집합 예산)으로 실행 — 정보 지연만의 효과
%     상태 분기: C1 실행 안의 R 후보 지령(같은 격자) 대 R 실행 지령, 그때의 실제 회전각·최상층 응답 차
%  3) 예측 구간 끝 잔여 진동: 선택안과 R 후보를 같은 실제 미래로 다시 모의한 구간 끝 0.5 s 제곱평균 (진단 전용, 제어에 쓰지 않음)
%  4) AI 예측 진단·실행시간: run_torch_smoke 결과(있으면)와 runtime_measure.csv를 같은 표에 넣는다.
%  결과: report/D2_summary.md, results/D2_*.csv
%  opt.allow_prelim (Octave 예비), opt.reuse (저장된 실행 재사용), opt.max_seconds (기능 점검용 자르기)
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'allow_prelim'), opt.allow_prelim = false; end
if ~isfield(opt, 'reuse'), opt.reuse = false; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct && ~opt.allow_prelim, error('diagnose_D2: MATLAB에서 실행'); end
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg = pc_config(); tag = out_tag(); sfx = '';
if isfinite(opt.max_seconds), sfx = '_trunc'; tag = [tag sfx]; end
if isoct, cfg.latency.timing_mode = 'nominal'; end
if ~cfg.latency.compute_measured && ~isoct, error('diagnose_D2: 계산시간 실측 필요 (run_week08_laptop D 단계)'); end
dev = cfg.data.dev_events_control;
C1m = {'SIMPLE-zero', 'SIMPLE-persistence', 'PREVIEW-C1'};
sets = {'base15', [-15 0 15], '현행 ±15°'; 'd30', [-30 0 30], '±30°'; 'd45', [-45 0 45], '±45° (진단 후보, 채택 아님)'; ...
        'ext', [-45 -30 -15 0 15 30 45], '확장 {0,±15,±30,±45}° (진단 후보)'};
B = cell(size(sets, 1), 1); bud = zeros(size(sets, 1), 1);
for k = 1:size(sets, 1)
    c = cfg; c.controller.C1.dtheta_deg = sets{k,2}(:);
    [c, bud(k)] = measure_select_budget(c);
    fprintf('[%s] C1 선택 예산 %.3f s (후보 각도 %s)\n', sets{k,1}, bud(k), mat2str(sets{k,2}));
    B{k} = rb(opt, root, ['D2_' sets{k,1} sfx], [{'R'}, C1m], dev, struct('cfg', c, 'diag_true', true, 'max_seconds', opt.max_seconds));
end
cl = cfg; cl.latency.compute_s.R = bud(1);                    % R 법칙, 결정 앞당김만 C1 기본 집합과 같게
BL = rb(opt, root, ['D2_Rlag' sfx], {'R'}, dev, struct('cfg', cl, 'keep_series', true, 'max_seconds', opt.max_seconds));
% ---------------- 분석 ----------------
Tc = cand_table(B, sets, bud, cfg);
Tr = rlag_table(B{1}, BL, cfg, C1m);
Ta = ai_rows(root);
R = struct('cand', {Tc}, 'rlag', Tr, 'ai', {Ta}, 'budgets', bud, 'sets', {sets(:, [1 3])}, 'provenance', pv);
save(fullfile(root, 'results', ['D2' tag '.mat']), 'R', '-v7');
write_csv(root, tag, Tc);
write_report(root, tag, R, cfg, pv);
fprintf('D2 진단 완료 → report/D2_summary%s.md\n', tag);
end

% =====================================================================
function B = rb(opt, root, tg, methods, dev, o)
f = fullfile(root, 'results', ['benchmarks_' tg out_tag() '.mat']);
if opt.reuse && exist(f, 'file'), L = load(f); B = L.out; fprintf('재사용: %s\n', f);
else, B = run_benchmarks(tg, methods, dev, o); end
end

% =====================================================================
function T = cand_table(B, sets, bud, cfg)
% 행: 후보 집합 × 방식. 전체 기록 비틀림 위반은 사건별 저감률이 R보다 낮은 경우(허용 0 %p, 반올림하지 않음).
T = {};
for k = 1:numel(B)
    S = B{k}.S; iR = find(strcmp(S.methods, 'R'));
    sp_best = -inf; sp_name = '';
    for m = 1:numel(S.methods)
        nm = S.methods{m}; if any(strcmp(nm, {'U', 'R'})), continue; end
        d = S.red_event(:, :, m) - S.red_event(:, :, iR);          % 사건 x 6지표 (%p)
        r = struct('set', sets{k,1}, 'set_label', sets{k,3}, 'method', nm, 'budget', bud(k), 'S', S.S(m), 'dS', S.dS(m), ...
                   'dS_event', S.score_event(:, m)' - S.score_event(:, iR)', 'events', {S.events'}, 'n_better', S.n_better(m), ...
                   'thmax_viol', sum(d(:,5) < 0), 'thmax_worst', min(d(:,5)), 'thrms_viol', sum(d(:,6) < 0), 'thrms_worst', min(d(:,6)));
        [r.late, r.horizon, r.remain, r.d_cmd] = timing_stats(B{k}, nm);
        [r.win_gain, r.tail_ratio, r.tail_worse, r.n_dec] = tail_stats(B{k}, nm);
        if strncmp(nm, 'SIMPLE', 6) && S.dS(m) > sp_best, sp_best = S.dS(m); sp_name = nm; end
        T{end+1} = r; %#ok<AGROW>
    end
    for j = 1:numel(T)                                             % G3 근거: 같은 후보 집합의 PREVIEW − 최선 SIMPLE
        if strcmp(T{j}.set, sets{k,1})
            T{j}.g3_ref = sp_name; T{j}.g3 = NaN;
            if strcmp(T{j}.method, 'PREVIEW-C1'), T{j}.g3 = T{j}.dS - sp_best; end
        end
    end
end
end

function [late, hor, remain, dcmd] = timing_stats(B, nm)
ss = B.series(strcmp({B.series.method}, nm)); A = []; dcmd = NaN;
for q = 1:numel(ss)
    tl = ss(q).timeline; tl = tl(tl(:,4) == 1, :); rt = ss(q).rt;
    A = [A; tl(:,19), tl(:,20) == 4, (tl(:,12) + rt.Hn*rt.r - tl(:,3))*rt.update_period_s/rt.nupd]; %#ok<AGROW>
    dcmd = rt.d_cmd;
end
late = mean(A(:,1)); hor = mean(A(:,2)); v = A(~isnan(A(:,3)), 3); if isempty(v), remain = NaN; else, remain = median(v); end
end

function [wg, tratio, tworse, nd] = tail_stats(B, nm)
% 각 결정: 선택안 대 R 후보, 같은 실제 미래로 다시 모의한 값 (clog 13열 J_true, 21열 구간 끝 잔여_참)
ss = B.series(strcmp({B.series.method}, nm)); G = [];
for q = 1:numel(ss)
    cl = ss(q).clog; if isempty(cl), continue; end
    for d = unique(cl(:,1))'
        c = cl(cl(:,1) == d, :); ch = find(c(:,12) == 1, 1);
        if isempty(ch) || any(any(isnan(c([1 ch], [13 21])))), continue; end
        G(end+1,:) = [100*(1 - c(ch,13)/c(1,13)), c(ch,21)/max(c(1,21), eps), c(ch,21) > c(1,21)*(1 + 1e-12), ch == 1]; %#ok<AGROW>
    end
end
if isempty(G), wg = NaN; tratio = NaN; tworse = NaN; nd = 0; return; end
nd = size(G, 1); wg = mean(G(:,1));
nc = G(:,4) == 0;                                              % R 후보를 고르지 않은 결정만
if any(nc), tratio = median(G(nc,2)); tworse = mean(G(nc,3)); else, tratio = NaN; tworse = NaN; end
end

% =====================================================================
function T = rlag_table(B0, BL, cfg, C1m)
% R-lag 대 R, 그리고 C1 실행 안의 R 후보 지령 대 R 실행 지령 (같은 적용 격자)
T = struct();
S0 = B0.S; SL = BL.S; iR0 = find(strcmp(S0.methods, 'R')); iRL = find(strcmp(SL.methods, 'R'));
T.events = S0.events'; T.R_S = S0.S(iR0); T.Rlag_S = SL.S(iRL);
T.Rlag_dS_event = SL.score_event(:, iRL)' - S0.score_event(:, iR0)';
d = SL.red_event(:, :, iRL) - S0.red_event(:, :, iR0); T.Rlag_dth = d(:, 5:6);
rows = {};
for m = [{'R-lag'}, C1m]
    nm = m{1};
    for q = 1:numel(T.events)
        rid = record_of(B0, T.events{q});
        sR = B0.series(strcmp({B0.series.method}, 'R') & strcmp({B0.series.record_id}, rid));
        if strcmp(nm, 'R-lag'), sA = BL.series(strcmp({BL.series.method}, 'R') & strcmp({BL.series.record_id}, rid)); col = [6 7];
        else, sA = B0.series(strcmp({B0.series.method}, nm) & strcmp({B0.series.record_id}, rid)); col = [9 10]; end
        tA = sA.timeline(sA.timeline(:,4) == 1, :); tR = sR.timeline(sR.timeline(:,4) == 1, :);
        [g, ia, ir] = intersect(tA(:,3), tR(:,3));
        dth = abs(tA(ia, col(2)) - tR(ir, 7))*180/pi; df = abs(tA(ia, col(1)) - tR(ir, 6));
        gi = min(g + 1, numel(sA.theta));                         % 적용 격자에서의 실제 상태
        dang = abs(sA.theta(gi) - sR.theta(gi))*180/pi;
        sc = sqrt(mean(sR.th.^2)); dthr = abs(sA.th(gi) - sR.th(gi))/max(sc, eps);
        early = g*cfg.plant.dt <= 10;
        rows(end+1,:) = {nm, T.events{q}, numel(g), mean(dth, 'omitnan'), mean(df, 'omitnan'), mean(dang), mean(dang(early)), mean(dang(~early)), mean(dthr)}; %#ok<AGROW>
    end
end
T.rows = rows;
end

function rid = record_of(B, ev)
r = B.recs(strcmp({B.recs.event_id}, ev)); rid = r(1).record_id;
end

% =====================================================================
function T = ai_rows(root)
% run_torch_smoke 결과가 있으면 예측 진단(전체 평균)과 추론 시간을 표에 넣는다
T = {};
f = fullfile(root, 'results', 'forecast_metrics_smoke_torch.csv');
if exist(f, 'file')
    L = strsplit(fileread(f), newline);
    for k = 2:numel(L)
        v = strsplit(L{k}, ',');
        if numel(v) >= 13 && strcmp(v{4}, 'all')
            T(end+1,:) = {'forecast', v{2}, v{3}, str2double(v{9}), str2double(v{11}), str2double(v{12})}; %#ok<AGROW>
        end
    end
end
for g = {fullfile(root, 'logs', 'runtime_measure.csv'), fullfile(root, 'logs', 'runtime_measure_torch.csv')}
    if ~exist(g{1}, 'file'), continue; end
    L = strsplit(fileread(g{1}), newline);
    for k = 2:numel(L)
        v = strsplit(strtrim(L{k}), ',');
        if numel(v) >= 8, T(end+1,:) = {'runtime', v{3}, '', str2double(v{6}), str2double(v{7}), str2double(v{8})}; end %#ok<AGROW>
    end
end
end

% =====================================================================
function write_csv(root, tag, Tc)
f = fopen(fullfile(root, 'results', ['D2_candidates' tag '.csv']), 'w');
fprintf(f, 'env,set,method,select_budget_s,d_cmd,S,dS_vs_R,n_better,thmax_viol_events,thmax_worst_pp,thrms_viol_events,thrms_worst_pp,g3_vs_best_simple,g3_ref,late_frac,horizon_frac,remaining_horizon_s,window_gain_true_pct,tail_ratio_median,tail_worse_frac,n_decisions,dS_events\n');
for k = 1:numel(Tc)
    r = Tc{k};
    fprintf(f, '%s,%s,%s,%.4f,%d,%.4f,%.4f,%d,%d,%.4f,%d,%.4f,%.4f,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%s\n', env_string(), r.set, r.method, r.budget, r.d_cmd, ...
            r.S, r.dS, r.n_better, r.thmax_viol, r.thmax_worst, r.thrms_viol, r.thrms_worst, r.g3, r.g3_ref, r.late, r.horizon, r.remain, ...
            r.win_gain, r.tail_ratio, r.tail_worse, r.n_dec, strjoin(arrayfun(@(x) sprintf('%+.2f', x), r.dS_event, 'UniformOutput', false), ' '));
end
fclose(f);
end

function write_report(root, tag, R, cfg, pv)
f = fopen(fullfile(root, 'report', ['D2_summary' tag '.md']), 'w');
p = @(varargin) fprintf(f, varargin{:});
p('# D 단계 2차 진단 요약\n\n');
p('- 실행: %s, 브랜치 `%s`, 커밋 `%s`, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.branch, pv.commit, pv.digest, pv.config_hash);
p('- 개발 사건 %s, timing_mode=%s. **시험 결과 아님.** 사전 기준(G1~G4)·허용 악화폭(비틀림 0 %%p)·자료는 바꾸지 않았습니다.\n', strjoin(cfg.data.dev_events_control', ', '), cfg.latency.timing_mode);
p('- ±45°·확장 집합은 **채택하지 않은 개발 진단 후보**입니다. 설정 파일(`experiment.json`)은 현행 ±15° 그대로입니다.\n\n');
p('## 통합 표 — 후보별 효과 · 비틀림 위반 · G3 근거 · AI 예측 진단 · 실행시간\n\n');
p('사건별 값의 순서: %s.\n', strjoin(R.cand{1}.events(:)', ', '));
p('ΔS·비틀림은 R 대비 %%p(사건 평균 / 사건별). 비틀림 위반 = 전체 기록 저감률이 R보다 낮은 사건 수(3개 중)와 최악값. G3 = 같은 후보 집합에서 PREVIEW − 최선 SIMPLE(기준 +0.5 %%p).\n');
p('구간 끝 잔여 = 선택안이 R 후보를 고르지 않은 결정에서, 같은 실제 미래로 다시 모의한 구간 끝 0.5 s 제곱평균의 비(선택안/R 후보) 중앙값과 >1 비율.\n\n');
p('| 구분 | 후보 집합 | 방식 | ΔS (사건별) | 나아진 사건 | θ최대 위반 (최악) | θRMS 위반 (최악) | G3 근거 | 선택 예산 / d_cmd / 늦음 / 지평 부족 | 남은 예측 구간 | 구간 J 감소(참) | 구간 끝 잔여 비 / >1 |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n');
for k = 1:numel(R.cand)
    r = R.cand{k}; g3 = '—';
    if ~isnan(r.g3), g3 = sprintf('%+.4f (vs %s) → %s', r.g3, r.g3_ref, ternary(r.g3 >= 0.5, '충족', '미충족')); end
    p('| 제어 | %s | %s | %+.4f (%s) | %d/3 | %d (%+.2f) | %d (%+.2f) | %s | %.3f s / %d / %.0f %% / %.0f %% | %.2f s | %+.1f %% | %.2f / %.0f %% |\n', r.set_label, r.method, r.dS, ...
      strjoin(arrayfun(@(x) sprintf('%+.2f', x), r.dS_event, 'UniformOutput', false), ', '), r.n_better, r.thmax_viol, r.thmax_worst, ...
      r.thrms_viol, r.thrms_worst, g3, r.budget, r.d_cmd, 100*r.late, 100*r.horizon, r.remain, r.win_gain, r.tail_ratio, 100*r.tail_worse);
end
for k = 1:size(R.ai, 1)
    a = R.ai(k,:);
    if strcmp(a{1}, 'forecast')
        p('| AI 예측 진단 (smoke) | %s | %s | — | — | — | — | — | — | — | RMSE 1 s %.4f / 4 s %.4f m/s² | — |\n', a{2}, a{3}, a{4}, a{5});
    else
        p('| 실행시간 | — | %s | — | — | — | — | — | 중앙 %.4f / p95 %.4f / 최대 %.4f s | — | — | — |\n', a{2}, a{4}, a{5}, a{6});
    end
end
if isempty(R.ai), p('| AI 예측 진단 | — | (run_torch_smoke 결과 없음) | | | | | | | | | |\n'); end
t = R.rlag;
p('\n## R 후보와 처음부터 실행한 R의 차이\n\n');
p('- C1 실행 안의 **R 후보**는 결정 시점(적용 %.2f s 전)에 그때까지 도착한 관측으로 R 법칙을 계산하고, 예측 구간 동안 그 지령을 유지한 것입니다.\n', R.budgets(1));
p('- **처음부터 실행한 R**은 매 격자 직전(1스텝 앞)에 R 법칙을 다시 계산하고, 자기 궤적을 따라갑니다.\n');
p('- 따라서 차이는 (1) 정보 지연 %.2f s, (2) 앞선 후보 선택으로 달라진 상태, (3) 구간 뒤 재계산 여부입니다. (1)은 R-lag로 따로 봅니다.\n\n', R.budgets(1));
p('| | 사건 평균 S | 사건별 ΔS (R-lag − R) | 비틀림 최대·RMS 차 (사건별) |\n|---|---|---|---|\n');
p('사건 순서: %s\n\n', strjoin(t.events(:)', ', '));
p('| R | %.4f | — | — |\n| R-lag (결정 %.2f s 앞당김) | %.4f | %s | %s |\n\n', t.R_S, R.budgets(1), t.Rlag_S, ...
  strjoin(arrayfun(@(x) sprintf('%+.2f', x), t.Rlag_dS_event, 'UniformOutput', false), ', '), mat2str(round(t.Rlag_dth*100)/100));
p('| 실행 | 사건 | 격자 수 | R 후보(또는 R-lag) 각도 − R 실행 각도 평균 (deg) | 진동수 차 평균 (Hz) | 실제 회전각 차 평균 (deg) | ~10 s | 10 s~ | 최상층 비틀림 차 / R RMS |\n|---|---|---|---|---|---|---|---|---|\n');
for k = 1:size(t.rows, 1)
    p('| %s | %s | %d | %.1f | %.4f | %.1f | %.1f | %.1f | %.2f |\n', t.rows{k,:});
end
p('\n허용 악화폭은 그대로(0 %%p)이고, 실제 미래 응답은 제어기에 주지 않았습니다(구간 J·잔여 진동의 실제 미래 재모의는 기록 전용).\n');
fclose(f);
end

function s = ternary(c, a, b)
if c, s = a; else, s = b; end
end
