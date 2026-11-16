function res = test_simulink_vs_engine(methods, seconds)
% TEST_SIMULINK_VS_ENGINE  계획서 4·13절 B: Simulink 모델 대 MATLAB 스텝 엔진(run_closed_loop) 작은 기록 대조 (MATLAB+Simulink 전용).
%  기본: El Centro 앞 20 s, 방식 U·R·FIX·SIMPLE-zero (지연 0과 지연 있음 두 조건). AI 모델이 있으면 AI-C1 추가.
%  판정: 응답 정규화 최대 오차 ≤ 1e-12, 장치 상태(f, θ, κ) 일치, 선택기 timeline(결정·적용 스텝·지령) 일치.
%  결과: results/simulink_check.csv
if exist('OCTAVE_VERSION', 'builtin') > 0, error('MATLAB + Simulink 전용'); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'src', 'sl'), fullfile(root, 'scripts'));
cfg = pc_config(); cfg.latency.timing_mode = 'nominal';
if nargin < 1 || isempty(methods), methods = {'U', 'R', 'FIX', 'SIMPLE-zero'}; end
if nargin < 2, seconds = 20; end
mf = fullfile(root, 'models', 'forecaster_selected.mat'); model = [];
if exist(mf, 'file'), S = load(mf); model = S.model; methods{end+1} = 'AI-C1'; end
[ax, ay] = load_record(cfg, 'ElCentro_1940', cfg.plant.dt);
n = round(seconds/cfg.plant.dt) + 1; ax = ax(1:n); ay = ay(1:n);
lat = {struct('sensor_s', 0, 'comm_s', 0, 'extra_info_s', 0, 'select_s', 0, 'forecast_s', 0), ...
       struct('sensor_s', 0.1, 'comm_s', 0.05, 'extra_info_s', 0.1, 'select_s', 0, 'forecast_s', 0.05)};
rows = {}; allpass = true;
for m = 1:numel(methods)
    for L = 1:2
        o1 = run_closed_loop(ax, ay, cfg, pc_method(cfg, methods{m}, lat{L}), struct('dt', cfg.plant.dt, 'model', model));
        o2 = run_simulink_case(ax, ay, methods{m}, struct('dt', cfg.plant.dt, 'model', model, 'override', lat{L}, 'cfg', cfg));
        k = 1:o2.n_logged;
        e = max([nrm(o2.ux, o1.ux(k)), nrm(o2.uy, o1.uy(k)), nrm(o2.th, o1.th(k))]);
        de = max(abs([o2.f_dev - o1.f_dev(k); o2.theta - o1.theta(k); o2.kappa - o1.kappa(k)]));
        tl1 = o1.timeline(:, 1:15); tl2 = o2.timeline(:, 1:15);
        okt = isequaln(tl1, tl2);
        ok = e <= 1e-12 && de <= 1e-12 && okt;
        allpass = allpass && ok;
        rows(end+1,:) = {'ElCentro20s', sprintf('%s_lat%d', methods{m}, L-1), 'resp_nmax', e, 1e-12, e <= 1e-12}; %#ok<AGROW>
        rows(end+1,:) = {'ElCentro20s', sprintf('%s_lat%d', methods{m}, L-1), 'device_maxabs', de, 1e-12, de <= 1e-12}; %#ok<AGROW>
        rows(end+1,:) = {'ElCentro20s', sprintf('%s_lat%d', methods{m}, L-1), 'timeline_equal', double(okt), NaN, okt}; %#ok<AGROW>
        rows(end+1,:) = {'ElCentro20s', sprintf('%s_lat%d', methods{m}, L-1), 'wall_simulink_s', o2.wall_s, NaN, true}; %#ok<AGROW>
        fprintf('%-12s 지연%d: 응답 %.2e, 장치 %.2e, timeline %d, Simulink %.1f s / 엔진 %.1f s\n', methods{m}, L-1, e, de, okt, o2.wall_s, o1.wall_s);
    end
end
rows(end+1,:) = {'ALL', 'ALL', 'overall_pass', double(allpass), NaN, allpass};
write_check_csv(fullfile(root, 'results', 'simulink_check.csv'), rows, env_string());
res = struct('pass', allpass);
fprintf('Simulink 대 스텝 엔진 판정: %d (%s)\n', allpass, env_string());
end

function e = nrm(a, b)
e = max(abs(a(:) - b(:)))/max(max(abs(b(:))), eps);
end
