function model = fit_var_baseline(stage)
% FIT_VAR_BASELINE  비교 예측기 VAR(50) ridge 적합 (계획서 8절). 학습/검증 분할만 사용.
%  학습: train 창의 입력 부분(정규화, 마스크 0 = 0)과 정답 첫 샘플에서 1스텝 회귀쌍을 만든다.
%  ridge 계수: cfg.var.ridge_grid 중 val 창 400스텝 재귀 예측 MSE(정규화)가 가장 낮은 값.
%  결과: models/var_<stage>.mat (forecast_simple('var') 형식)
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
D = load_dataset(root, stage);
L = cfg.var.lags; Hn = D.Hn; Wn = D.Wn;
% 회귀쌍: 창 끝에서 거꾸로 여러 위치 (입력 창 안에서 다음 샘플 예측)
Xtr = D.W.train.X; n = size(Xtr, 3);
rng(cfg.data.split_seed, 'twister');
npos = 8; Phi = zeros(n*npos, 2*L); T = zeros(n*npos, 2); m = 0;
for j = 1:n
    z = double(Xtr(:,:,j)); y0 = double(D.W.train.Y([1 Hn+1], j))';
    zz = [z(1:2,:), y0'];                       % 창 + 정답 첫 샘플 (2 x Wn+1)
    mk = [z(3,:), 1];
    ends = Wn + 1 - (0:npos-1)*25;              % 예측 대상 위치
    for e = ends
        if e - L < 1 || mk(e) < 0.5, continue; end
        m = m + 1;
        Phi(m,:) = [fliplr(zz(1, e-L:e-1)), fliplr(zz(2, e-L:e-1))];
        T(m,:) = zz(:, e)';
    end
end
Phi = Phi(1:m,:); T = T(1:m,:);
G = Phi'*Phi; b = Phi'*T;
grid = cfg.var.ridge_grid(:)'; mse = zeros(size(grid));
Xv = D.W.val.X; Yv = D.W.val.Y; nv = size(Xv, 3);
sub = 1:max(1, floor(nv/1000)):nv;               % 검증 창 최대 약 1,000개로 선택 (계산량)
for g = 1:numel(grid)
    B = (G + grid(g)*m*eye(2*L)) \ b;
    mdl = struct('lags', L, 'B', B, 'mu', [0 0], 'sd', [1 1]);
    e2 = 0;
    for j = sub
        z = double(Xv(:,:,j));
        Yh = forecast_simple('var', z(1,:)', z(2,:)', z(3,:)', mdl, Hn);
        e2 = e2 + mean((Yh(:) - double(Yv(:,j))).^2);
    end
    mse(g) = e2/numel(sub);
    fprintf('ridge %.3g : val MSE %.4f\n', grid(g), mse(g));
end
[~, gb] = min(mse);
B = (G + grid(gb)*m*eye(2*L)) \ b;
model = struct('kind', 'var', 'lags', L, 'B', B, 'mu', D.scaler.mu, 'sd', D.scaler.sd, 'ridge', grid(gb), ...
               'ridge_grid', grid, 'val_mse', mse, 'n_pairs', m, 'stage', stage, 'env', env_string(), 'created', datestr(now, 31));
if exist('OCTAVE_VERSION', 'builtin') > 0, tag = '_octave'; else, tag = ''; end
save(fullfile(root, 'models', ['var_' stage tag '.mat']), '-struct', 'model');
fprintf('VAR(%d) ridge=%.3g, val MSE=%.4f (정규화)\n', L, grid(gb), mse(gb));
end
