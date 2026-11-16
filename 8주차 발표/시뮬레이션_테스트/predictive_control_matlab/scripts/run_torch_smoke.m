function T = run_torch_smoke()
% RUN_TORCH_SMOKE  Python/PyTorch 작은 LSTM의 학습·추론 연결 시험 (smoke만; 정식 pilot은 G2·G3 통과 후).
%  Deep Learning Toolbox 구매 보류에 따른 대체 경로. MATLAB/Simulink는 플랜트·평가에 그대로 쓴다.
%  1) Python 환경 기록 (pyenv: 버전, 실행 파일, 실행 모드, torch 버전)
%  2) 학습 자료: MATLAB build_forecast_dataset('smoke') 그대로 (입력·정답·분할 유지, Python에서 다시 만들지 않음)
%  3) Python 학습: python/pc_lstm.py (최대 10 epoch, seed 8401) → models/torch_smoke_seed8401.{pt,json,_weights.mat}
%  4) 연결 단위시험: Python 호출 출력 = MATLAB 재구현(lstm_forward) 출력 (정규화 최대 차 ≤ 1e-4, 검증 창 50개)
%  5) 예측 진단: zero / persistence / torch / lstmnat (val 합성, real_val 실제 개발 사건)
%  6) 실행시간: 예측 갱신 1회 (Python 호출 = numpy 변환 + 호출 + 역변환 / MATLAB 재구현) → config/latency_measured.json
%  7) 폐루프 연결 시험 1회 (El Centro, R·AIPY-C1·AINAT-C1, 실측 지연) — 성능 판정에 쓰지 않음
%  결과: report/T_torch_smoke.md, logs/torch_smoke_train.log, results/forecast_metrics_smoke_torch.csv
%  Python 준비 (노트북 한 번):  pip install -r python/requirements.txt
%     MATLAB에서 Python 지정(필요 시):  pyenv('Version', 'C:\경로\python.exe', 'ExecutionMode', 'OutOfProcess')
if exist('OCTAVE_VERSION', 'builtin') > 0, error('run_torch_smoke: MATLAB 전용 (클라우드 예비 점검은 python/pc_lstm.py 직접 실행)'); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
cfg = pc_config();
% ---- 1) Python 환경 ----
pe = pyenv;
if pe.Status == "NotLoaded" && pe.ExecutionMode ~= "OutOfProcess"
    pyenv('ExecutionMode', 'OutOfProcess');            % torch와 MATLAB 라이브러리 충돌을 피함 (프로세스 간 호출 시간도 실측에 들어감)
    pe = pyenv;
end
if strlength(pe.Executable) == 0, error('run_torch_smoke: Python을 찾지 못함 — pyenv(''Version'', ''...python.exe'') 로 지정'); end
tv = char(py.getattr(py.importlib.import_module('torch'), '__version__'));
env = struct('python', char(pe.Version), 'exe', char(pe.Executable), 'mode', char(pe.ExecutionMode), 'torch', tv);
fprintf('Python %s (%s, %s), torch %s\n', env.python, env.exe, env.mode, env.torch);
% ---- 2) 학습 자료 (MATLAB) ----
ds = fullfile(root, 'data', 'forecast_dataset_smoke.mat');
if ~exist(ds, 'file'), build_forecast_dataset('smoke'); end
% ---- 3) Python 학습 ----
tp = fullfile(root, 'models', sprintf('torch_smoke_seed%d', cfg.lstm.smoke_seed));
lg = fullfile(root, 'logs', 'torch_smoke_train.log');
cmd = sprintf('"%s" "%s" --dataset "%s" --out "%s" --epochs %d --seed %d > "%s" 2>&1', env.exe, fullfile(root, 'python', 'pc_lstm.py'), ...
              ds, tp, cfg.lstm.smoke_epochs, cfg.lstm.smoke_seed, lg);
t0 = tic; st = system(cmd); t_train = toc(t0);
fprintf('%s', fileread(lg));
if st ~= 0, error('run_torch_smoke: Python 학습 실패 (logs/torch_smoke_train.log)'); end
meta = jsondecode(fileread([tp '.json']));
% ---- 4) 연결 단위시험 ----
mpy = load_torch_model(tp, true); mnat = load_torch_model(tp, false);
D = load(ds, 'W'); Xv = D.W.val.X; n = min(50, size(Xv, 3)); dmax = 0;
for j = 1:n
    X = double(Xv(:,:,j));
    y1 = double(mpy.mod.infer(tp, py.numpy.array(X(:)')))'; y2 = lstm_forward(mnat.W, X);
    dmax = max(dmax, max(abs(y1 - y2)));
end
okpar = dmax <= 1e-4;
fprintf('Python 호출 대 MATLAB 재구현: 최대 차 %.2e (기준 1e-4) → %d\n', dmax, okpar);
if ~okpar, error('run_torch_smoke: 출력 불일치 — 입력 배열 순서·변환 확인'); end
% ---- 5) 예측 진단 ----
evaluate_forecasts('smoke', {'zero', 'persistence', 'torch', 'lstmnat'}, tp);
% ---- 6) 실행시간 ----
measure_runtime('ElCentro_1940', {'forecast_zero', 'forecast_persistence', 'forecast_preview', 'forecast_torch', 'forecast_lstmnat'}, '_torch');   % 같은 조건에서 단순 예측과 함께 잼
% ---- 7) 폐루프 연결 시험 ----
B = run_benchmarks('T_connect', {'R', 'AIPY-C1', 'AINAT-C1'}, {'ElCentro1940'}, struct('models', struct('torch', tp)));
T = struct('env', env, 'meta', meta, 'train_wall_s', t_train, 'parity_maxabs', dmax, 'connect', B.S);
write_torch_report(root, T);
end

function write_torch_report(root, T)
f = fopen(fullfile(root, 'report', 'T_torch_smoke.md'), 'w');
p = @(varargin) fprintf(f, varargin{:});
pv = run_provenance();
p('# PyTorch LSTM smoke 학습·추론 연결 시험\n\n');
p('- 실행: %s, 브랜치 `%s`, 커밋 `%s`, 코드 digest `%s`\n', pv.env, pv.branch, pv.commit, pv.digest);
p('- Python %s (`%s`, %s), torch %s\n', T.env.python, T.env.exe, T.env.mode, T.env.torch);
p('- **smoke 연결 시험입니다.** 정식 pilot이 아니며, 예측·제어 성능 주장에 쓰지 않습니다 (G2·G3 통과 후 pilot).\n\n');
p('## 학습\n- 자료: MATLAB `build_forecast_dataset(''smoke'')` 그대로 (합성 160/40, 분할 시드 8400, 생성 시드 84000~84199), 형식 %s, 해시 `%s`\n', T.meta.dataset_format, T.meta.dataset_sha16);
p('- 학습 창 %d, 검증 창 %d, 최대 %d epoch, 최저 검증 MSE %.4f (epoch %d), 학습 %.0f s (MATLAB에서 본 전체 %.0f s)\n', T.meta.n_train, T.meta.n_val, ...
  T.meta.epochs_max, T.meta.val_mse, T.meta.best_epoch, T.meta.train_s, T.train_wall_s);
p('- Python 내부 numpy 순전파 대조 %.1e, MATLAB 재구현 대 Python 호출 %.1e\n\n', T.meta.numpy_parity_maxabs, T.parity_maxabs);
p('## 예측 진단\n`results/forecast_metrics_smoke_torch.csv` (val = 합성 검증, real_val = 실제 개발 사건 El Centro·포항·고베)\n\n');
p('## 실행시간\n`logs/runtime_measure_torch.csv`의 forecast_torch(Python 호출: 변환·호출·역변환 포함), forecast_lstmnat(MATLAB 재구현). 실측 p95가 `config/latency_measured.json`에 들어가 예측 준비 지연(d_fc)으로 쓰입니다.\n\n');
p('## 폐루프 연결 시험 (El Centro 1회, 성능 판정 아님)\n`results/comparison_summary_T_connect.csv`, `logs/runtime_T_connect.csv`\n');
fclose(f);
end
