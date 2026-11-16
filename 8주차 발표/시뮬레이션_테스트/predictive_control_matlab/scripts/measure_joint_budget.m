function B = measure_joint_budget(opt)
% MEASURE_JOINT_BUDGET  J-AI 지속 부하 선택 예산 (계획 §7: 워밍업 뒤 측정, 개발 결과를 보기 전에 고정).
%  점수망 학습 전에 시간축을 정해야 teacher 특징(적용 격자까지 시간)과 비교 시간축이 같으므로,
%  같은 구조(98→128→64→1)의 고정 시드 난수 가중치 점수망으로 계산량을 잰다(선택 결과는 쓰지 않음).
%  기록: 고베 1회 워밍업(버림) → El Centro·포항·고베. 느린 결정(top 3 + 유지 + R 물리 검사 + 그림자 R)과
%        빠른 결정(κ 최대 5 + 그림자 R)의 실측 계산시간 p99를 각각 0.01 s 올림.
%  측정 중 시간축: nominal, 느린 0.50 s·빠른 0.30 s (계산시간 기록만 사용)
%  결과: results/joint_budget<tag>.json
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
cfg = pc_config();
c = joint_timeline(cfg, [0.50 0.30]);
tp = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', cfg.lstm.pilot8_seed));
if isfield(opt, 'model'), tp = opt.model; end
mname = 'J-AI'; mdl = [];
if exist([tp '_weights.mat'], 'file'), mdl = load_torch_model(tp, false); else, mname = 'J-zero'; warning('LSTM 없음 → J-zero 예측으로 측정 (기능 점검용)'); end
SC = dummy_scorer(98);
M = pc_method(c, mname); M.jscorer = true;
rec = {'PEER14', 'ElCentro_1940', 'Pohang_2017_BUS2', 'PEER14'}; w1 = []; w2 = [];
for k = 1:numel(rec)
    [ax, ay] = load_record(c, rec{k}, 0.01);
    if isfinite(opt.max_seconds), n = min(numel(ax), round(opt.max_seconds/0.01) + 1); ax = ax(1:n); ay = ay(1:n); end
    o = run_closed_loop(ax, ay, c, M, struct('dt', 0.01, 'model', mdl, 'scorer', SC));
    if k > 1
        J = o.jlog; J = J(~isnan(J(:,16)), :);
        w1 = [w1; J(J(:,4) == 1, 16)]; w2 = [w2; J(J(:,4) == 2, 16)]; %#ok<AGROW>
    end
    fprintf('예산 측정 %s: 느린 %d, 빠른 %d 결정\n', rec{k}, sum(o.jlog(:,4) == 1), sum(o.jlog(:,4) == 2));
end
q = @(w) ceil(w(max(1, ceil(0.99*numel(w))))/0.01 - 1e-9)*0.01;
w1 = sort(w1); w2 = sort(w2);
if isempty(w1) || isempty(w2), error('measure_joint_budget: 결정 기록 없음'); end
b = [q(w1), q(w2)];
b(2) = max(b(2), 0.01); b(1) = max(b(1), b(2));     % ontime 경로: 앞당김 ≥ R(0.01 s)
pv = run_provenance();
B = struct('budget_s', b, 'slow_p50', w1(ceil(0.5*end)), 'slow_p99', w1(max(1, ceil(0.99*end))), 'fast_p50', w2(ceil(0.5*end)), 'fast_p99', w2(max(1, ceil(0.99*end))), ...
           'n_slow', numel(w1), 'n_fast', numel(w2), 'method', mname, 'env', env_string(), 'commit', pv.commit, 'digest', pv.digest, ...
           'rule', '지속 부하 p99, 0.01 s 올림, 고베 1회 워밍업 제외, 난수 가중치 점수망(같은 구조)', 'feasible', b(1) <= 1.5 && b(2) < 1.0);
f = fopen(fullfile(root, 'results', ['joint_budget' out_tag() '.json']), 'w'); fprintf(f, '%s', jsonencode(B)); fclose(f);
fprintf('J-AI 선택 예산: 느린 %.2f s (p50 %.3f), 빠른 %.2f s (p50 %.3f) → results/joint_budget%s.json\n', b(1), B.slow_p50, b(2), B.fast_p50, out_tag());
if ~B.feasible, warning('J-AI 예산이 격자 조건(느린 ≤ 1.5 s, 빠른 < 1 s)을 넘음 — 비교 실행 전 보고 필요'); end
end

function SC = dummy_scorer(d)
st = rng; rng(8401, 'twister');
SC = struct('path', 'dummy', 'mu', zeros(1, d), 'sd', ones(1, d), 'W1', 0.1*randn(128, d), 'b1', zeros(1, 128), ...
            'W2', 0.1*randn(64, 128), 'b2', zeros(1, 64), 'W3', 0.1*randn(1, 64), 'b3', 0, 'meta', struct());
rng(st);
end
