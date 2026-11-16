function D = load_dataset(root, stage)
% LOAD_DATASET  data/forecast_dataset_<stage>.mat (Octave에서는 _octave 예비 자료).
if exist('OCTAVE_VERSION', 'builtin') > 0, tag = '_octave'; else, tag = ''; end
f = fullfile(root, 'data', ['forecast_dataset_' stage tag '.mat']);
if ~exist(f, 'file'), error('load_dataset: %s 없음 — build_forecast_dataset(''%s'') 먼저', f, stage); end
D = load(f);
end
