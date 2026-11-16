function recheck2_det3()
% 진단 2: det3 정책 문자열이 selector_step의 분기에 도달하는지 직접 출력. 기록 25 s까지만(기능 점검용, 결과 해석에 쓰지 않음).
clear functions; here = fileparts(mfilename('fullpath'));
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\predictive_control_matlab';
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests')); addpath(fullfile(here,'override_dbg2'));
w = which('selector_step', '-all'); disp(w{1});
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
for pol = {'det3', 'rand3', 'eval'}
    fprintf('=== policy %s ===\n', pol{1});
    clear selector_step;
    opt = struct('cfg', cfg, 'models', mo, 'keep_series', false, 'max_seconds', 25);
    if ~strcmp(pol{1}, 'eval'), opt.jpolicy = pol{1}; opt.explore_seed = 8401; end
    run_benchmarks(['V5_DBG2_' pol{1}], {'J-AI'}, {'Kobe1995'}, opt);
end
disp('RECHECK2_DONE');
end
