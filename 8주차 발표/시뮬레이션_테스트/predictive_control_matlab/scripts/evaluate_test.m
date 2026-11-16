function evaluate_test()
% EVALUATE_TEST  계획서 12·13절 H: 봉인된 새 사건에서 한 번만 평가.
%  조건: config data.test_events가 비어 있지 않고, 설정이 config/frozen/에 동결되어 있으며, 결과가 아직 없을 것.
%  현재 저장소에는 새 시험 사건이 없으므로 이 스크립트는 실행을 거부하고 그 사실을 기록한다.
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
if isempty(cfg.data.test_events)
    msg = '시험 사건 없음 (data.test_events = []). H 단계 미실행: 새 실제 사건을 record_manifest.csv에 split=test로 추가하고 설정을 동결한 뒤 실행';
    fid = fopen(fullfile(root, 'report', 'H_not_run.txt'), 'w'); fprintf(fid, '%s\n%s\n', datestr(now, 31), msg); fclose(fid);
    error('evaluate_test: %s', msg);
end
frz = fullfile(root, 'config', 'frozen', 'experiment.json');
if ~exist(frz, 'file'), error('evaluate_test: 동결 설정 %s 없음', frz); end
res = fullfile(root, 'results', 'comparison_summary_H_test.csv');
if exist(res, 'file'), error('evaluate_test: 이미 평가함 (%s). 시험은 한 번만', res); end
methods = {'R', 'FIX', 'SIMPLE-var', 'AI-C1', 'AI-C2', 'AI-ideal-C1', 'PREVIEW-C1'};
models = struct('var', fullfile(root, 'models', 'var_pilot.mat'), 'lstm', fullfile(root, 'models', 'forecaster_selected.mat'));
run_benchmarks('H_test', methods, cfg.data.test_events, struct('models', models, 'allow_test', true));
end
