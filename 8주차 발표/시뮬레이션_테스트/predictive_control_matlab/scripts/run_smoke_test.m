function run_smoke_test()
% RUN_SMOKE_TEST  계획서 13절 E: 합성 200개(160/40), 최대 10 epoch, seed 8401.
%  완료 조건: 입출력·분할·손실·추론 시간 정상. 성능 판정에 쓰지 않는다.
%  1) 자료 생성  2) 배열 단위시험  3) 학습  4) 손실 감소·예측 진단  5) 짧은 폐루프 1회(AI-C1, El Centro)
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'), fullfile(root, 'tests'));
cfg = pc_config();
f = fullfile(root, 'data', 'forecast_dataset_smoke.mat');
if ~exist(f, 'file'), build_forecast_dataset('smoke'); end
test_lstm_shapes();
info = train_forecaster('smoke', cfg.lstm.smoke_seed);
th = info.history.TrainingHistory; vn = th.Properties.VariableNames;
lc = vn{find(contains(vn, 'Loss'), 1)};                 % 설치 버전의 열 이름 (Loss / TrainingLoss)
h = struct('Loss', th.(lc));
lossdec = mean(h.Loss(end-min(9,end-1):end)) < mean(h.Loss(1:min(10,end)));
fprintf('학습 손실(%s) 처음 %.4f → 끝 %.4f (감소 %d)\n', lc, h.Loss(1), h.Loss(end), lossdec);
select_forecaster('smoke');
fit_var_baseline('smoke');
evaluate_forecasts('smoke', {'zero', 'persistence', 'var', 'lstm'});
[ax, ay] = load_record(cfg, 'ElCentro_1940', cfg.plant.dt);
S = load(fullfile(root, 'models', 'forecaster_selected.mat'));
cfg.latency.timing_mode = 'nominal';   % 파이프라인 점검용 1회 (LSTM 계산시간은 학습 후 측정)
o = run_closed_loop(ax, ay, cfg, pc_method(cfg, 'AI-C1', struct('select_s', 0, 'forecast_s', 0)), struct('dt', cfg.plant.dt, 'model', S.model, 'record_id', 'ElCentro_1940'));
fprintf('폐루프 AI-C1 1회: %.1f s, 예측 %d회 (busy %d, deadline %d), 결정 %d개\n', o.wall_s, o.forecast.n_run, ...
        o.forecast.miss_busy, o.forecast.miss_deadline, size(o.timeline, 1));
fid = fopen(fullfile(root, 'report', 'E_smoke_result.txt'), 'w');
fprintf(fid, '%s\n%s\nval_mse=%.6g  loss %.4f -> %.4f  decreased=%d\ninfer median %.2f ms\nclosed-loop AI-C1 ElCentro wall %.1f s, forecasts %d, miss_busy %d, miss_deadline %d\n', ...
        datestr(now, 31), env_string(), info.val_mse, h.Loss(1), h.Loss(end), lossdec, 1e3*median(info.infer_s), o.wall_s, ...
        o.forecast.n_run, o.forecast.miss_busy, o.forecast.miss_deadline);
fclose(fid);
end
