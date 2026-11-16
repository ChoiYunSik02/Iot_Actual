function recheck3_det3()
% 진단 3: 어떤 selector_step이 호출되는지, j_decide에 어떤 정책 값이 들어오는지, det3 분기에 도달하면 오류로 표시. 25 s 기능 점검용.
clear functions; here = fileparts(mfilename('fullpath'));
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\predictive_control_matlab';
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests')); addpath(fullfile(here,'override_dbg3'));
w = which('selector_step', '-all'); disp(w{1});
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
opt = struct('cfg', cfg, 'models', mo, 'keep_series', false, 'max_seconds', 25, 'jpolicy', 'det3', 'explore_seed', 1);
try
    run_benchmarks('V5_DBG3', {'J-AI'}, {'Kobe1995'}, opt);
    disp('RESULT: 오류 없이 완료 (det3 분기에 도달하지 않음)');
catch ME
    fprintf('RESULT: 오류 발생 -> %s\n', ME.message);
    for k = 1:min(4, numel(ME.stack)), fprintf('   %s (line %d) in %s\n', ME.stack(k).name, ME.stack(k).line, ME.stack(k).file); end
end
disp('RECHECK3_DONE');
end
