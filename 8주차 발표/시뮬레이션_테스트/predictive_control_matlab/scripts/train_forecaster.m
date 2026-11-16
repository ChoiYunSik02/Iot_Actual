function info = train_forecaster(stage, seed)
% TRAIN_FORECASTER  LSTM 미래 파형 예측기 학습 (계획서 8절, MATLAB + Deep Learning Toolbox 전용).
%  sequenceInput(3) → LSTM(64, last) → FC(128) → ReLU → FC(800)
%  손실 MSE(정규화 미래 X·Y 동일 가중), Adam 1e-3, batch 32, gradient threshold 1,
%  최대 100 epoch(smoke 10), 매 epoch 검증, 검증 손실 10회 연속 개선 없으면 종료, 최저 검증 손실 모델 반환.
%  stage : 'smoke' | 'pilot',  seed : 8401 / 8402 / 8403
%  결과 : checkpoints/net_<stage>_seed<seed>.mat (network, scaler, 순서, dt/W/H, 마스크 규칙, 분할, 버전, 코드 해시)
if exist('OCTAVE_VERSION', 'builtin') > 0, error('train_forecaster: MATLAB Deep Learning Toolbox 필요 (Octave 불가)'); end
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config(); lc = cfg.lstm;
if ~has_product('Deep Learning Toolbox')
    error('train_forecaster: Deep Learning Toolbox 없음 — 계획서 3절: 이 단계 미충족으로 보고');
end
D = load_dataset(root, stage);
if strcmp(stage, 'smoke'), maxep = lc.smoke_epochs; else, maxep = lc.max_epochs; end
rng(seed, 'twister');
layers = [
    sequenceInputLayer(3, 'Name', 'in')
    lstmLayer(lc.hidden, 'OutputMode', 'last', 'Name', 'lstm')
    fullyConnectedLayer(lc.fc1, 'Name', 'fc1')
    reluLayer('Name', 'relu')
    fullyConnectedLayer(lc.out, 'Name', 'fc2')];
Xtr = D.W.train.X; Ytr = D.W.train.Y; Xv = D.W.val.X; Yv = D.W.val.Y;
nb = floor(size(Xtr, 3)/lc.batch);
args = {'adam', ...
    'InitialLearnRate', lc.lr, 'MiniBatchSize', lc.batch, 'GradientThreshold', lc.grad_threshold, ...
    'MaxEpochs', maxep, 'Shuffle', 'every-epoch', ...
    'ValidationData', {Xv, Yv}, 'ValidationFrequency', nb, 'ValidationPatience', lc.patience, ...
    'OutputNetwork', 'best-validation', ...
    'InputDataFormats', 'CTB', 'TargetDataFormats', 'CB', ...
    'Plots', 'none', 'Verbose', true, 'VerboseFrequency', nb};
try
    opts = trainingOptions(args{:});
catch err                                   % 설치 버전이 옛 이름만 지원하는 경우
    warning('OutputNetwork best-validation 미지원(%s) → best-validation-loss 사용', err.message);
    args{find(strcmp(args, 'best-validation'))} = 'best-validation-loss';
    opts = trainingOptions(args{:});
end
t0 = tic;
[net, tr] = trainnet(Xtr, Ytr, layers, lc.loss, opts);
t_train = toc(t0);
% 검증 MSE (정규화, 반환된 최저 검증 손실 모델)
Yh = minibatchpredict(net, Xv, 'InputDataFormats', 'CTB', 'OutputDataFormats', 'CB', 'MiniBatchSize', 256);
assert(isequal(size(Yh), size(Yv)), 'train_forecaster: 예측 배열 크기 %s ≠ 정답 %s', mat2str(size(Yh)), mat2str(size(Yv)));
val_mse = mean((double(Yh(:)) - double(Yv(:))).^2);
% 단건 추론 시간 (온라인과 같은 경로: forecast_lstm)
model = struct('net', net, 'scaler', D.scaler, 'Hn', D.Hn, 'Wn', D.Wn, 'dt', D.dt);
z = double(Xv(:,:,1)); wx = z(1,:)'*D.scaler.sd(1) + D.scaler.mu(1); wy = z(2,:)'*D.scaler.sd(2) + D.scaler.mu(2);
for k = 1:3, forecast_lstm(model, wx, wy, z(3,:)'); end          % 워밍업
tt = zeros(50, 1);
for k = 1:50, t1 = tic; forecast_lstm(model, wx, wy, z(3,:)'); tt(k) = toc(t1); end
info = struct('stage', stage, 'seed', seed, 'val_mse', val_mse, 'train_s', t_train, 'infer_s', tt, ...
              'history', tr, 'n_train', size(Xtr,3), 'n_val', size(Xv,3), 'max_epochs', maxep);
meta = struct('order_in', D.order, 'mask_rule', cfg.forecast.valid_mask_rule, 'dt', D.dt, 'W_s', cfg.forecast.window_s, ...
              'H_s', cfg.forecast.horizon_s, 'split', D.sources, 'cfg_data', D.cfg_data, 'lstm', lc, ...
              'matlab', version, 'toolboxes', ver, 'code_hash', {code_hash(root)}, 'created', datestr(now, 31), ...
              'dataset_env', D.env);
f = fullfile(root, 'checkpoints', sprintf('net_%s_seed%d.mat', stage, seed));
save(f, 'model', 'info', 'meta', '-v7.3');
fprintf('[%s seed %d] val MSE %.4f, 학습 %.0f s, 추론 중앙값 %.1f ms → %s\n', stage, seed, val_mse, t_train, 1e3*median(tt), f);
end
