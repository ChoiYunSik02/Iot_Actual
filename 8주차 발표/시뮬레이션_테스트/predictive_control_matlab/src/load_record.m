function [agx, agy, meta] = load_record(cfg, record_id, dt)
% LOAD_RECORD  data/records/dt*/<record_id>.csv (scripts/export_records.py 출력) 읽기.
if nargin < 3, dt = cfg.plant.dt; end
f = fullfile(cfg.root, cfg.paths.records_dir, sprintf('dt%g', dt), [record_id '.csv']);
if ~exist(f, 'file'), error('load_record: %s 없음 (scripts/export_records.py 실행 필요)', f); end
D = dlmread(f, ',', 1, 0);
agx = D(:,2); agy = D(:,3);
man = read_manifest(fullfile(cfg.root, cfg.paths.record_manifest));
k = find(strcmp(man.record_id, record_id), 1);
meta = struct('record_id', record_id, 'event_id', man.event_id{k}, 'split', man.split{k}, 'dt', dt);
end
