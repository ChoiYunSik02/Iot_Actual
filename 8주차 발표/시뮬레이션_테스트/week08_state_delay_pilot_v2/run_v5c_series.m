function run_v5c_series()
% 시계열 저장용 재실행 (그림용). 학습 없음, 성능 탐색 없음. V5B_SCORER_REF와 같은 코드(v5root)·가중치·설정·입력을 쓰고
% opt.keep_series=true만 켠다. 사건은 ImperialValley1979(PEER01·02·03·04·11, PEER02·PEER11 포함)만 실행한다.
% 결과: v5root/results/benchmarks_V5C_SERIES.mat, control_metrics_record_V5C_SERIES.csv (V5B_SCORER_REF와 같아야 함),
%       v5root/results/series_V5C_<record>.csv (시간, 방법별 X·Y 변위와 비틀림각)
clear functions;
root = 'C:\Users\cys\Desktop\건물제진능동\ai_improvement_v4\v5root';
assert(isfolder(root), 'v5root 없음');
cd(root); addpath(fullfile(root,'src'), fullfile(root,'scripts'), fullfile(root,'tests'));
cfg = joint_timeline(pc_config(), [.27 .22]); cfg.controller.J.lookahead_policy = 'one_action_R';
mo = struct('lstmnat', fullfile(pc_root(),'models','torch_pilot8_seed8401'), 'scorer', fullfile(pc_root(),'models','joint_scorer_seed8401'));
opt = struct('cfg', cfg, 'models', mo, 'keep_series', true);
t0 = tic; out = run_benchmarks('V5C_SERIES', {'R','J-AI'}, {'ImperialValley1979'}, opt); fprintf('V5C_RUN %.1f s\n', toc(t0));
dt = cfg.plant.dt; S = out.series; ids = unique({S.record_id}, 'stable');
for i = 1:numel(ids)
    hdr = 'time_s'; cols = []; n = [];
    for m = {'U','R','J-AI'}
        k = find(strcmp({S.record_id}, ids{i}) & strcmp({S.method}, m{1}), 1);
        d = [S(k).ux(:), S(k).uy(:), S(k).th(:)]; cols = [cols, d]; n = size(d,1); %#ok<AGROW>
        mm = strrep(m{1}, '-', '');
        hdr = [hdr, sprintf(',%s_ux,%s_uy,%s_th', mm, mm, mm)]; %#ok<AGROW>
    end
    A = [(0:n-1)'*dt, cols];
    fn = fullfile(root, 'results', ['series_V5C_' ids{i} '.csv']);
    fid = fopen(fn, 'w'); fprintf(fid, '%s\n', hdr); fclose(fid); dlmwrite(fn, A, '-append', 'precision', 10);
    fprintf('SERIES_WRITTEN %s n=%d dt=%g\n', ids{i}, n, dt);
end
disp('V5C_ALL_DONE');
end
