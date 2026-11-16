function C = estimate_training_cost(n_iter)
% ESTIMATE_TRAINING_COST  E·F 학습 비용 추정 (학습하지 않음). 계획서 8절과 같은 구조·batch로
%  무작위 입력 3 x 500 x 32에 대한 순전파+역전파+Adam 갱신 1회 시간을 노트북에서 잰다.
%  창 수는 Octave 예비 자료 구성 결과(smoke 학습 13,980 / 검증 3,431)와 pilot 상한(원본당 100, 학습 800원본 + 실제 복제)으로 잡는다.
%  결과: results/training_cost_estimate.csv, 반환 struct
if nargin < 1, n_iter = 30; end
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config(); lc = cfg.lstm;
C = struct('env', env_string(), 'available', false);
if ~has_product('Deep Learning Toolbox')
    C.note = 'Deep Learning Toolbox 없음 — 학습 비용을 잴 수 없음'; disp(C.note); return;
end
rng(1);
net = dlnetwork([sequenceInputLayer(3), lstmLayer(lc.hidden, 'OutputMode', 'last'), fullyConnectedLayer(lc.fc1), reluLayer, fullyConnectedLayer(lc.out)]);
X = dlarray(randn(3, 500, lc.batch, 'single'), 'CTB'); T = dlarray(randn(lc.out, lc.batch, 'single'), 'CB');
avg = []; avgsq = []; tt = zeros(n_iter, 1);
for k = 1:n_iter + 3
    t0 = tic;
    [~, g] = dlfeval(@lossgrad, net, X, T);
    [net, avg, avgsq] = adamupdate(net, g, avg, avgsq, k, lc.lr);
    w = toc(t0);
    if k > 3, tt(k-3) = w; end
end
s_it = median(tt);
% 예측 1회 (검증·추론) 시간
tv = zeros(20,1); x1 = dlarray(randn(3, 500, 1, 'single'), 'CTB');
for k = 1:23, t0 = tic; predict(net, x1); w = toc(t0); if k > 3, tv(k-3) = w; end, end
sm = struct('n_train', 13980, 'n_val', 3431, 'epochs', lc.smoke_epochs, 'seeds', 1);
pl = struct('n_train', 80000*1.25, 'n_val', 20000, 'epochs', lc.max_epochs, 'seeds', numel(lc.pilot_seeds));   % 상한: 실제 복제로 학습 창 약 25% 증가 가정
rows = {};
for st = {'smoke', 'pilot'}
    if strcmp(st{1}, 'smoke'), q = sm; else, q = pl; end
    it_ep = ceil(q.n_train/lc.batch);
    val_ep = q.n_val*s_it/lc.batch/3;       % 검증은 순전파만 (대략 학습 1회의 1/3로 가정)
    per_ep = it_ep*s_it + val_ep;
    rows(end+1,:) = {st{1}, q.n_train, q.epochs, q.seeds, it_ep, per_ep, per_ep*q.epochs*q.seeds}; %#ok<AGROW>
end
C = struct('env', env_string(), 'available', true, 's_per_iter', s_it, 'predict_s', median(tv), 'rows', {rows}, ...
           'note', 'pilot은 최대 100 epoch 상한 기준(조기 종료 시 더 짧음). GPU 미사용 가정이면 CPU 시간.');
f = fopen(fullfile(root, 'results', 'training_cost_estimate.csv'), 'w');
fprintf(f, 'env,stage,n_train_windows,max_epochs,seeds,iters_per_epoch,s_per_epoch,s_total_upper\n');
for k = 1:size(rows,1), fprintf(f, '%s,%s,%d,%d,%d,%d,%.1f,%.0f\n', env_string(), rows{k,:}); end
fclose(f);
fprintf('반복 1회 %.1f ms, 단건 추론 %.2f ms\n', 1e3*s_it, 1e3*median(tv));
for k = 1:size(rows,1), fprintf('  %s: epoch당 %.0f s, 상한 합계 %.1f h\n', rows{k,1}, rows{k,6}, rows{k,7}/3600); end
end

function [loss, g] = lossgrad(net, X, T)
Y = forward(net, X);
loss = mse(Y, T);
g = dlgradient(loss, net.Learnables);
end
