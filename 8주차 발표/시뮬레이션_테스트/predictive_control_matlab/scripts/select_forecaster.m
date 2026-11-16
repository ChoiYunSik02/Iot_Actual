function best = select_forecaster(stage)
% SELECT_FORECASTER  배포용 시드 선택: 검증 MSE가 가장 낮은 시드 (계획서 8절). 시험 성능은 보지 않는다.
%  결과: models/forecaster_selected.mat, results/forecaster_seeds_<stage>.csv
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
if strcmp(stage, 'smoke'), seeds = cfg.lstm.smoke_seed; else, seeds = cfg.lstm.pilot_seeds(:)'; end
v = inf(size(seeds));
f = fopen(fullfile(root, 'results', ['forecaster_seeds_' stage '.csv']), 'w');
fprintf(f, 'stage,seed,val_mse,train_s,infer_median_ms,epochs_max\n');
for k = 1:numel(seeds)
    p = fullfile(root, 'checkpoints', sprintf('net_%s_seed%d.mat', stage, seeds(k)));
    if ~exist(p, 'file'), warning('없음: %s', p); continue; end
    S = load(p, 'info'); v(k) = S.info.val_mse;
    fprintf(f, '%s,%d,%.6g,%.1f,%.3f,%d\n', stage, seeds(k), S.info.val_mse, S.info.train_s, 1e3*median(S.info.infer_s), S.info.max_epochs);
end
fclose(f);
[~, b] = min(v); if isinf(v(b)), error('select_forecaster: 체크포인트 없음'); end
best = seeds(b);
S = load(fullfile(root, 'checkpoints', sprintf('net_%s_seed%d.mat', stage, best)));
S.selected = struct('stage', stage, 'seed', best, 'rule', '검증 MSE 최소', 'all_seeds', seeds, 'val_mse', v);
save(fullfile(root, 'models', 'forecaster_selected.mat'), '-struct', 'S', '-v7.3');
fprintf('선택: %s seed %d (val MSE %.4f)\n', stage, best, v(b));
end
