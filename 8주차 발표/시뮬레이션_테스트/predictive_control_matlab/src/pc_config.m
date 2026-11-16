function cfg = pc_config(file)
% PC_CONFIG  config/experiment.json을 읽는다. 측정 지연 파일(config/latency_measured.json)이 있으면 compute_s를 덮어쓴다.
root = pc_root();
if nargin < 1 || isempty(file), file = fullfile(root, 'config', 'experiment.json'); end
cfg = jsondecode(fileread(file));
cfg.root = root;
% 사건 목록은 항상 cellstr: JSON 빈 배열 []은 MATLAB jsondecode에서 빈 double이 되어 ismember(cell, double) 오류가 남
for k = {'dev_events_control', 'real_train_events', 'real_val_events', 'test_events'}
    cfg.data.(k{1}) = as_cellstr(cfg.data.(k{1}));
end
cfg.controller.scales_events = as_cellstr(cfg.controller.scales_events);
cfg.config_file = file;
cfg.latency.compute_measured = false;
lm = fullfile(root, 'config', 'latency_measured.json');
if exist(lm, 'file')
    m = jsondecode(fileread(lm));
    fn = fieldnames(m.compute_s);
    for k = 1:numel(fn), cfg.latency.compute_s.(fn{k}) = m.compute_s.(fn{k}); end
    cfg.latency.compute_measured = true;
    cfg.latency.measured_file = lm;
end
end

function c = as_cellstr(v)
if isempty(v), c = {};
elseif ischar(v), c = {v};
else, c = v(:);
end
end
