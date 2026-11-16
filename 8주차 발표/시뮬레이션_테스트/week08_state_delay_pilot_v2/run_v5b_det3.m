function run_v5b_det3()
% 수정 실행: run_benchmarks가 원본 src를 경로 맨 앞으로 되돌리므로, 변경 코드를 별도 루트(v5root)의 src에 두고 그 루트에서 실행한다.
% 원본 v4 폴더는 수정하지 않는다. 회귀 확인(V5B_SCORER_REF가 기존 결과와 같아야 함)과 det3(V5B_DET3)를 실행한다. 학습 없음.
clear functions; here = fileparts(mfilename('fullpath'));
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\v5root';
assert(isfolder(root), 'v5root 없음');
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests'));
w = which('selector_step'); assert(startsWith(w, root), 'selector_step이 v5root가 아님: %s', w); disp(w);
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
man = read_manifest(fullfile(pc_root(), cfg.paths.record_manifest)); ev = unique(man.event_id, 'stable')';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
setappdata(0, 'det3_hits', 0);
runs = {'V5B_SCORER_REF', 'eval', {'R','J-AI'}; 'V5B_DET3', 'det3', {'J-AI'}};
for k = 1:size(runs, 1)
    if isfile(fullfile(root, 'results', ['control_metrics_record_' runs{k,1} out_tag() '.csv'])), fprintf('건너뜀: %s\n', runs{k,1}); continue; end
    opt = struct('cfg', cfg, 'models', mo, 'keep_series', false);
    if ~strcmp(runs{k,2}, 'eval'), opt.jpolicy = runs{k,2}; opt.explore_seed = 1; end
    t0 = tic; run_benchmarks(runs{k,1}, runs{k,3}, ev, opt); fprintf('V5B_DONE %s %.1f s\n', runs{k,1}, toc(t0));
end
disp('V5B_ALL_DONE');
end
