function T = run_ai_pilot(seed)
% RUN_AI_PILOT  8주차 소규모 AI 학습 (PyTorch). seed 생략 시 필수 시드 8401. 추가 시드(8402·8403)는 같은 설정으로 따로 실행하며 성능을 보고 고르지 않는다.
%  학습·검증·체크포인트 선택은 합성 자료만 쓴다(실제 기록 11개는 학습·선택에 쓰지 않고 학습 후 진단에만 씀).
%  학습 전 점검: train 앞 64창 300스텝 과적합 시험(손실이 절반 이하로 줄어야 함, 파이프라인 점검이며 일반화 증거 아님), 무진동 창 비율 기록.
%  1) Python 환경 기록  2) 학습 자료: MATLAB build_forecast_dataset('pilot') (합성 원천 1,000 = 800/200, 생성 시드 84000~84999, 분할 시드 8400, 원천당 창 최대 40)
%     실제 기록은 real_val(개발 3사건) 진단 창으로만 만들어지고 학습·검증 손실·체크포인트 선택에 쓰이지 않는다.
%  3) Python 학습: python/pc_lstm.py --stage pilot8 (최대 100 epoch, 검증 손실 10회 연속 개선 없으면 종료)
%  4) Python 출력 = MATLAB 재구현(lstm_forward) 확인 (≤ 1e-4, 검증 창 50개)
%  5) 예측 진단: zero / persistence / lstmnat (val 합성, real_val 실제 개발 사건)
%  6) 예측 계산시간: MATLAB 재구현 1회 (폐루프에서 쓰는 경로) → config/latency_measured.json forecast_lstmnat
%  결과: models/torch_pilot8_seed<seed>.{pt,json,_weights.mat}, report/P_ai_pilot_seed<seed>.md, results/forecast_metrics_pilot8_seed<seed>.csv
if exist('OCTAVE_VERSION', 'builtin') > 0, error('run_ai_pilot: MATLAB 전용'); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
cfg = pc_config();
pe = pyenv;
if pe.Status == "NotLoaded" && pe.ExecutionMode ~= "OutOfProcess", pyenv('ExecutionMode', 'OutOfProcess'); pe = pyenv; end
if strlength(pe.Executable) == 0, error('run_ai_pilot: Python을 찾지 못함 — pyenv(''Version'', ''...python.exe'') 로 지정'); end
tv = char(py.getattr(py.importlib.import_module('torch'), '__version__'));
env = struct('python', char(pe.Version), 'exe', char(pe.Executable), 'mode', char(pe.ExecutionMode), 'torch', tv);
fprintf('Python %s (%s), torch %s\n', env.python, env.exe, env.torch);
ds = fullfile(root, 'data', 'forecast_dataset_pilot.mat');
if ~exist(ds, 'file'), build_forecast_dataset('pilot'); end
L = cfg.lstm; if nargin < 1, seed = L.pilot8_seed; end
tp = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', seed));
lg = fullfile(root, 'logs', sprintf('torch_pilot8_seed%d_train.log', seed));
cmd = sprintf('"%s" "%s" --dataset "%s" --out "%s" --epochs %d --patience %d --seed %d --device auto --stage pilot8 --overfit_check 300 > "%s" 2>&1', env.exe, ...
              fullfile(root, 'python', 'pc_lstm.py'), ds, tp, L.pilot8_max_epochs, L.pilot8_patience, seed, lg);
t0 = tic; st = system(cmd); t_train = toc(t0);
fprintf('%s', fileread(lg));
if st ~= 0, error('run_ai_pilot: Python 학습 실패 (logs/torch_pilot8_train.log)'); end
meta = jsondecode(fileread([tp '.json']));
if ~isempty(meta.overfit_check) && ~meta.overfit_check.pass, error('run_ai_pilot: 과적합 시험 실패 — 파이프라인 오류 확인 (%s)', lg); end
mpy = load_torch_model(tp, true); mnat = load_torch_model(tp, false);
D = load(ds, 'W'); Xv = D.W.val.X; n = min(50, size(Xv, 3)); dmax = 0;
for j = 1:n
    X = double(Xv(:,:,j));
    y1 = double(mpy.mod.infer(tp, py.numpy.array(X(:)')))'; y2 = lstm_forward(mnat.W, X);
    dmax = max(dmax, max(abs(y1 - y2)));
end
fprintf('Python 대 MATLAB 재구현 최대 차 %.2e\n', dmax);
if dmax > 1e-4, error('run_ai_pilot: 출력 불일치'); end
Tf = evaluate_forecasts('pilot', {'zero', 'persistence', 'lstmnat'}, tp);
measure_runtime('ElCentro_1940', {'forecast_lstmnat'}, sprintf('_pilot8_seed%d', seed), tp);
copyfile(fullfile(root, 'results', 'forecast_metrics_pilot_torch.csv'), fullfile(root, 'results', sprintf('forecast_metrics_pilot8_seed%d.csv', seed)));
T = struct('env', env, 'meta', meta, 'train_wall_s', t_train, 'parity', dmax, 'forecast', {Tf});
f = fopen(fullfile(root, 'report', sprintf('P_ai_pilot_seed%d.md', seed)), 'w'); p = @(varargin) fprintf(f, varargin{:});
pv = run_provenance();
p('# 8주차 소규모 AI 학습 (PyTorch, seed %d)\n\n', seed);
p('- 실행: %s, 커밋 `%s`, 코드 digest `%s`, 설정 `%s`\n', pv.env, pv.commit, pv.digest, pv.config_hash);
p('- Python %s, torch %s, 장치 %s\n', env.python, env.torch, meta.device);
p('- **범위를 제한한 탐색적 학습입니다.** 구조 탐색 없음. 학습·검증·체크포인트 선택은 합성 자료만 사용, 실제 기록은 학습 후 진단에만 사용.\n');
p('- 학습 전 점검: 64창 과적합 시험 손실 %.4f → %.4f (통과), 정답 무진동(RMS<0.1) 창 비율 %.3f\n\n', meta.overfit_check.loss_first, meta.overfit_check.loss_last, meta.quiet_frac_train);
p('| 항목 | 값 |\n|---|---|\n');
p('| 자료 | `build_forecast_dataset(''pilot'')`, 학습 창 %d, 검증 창 %d, 해시 `%s` |\n', meta.n_train, meta.n_val, meta.dataset_sha16);
p('| 학습 | 최대 %d epoch, 종료 epoch %d (최저 검증), 검증 MSE %.4f, %.0f s |\n', meta.epochs_max, meta.best_epoch, meta.val_mse, meta.train_s);
p('| 출력 일치 | Python 대 MATLAB 재구현 %.1e |\n\n', dmax);
p('예측 RMSE (m/s², 사건 평균): `results/forecast_metrics_pilot_torch.csv`\n\n| 자료 | 예측기 | 0.2 s | 1 s | 4 s |\n|---|---|---|---|---|\n');
for k = 1:size(Tf, 1), p('| %s | %s | %.4f | %.4f | %.4f |\n', Tf{k,1}, Tf{k,2}, Tf{k,3}(1), Tf{k,3}(3), Tf{k,3}(5)); end
p('\n예측 계산시간(MATLAB 재구현): `logs/runtime_measure_pilot8_seed%d.csv`, 학습 곡선: `models/torch_pilot8_seed%d.json` history\n', seed, seed);
fclose(f);
fprintf('AI pilot 완료 → report/P_ai_pilot_seed%d.md\n', seed);
end
