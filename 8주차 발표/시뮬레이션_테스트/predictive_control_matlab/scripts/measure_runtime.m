function L = measure_runtime(record_id, which, ctag, tpath)
% MEASURE_RUNTIME  계획서 6절 1항: 노트북에서 예측·후보 계산·R 계산 시간을 각각 실측한다.
%  지연 0으로 한 기록을 돌려 결정별 벽시계 시간을 모은다. 첫 결정(초기화 포함)과 워밍업 후 분포를 구분한다.
%  설정 지연값 = 워밍업 후 95번째 백분위 (사전 고정 규칙). 결과: config/latency_measured.json, logs/runtime_measure.csv
%  record_id : 기본 'ElCentro_1940' (개발 사건)
%  which     : 선택 계산(R, select_C1, select_C2)과 예측 갱신 계산(forecast_*)을 따로 잰다.
%              forecast_lstm_untrained: 학습 전 같은 구조 LSTM(무작위 가중치)의 추론 시간 — 시간 측정 전용, 예측에 쓰지 않음
%  예측 갱신 시간은 선택기를 R로 두고(후보 모의 없이) 예측기만 돌려 잰다.
%  ctag      : 기록 파일 접미사 (예: '_torch' → logs/runtime_measure_torch.csv). 기본 '' 
%  Octave 실행값은 노트북 MATLAB과 다르므로 저장하지 않는다.
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config(); cfg.latency.timing_mode = 'nominal';
if nargin < 1 || isempty(record_id), record_id = 'ElCentro_1940'; end
if nargin < 3, ctag = ''; end
if nargin < 4, tpath = fullfile(root, 'models', 'torch_smoke_seed8401'); end   % forecast_torch/lstmnat에 쓸 모델 (확장자 없이)
if nargin < 2, which = {'R', 'select_C1', 'select_C2', 'forecast_zero', 'forecast_persistence', 'forecast_var', 'forecast_lstm', 'forecast_lstm_untrained'}; end
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
[ax, ay] = load_record(cfg, record_id, cfg.plant.dt);
z = struct('sensor_s', 0, 'comm_s', 0, 'extra_info_s', 0, 'select_s', 0, 'forecast_s', 0);
L = struct(); rows = {};
for w = 1:numel(which)
    key = which{w}; o2 = struct('dt', cfg.plant.dt);
    switch key
        case 'R',             M = pc_method(cfg, 'R', z);
        case 'select_C1',     M = pc_method(cfg, 'SIMPLE-zero', z);
        case 'select_C2',     M = pc_method(cfg, 'SIMPLE-zero', z); M.select = 'C2';
        case 'forecast_zero',        M = pc_method(cfg, 'SIMPLE-zero', z); M.select = 'R';
        case 'forecast_persistence', M = pc_method(cfg, 'SIMPLE-persistence', z); M.select = 'R';
        case 'forecast_preview',     M = pc_method(cfg, 'PREVIEW-C1', z); M.select = 'R';
        case 'forecast_lstm_untrained'
            if ~has_product('Deep Learning Toolbox')
                fprintf('%s: Deep Learning Toolbox 없음/Octave, 건너뜀\n', key); continue;
            end
            lc = cfg.lstm; rng(1);
            net = dlnetwork([sequenceInputLayer(3), lstmLayer(lc.hidden, 'OutputMode', 'last'), fullyConnectedLayer(lc.fc1), reluLayer, fullyConnectedLayer(lc.out)]);
            M = pc_method(cfg, 'AI-C1', z); M.select = 'R';
            o2.model = struct('net', net, 'scaler', struct('mu', [0 0], 'sd', [1 1]), 'Hn', round(cfg.forecast.horizon_s*100));
        case 'forecast_var'
            f = fullfile(root, 'models', 'var_pilot.mat'); if ~exist(f, 'file'), f = fullfile(root, 'models', 'var_smoke.mat'); end
            if ~exist(f, 'file'), fprintf('%s: 모델 없음, 건너뜀\n', key); continue; end
            M = pc_method(cfg, 'SIMPLE-var', z); M.select = 'R'; o2.model = load(f);
        case {'forecast_torch', 'forecast_lstmnat'}          % PyTorch smoke 모델 (Python 호출 / MATLAB 재구현)
            tp = tpath;
            if isoct || ~exist([tp '.pt'], 'file'), fprintf('%s: 모델 없음/Octave, 건너뜀\n', key); continue; end
            if strcmp(key, 'forecast_torch'), M = pc_method(cfg, 'AIPY-C1', z); else, M = pc_method(cfg, 'AINAT-C1', z); end
            M.select = 'R'; o2.model = load_torch_model(tp, strcmp(key, 'forecast_torch'));
        case 'forecast_lstm'
            f = fullfile(root, 'models', 'forecaster_selected.mat');
            if isoct || ~exist(f, 'file'), fprintf('%s: 모델 없음/Octave, 건너뜀\n', key); continue; end
            M = pc_method(cfg, 'AI-C1', z); M.select = 'R'; S = load(f); o2.model = S.model;
    end
    o = run_closed_loop(ax, ay, cfg, M, o2);
    if strncmp(key, 'forecast', 8)
        t = o.forecast.log(:,4); t = t(~isnan(t));
    else
        tl = o.timeline;
        if strcmp(key, 'R'), t = tl(:,18); else, t = tl(tl(:,4) == 1, 18); end   % 후보 평가가 있는 펌프·각도 결정
        t = t(~isnan(t));
    end
    first = t(1); tw = sort(t(2:end));
    p95 = tw(max(1, ceil(0.95*numel(tw))));
    L.(key) = p95;
    rows(end+1,:) = {key, numel(t), first, median(tw), p95, tw(end)}; %#ok<AGROW>
    fprintf('%-14s n=%3d  첫 %.4f s / 중앙 %.4f s / p95 %.4f s / 최대 %.4f s\n', key, numel(t), first, median(tw), p95, tw(end));
end
f = fopen(fullfile(root, 'logs', ['runtime_measure' ctag out_tag() '.csv']), 'w');
fprintf(f, 'env,record_id,item,n,first_s,median_s,p95_s,max_s\n');
for k = 1:size(rows, 1), fprintf(f, '%s,%s,%s,%d,%.6g,%.6g,%.6g,%.6g\n', env_string(), record_id, rows{k,:}); end
fclose(f);
if ~isoct
    lm = fullfile(root, 'config', 'latency_measured.json');
    if exist(lm, 'file')                      % 앞서 잰 항목은 유지하고 이번에 잰 항목만 갱신
        old = jsondecode(fileread(lm)); fn = fieldnames(L);
        for k = 1:numel(fn), old.compute_s.(fn{k}) = L.(fn{k}); end
        L = old.compute_s;
    end
    out = struct('compute_s', L, 'rule', '워밍업 후 95번째 백분위', 'record_id', record_id, 'env', env_string(), ...
                 'created', datestr(now, 31), 'cores', feature('numcores'), 'provenance', run_provenance());
    if isfield(out.compute_s, 'forecast_lstm_untrained')      % 학습 전 값은 참고용으로만 두고 forecast_lstm에 넣지 않음
        out.note = 'forecast_lstm_untrained는 같은 구조 무작위 가중치 LSTM의 추론 시간(비용 추정용). 학습 후 forecast_lstm을 다시 잰다.';
    end
    fid = fopen(lm, 'w'); fprintf(fid, '%s', jsonencode(out)); fclose(fid);
    fprintf('→ config/latency_measured.json (이후 실행의 계산 지연으로 쓰임)\n');
end
end
