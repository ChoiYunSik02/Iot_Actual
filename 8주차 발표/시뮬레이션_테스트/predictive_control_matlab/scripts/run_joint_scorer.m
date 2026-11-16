function T = run_joint_scorer(stage)
% RUN_JOINT_SCORER  8주차 v2 teacher 생성(JT)과 공동 후보 점수망 학습(JS).
%  JT: 합성 기록 2개로 label 처리량을 먼저 재고, 100 기록 추정이 6 h를 넘으면 상태 수를 8 → 4로 한 번 줄인 뒤(성능 평가 전)
%      80/20 기록 전체 teacher 생성 → data/joint_teacher.csv. 결정은 results/joint_teacher_plan.json에 기록.
%  JS: python/train_joint_scorer.py (FC128-64-1, Huber, Adam 1e-3, batch 128, 최대 50 epoch, patience 5, seed 8401)
%      → models/joint_scorer_seed8401.{json,pt}, Python 대 MATLAB 추론 대조(≤ 1e-9), report/JS_scorer.md
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
cfg = pc_config(); js = cfg.joint_scorer;
fb = fullfile(root, 'results', ['joint_budget' out_tag() '.json']);
if ~exist(fb, 'file'), error('run_joint_scorer: %s 없음 (JB 먼저)', fb); end
jb = jsondecode(fileread(fb)); bud = jb.budget_s(:)';
switch stage
    case 'JT'
        t0 = tic;
        Tp = generate_joint_teacher(struct('budget', bud, 'n_records', 2, 'out', fullfile(root, 'data', 'joint_teacher_throughput')));
        st = js.teacher.states_per_record; reduced = false;
        if Tp.est_hours_100 > js.teacher.time_limit_h, st = 4; reduced = true; end
        plan = struct('throughput_sec_per_record', Tp.sec_per_record, 'est_hours_100_at_8', Tp.est_hours_100, 'states_per_record', st, ...
                      'reduced_8_to_4', reduced, 'rule', '추정 > 6 h면 성능 평가 전 상태 8 → 4 (계획 §6.3)', 'decided_at', datestr(now, 31), 'env', env_string());
        f = fopen(fullfile(root, 'results', 'joint_teacher_plan.json'), 'w'); fprintf(f, '%s', jsonencode(plan)); fclose(f);
        fprintf('처리량: 기록당 %.1f s → 100 기록 %.2f h → 기록당 상태 %d%s\n', Tp.sec_per_record, Tp.est_hours_100, st, ifs(reduced, ' (8 → 4 축소)', ''));
        T = generate_joint_teacher(struct('budget', bud, 'states', st, 'out', fullfile(root, 'data', 'joint_teacher')));
        T.plan = plan; T.wall_h = toc(t0)/3600;
    case 'JS'
        pe = pyenv;
        if strlength(pe.Executable) == 0, error('run_joint_scorer: Python 없음 — pyenv 지정'); end
        dat = fullfile(root, 'data', 'joint_teacher.csv');
        if ~exist(dat, 'file'), error('run_joint_scorer: %s 없음 (JT 먼저)', dat); end
        out = fullfile(root, 'models', sprintf('joint_scorer_seed%d', js.seed));
        lg = fullfile(root, 'logs', sprintf('joint_scorer_seed%d_train.log', js.seed));
        cmd = sprintf('"%s" "%s" --data "%s" --out "%s" --epochs %d --patience %d --batch %d --lr %g --seed %d --device cpu > "%s" 2>&1', pe.Executable, ...
                      fullfile(root, 'python', 'train_joint_scorer.py'), dat, out, js.max_epochs, js.patience, js.batch, js.lr, js.seed, lg);
        t0 = tic; s = system(cmd); tw = toc(t0);
        fprintf('%s', fileread(lg));
        if s ~= 0, error('run_joint_scorer: 학습 실패 (%s)', lg); end
        SC = load_scorer(out); J = jsondecode(fileread([out '.json']));
        Xp = J.parity_X; if isvector(Xp), Xp = Xp(:)'; end
        d = max(abs(rank_joint_candidates(SC, Xp) - J.parity_y(:)));
        fprintf('점수망 Python 대 MATLAB 추론 최대 차 %.2e (표본 %d)\n', d, size(Xp, 1));
        if d > 1e-9, error('run_joint_scorer: 추론 불일치 %.2e', d); end
        td = fullfile(root, 'week08_submission', 'training'); if ~exist(td, 'dir'), mkdir(td); end
        copyfile([out '.json'], td); copyfile(fullfile(root, 'data', 'joint_teacher_meta.json'), td);
        if exist(fullfile(root, 'results', 'joint_teacher_plan.json'), 'file'), copyfile(fullfile(root, 'results', 'joint_teacher_plan.json'), td); end
        m = J.metrics; pv = run_provenance();
        f = fopen(fullfile(root, 'report', 'JS_scorer.md'), 'w'); p = @(varargin) fprintf(f, varargin{:});
        p('# 공동 후보 점수망 학습 (8주차 v2, seed %d)\n\n', js.seed);
        p('- 실행: %s, 커밋 `%s`, digest `%s`. teacher `data/joint_teacher.csv` (sha16 `%s`)\n', pv.env, pv.commit, pv.digest, J.data_sha16);
        p('- 망 98 → 128 → 64 → 1, Huber, Adam %g, batch %d, 최대 %d epoch, patience %d. 종료 epoch %d (최저 검증 손실 %.5f), %.0f s\n', js.lr, js.batch, js.max_epochs, js.patience, J.best_epoch, J.val_loss, tw);
        p('- 목표 J_true/J_true(R) − 1 (실제 미래로 모의한 비인과 teacher). 제약 판정은 망이 아니라 물리 모델이 한다.\n');
        p('- 행 train %d / val %d, 상태 train %d / val %d. 자료 보강(정책 rollout 1회): 미실행\n', J.n_train_rows, J.n_val_rows, J.n_train_states, J.n_val_states);
        p('- Python 대 MATLAB 추론 최대 차 %.1e\n\n', d);
        p('| 분할 | top 3 적중 | 검사 집합(top3+유지+R) 최선 포함 | regret (J_R 대비) | fallback |\n|---|---|---|---|---|\n');
        for nm = {'train', 'train_random', 'val', 'val_random'}
            x = m.(nm{1}); p('| %s | %.3f | %.3f | %.4f | %.3f |\n', strrep(nm{1}, '_random', ' (무작위 3개)'), x.top3_hit, x.eval_hit, x.regret, x.fallback);
        end
        p('\n80/20 합성 기록 규모의 마감용 탐색 실험이며 일반화 검증이 아니다.\n');
        fclose(f);
        T = J; T.parity = d;
end
end

function s = ifs(c, a, b), if c, s = a; else, s = b; end, end
