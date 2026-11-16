function run_v5_nonlearned(which_tag)
% 비학습 대조군 폐루프 비교 (고정 시간축). 새 학습 없음. 규칙은 01_protocol.md에 실행 전 고정.
%  사용: run_v5_nonlearned            % 전부 (이미 결과가 있는 태그는 건너뜀)
%        run_v5_nonlearned('V5_DET3') % 하나만
here = fileparts(mfilename('fullpath'));
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\predictive_control_matlab';
if ~isfolder(root), error('v4 폴더를 찾을 수 없음: %s', root); end
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests'));
addpath(fullfile(here,'override'));                              % det3 분기가 있는 selector_step.m을 맨 앞에
w = which('selector_step'); assert(contains(w, 'override'), 'override selector_step이 우선 경로가 아님: %s', w);
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
man = read_manifest(fullfile(pc_root(), cfg.paths.record_manifest)); ev = unique(man.event_id, 'stable')';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
seeds = [8401 104729 1299709 15485863 179424673];              % 무작위 시드 5개 (결과 보기 전 고정)
runs = {'V5_SCORER_REF', 'eval', 1,        {'R','J-AI'}; ...
        'V5_DET3',       'det3', 1,        {'J-AI'}};
for k = 1:numel(seeds), runs(end+1, :) = {sprintf('V5_RAND3_S%d', k), 'rand3', seeds(k), {'J-AI'}}; end %#ok<AGROW>
fm = fopen(fullfile(here, 'V5_run_manifest.txt'), 'a');
fprintf(fm, '--- %s | selector_step=%s | MATLAB %s\n', datestr(now,'yyyy-mm-dd HH:MM:SS'), w, version);
for k = 1:size(runs, 1)
    tag = runs{k,1};
    if nargin >= 1 && ~strcmp(which_tag, tag), continue; end
    if isfile(fullfile(root, 'results', ['control_metrics_record_' tag out_tag() '.csv']))
        fprintf('건너뜀(결과 있음): %s\n', tag); continue;
    end
    opt = struct('cfg', cfg, 'models', mo, 'keep_series', false);
    if ~strcmp(runs{k,2}, 'eval'), opt.jpolicy = runs{k,2}; opt.explore_seed = runs{k,3}; end
    t0 = tic; run_benchmarks(tag, runs{k,4}, ev, opt); el = toc(t0);
    fprintf(fm, '%s policy=%s seed=%d elapsed=%.1f s\n', tag, runs{k,2}, runs{k,3}, el);
    fprintf('V5_DONE %s %.1f s\n', tag, el);
end
fclose(fm); disp('V5_ALL_DONE');
end
