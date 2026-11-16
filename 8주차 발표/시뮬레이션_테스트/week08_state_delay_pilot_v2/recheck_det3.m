function recheck_det3()
% 진단: V5_DET3 결과가 점수망과 완전히 같은 이유 확인. 함수 캐시를 비우고 det3 분기 실행 횟수를 센다. 기존 결과는 건드리지 않는다(태그 V5_DET3_DBG).
clear functions; clear classes;
here = fileparts(mfilename('fullpath'));
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\predictive_control_matlab';
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests'));
addpath(fullfile(here,'override_dbg'));
w = which('selector_step', '-all'); disp(w); assert(contains(w{1}, 'override_dbg'));
setappdata(0, 'det3_hits', 0);
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
man = read_manifest(fullfile(pc_root(), cfg.paths.record_manifest)); ev = unique(man.event_id, 'stable')';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
opt = struct('cfg', cfg, 'models', mo, 'keep_series', false, 'jpolicy', 'det3', 'explore_seed', 1);
run_benchmarks('V5_DET3_DBG', {'J-AI'}, ev, opt);
fprintf('DET3_BRANCH_HITS=%d\n', getappdata(0, 'det3_hits'));
disp('RECHECK_DONE');
end
