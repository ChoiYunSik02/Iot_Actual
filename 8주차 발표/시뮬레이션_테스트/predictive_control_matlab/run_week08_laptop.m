function run_week08_laptop(stages)
% RUN_WEEK08_LAPTOP  노트북 MATLAB에서 계획서 13절 단계를 순서대로 실행한다. 단계가 실패하면 멈춘다.
%  사용:  cd predictive_control_matlab;  run_week08_laptop        % A → B → SL(Simulink 대조) → C → D 진단
%         run_week08_laptop({'D'})                                 % A·B·SL·C 관문이 통과·같은 코드일 때만 실행
%         run_week08_laptop({'T', 'D2'})                           % PyTorch smoke 연결 시험 → D 2차 진단·통합 표
%         run_week08_laptop({'P', 'F8'})                           % 8주차 소규모 AI 학습 → 최종 폐루프 비교
%         run_week08_laptop({'JB', 'JT', 'JS', 'JC'})                % 8주차 v2: 예산 → teacher → 점수망 → 공동 선택 비교
%         run_week08_laptop({'RP'})                                % 재현성 진단 (완전 고정 2회, d_cmd 50/51, 실측 지연 5회)
%         (E·F 학습, G·H는 현재 보류. 실행하려면 run_week08_laptop({'E'}) 등으로 명시)
%  관문: 각 단계 결과를 results/gate_<단계>.json에 실행 브랜치·커밋·코드 digest와 함께 기록한다.
%        D 이후 단계는 gate('require', {'A','B','SL','C'})를 통과해야 시작한다 (MATLAB 실행, 같은 코드, 설정 변경은 CHANGELOG 기록).
%  기록: report/progress_laptop.md (실행·미실행·소요 시간·결과 파일)
%  주의: 결과가 나쁘다는 이유로 시험 사건·시드·지표·허용 악화폭을 바꾸지 않는다 (계획서 0절).
if nargin < 1, stages = {'A', 'B', 'SL', 'C', 'D'}; end
root = fileparts(mfilename('fullpath'));
addpath(fullfile(root, 'src'), fullfile(root, 'src', 'sl'), fullfile(root, 'scripts'), fullfile(root, 'tests'));
cfg = pc_config();
logf = fullfile(root, 'report', 'progress_laptop.md');
if exist('OCTAVE_VERSION', 'builtin') > 0, error('run_week08_laptop: 노트북 MATLAB 전용 (클라우드 Octave 예비 점검은 tests/·diagnose_D(allow_prelim))'); end
pv = run_provenance();
note(logf, sprintf('\n## 실행 %s — %s, 단계 %s\n', datestr(now, 31), env_string(), strjoin(stages, ',')));
note(logf, sprintf('- 브랜치 `%s`, 커밋 `%s`, 작업트리 변경 %s, 코드 digest `%s`, 설정 `%s`', pv.branch, pv.commit, mat2str(pv.dirty), pv.digest, pv.config_hash));
dev = cfg.data.dev_events_control;
models = struct('var', fullfile(root, 'models', 'var_pilot.mat'), 'lstm', fullfile(root, 'models', 'forecaster_selected.mat'));
for s = 1:numel(stages)
    t0 = tic;
    try
        switch stages{s}
            case 'A'
                E = check_environment();
                verify_scales(root, cfg);
                fb = E.blockers(strncmp(E.blockers, '파일 없음', 5));
                if ~isempty(fb), error('A: %s', strjoin(fb, ' / ')); end
                if ~isempty(E.blockers), note(logf, ['- A 참고(다음 관문에서 판정): ' strjoin(E.blockers, ' / ')]); end
                gate('pass', 'A', struct('environment', 'logs/environment.json', 'scales_verified', true));
            case 'B'
                r = test_stage_B();
                if ~r.pass, gate('fail', 'B', 'results/stage_B_check.csv'); error('B: 기준 재현 실패 → results/stage_B_check.csv'); end
                gate('pass', 'B', struct('evidence', 'results/stage_B_check.csv'));
            case 'SL'
                if ~has_product('Simulink')
                    gate('fail', 'SL', 'Simulink 없음'); error('SL: Simulink 없음 → Simulink 대조 불가, D로 넘어가지 않음');
                end
                build_simulink(cfg.plant.dt);
                r = test_simulink_vs_engine();
                if ~r.pass, gate('fail', 'SL', 'results/simulink_check.csv'); error('SL: Simulink 대 스텝 엔진 불일치 → results/simulink_check.csv'); end
                gate('pass', 'SL', struct('evidence', 'results/simulink_check.csv', 'model', 'models/rs_tlcd_predictive_control.slx'));
            case 'C'
                r = test_stage_C();
                if ~r.pass, gate('fail', 'C', 'results/stage_C_check.csv'); error('C: 지연·큐·인과성 시험 실패 → results/stage_C_check.csv'); end
                gate('pass', 'C', struct('evidence', 'results/stage_C_check.csv'));
            case 'D'
                gate('require', {'A', 'B', 'SL', 'C'});
                % 선택 계산과 예측 갱신 계산을 따로 잰다 (워밍업 후 p95 → 계산 지연 설정)
                measure_runtime('ElCentro_1940', {'R', 'select_C1', 'select_C2', 'forecast_zero', 'forecast_persistence', 'forecast_preview', 'forecast_lstm_untrained'});
                diagnose_D();
            case 'T'                                  % PyTorch smoke 학습·추론 연결 시험 (정식 pilot 아님)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_torch_smoke();
            case 'D2'                                 % 후보 집합·R 후보 대 R·구간 끝 잔여 진동 진단 + 통합 표
                gate('require', {'A', 'B', 'SL', 'C'});
                diagnose_D2();
            case 'RP'                                 % 재현성 진단: 완전 고정 2회 → d_cmd 50/51 → 실측 지연 5회 (현행 ±15°)
                gate('require', {'A', 'B', 'SL', 'C'});
                diagnose_RP();
            case 'P'                                  % 8주차 AI 학습 필수 시드 8401 (PyTorch)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_ai_pilot();
            case 'P2'                                 % 같은 설정의 추가 시드 8402·8403 (시간 여유가 있을 때만, 성능 보고 고르지 않음)
                gate('require', {'A', 'B', 'SL', 'C'});
                c_ = pc_config(); for sd_ = c_.lstm.pilot8_extra_seeds(:)', run_ai_pilot(sd_); end
            case 'F8'                                 % 8주차 폐루프 비교 (주 구조: 원래 R 경로 + 그림자 R + 절대 각도, 개발 3사건)
                gate('require', {'A', 'B', 'SL', 'C'});
                c_ = pc_config(); sm_ = {};               % 추가 시드 모델이 있으면 AI만 같은 조건으로 함께 보고 (고르지 않음)
                for sd_ = c_.lstm.pilot8_extra_seeds(:)'
                    f_ = fullfile(root, 'models', sprintf('torch_pilot8_seed%d', sd_));
                    if exist([f_ '_weights.mat'], 'file'), sm_{end+1} = f_; end %#ok<AGROW>
                end
                run_final8(struct('seed_models', {sm_}));
            case 'F8R'                                % F8 폐루프는 끝났고 내보내기·보고서만 다시 (저장 결과 재사용)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_final8(struct('reuse', true));
            case 'F8X'                                % 같은 설정으로 기존 11개 기록 전체 (계산시간이 허락할 때만)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_final8(struct('events', 'all'));
            case 'JB'                                 % 8주차 v2: J-AI 지속 부하 선택 예산 (점수망 학습 전, 결과 보기 전)
                gate('require', {'A', 'B', 'SL', 'C'});
                measure_joint_budget();
            case {'JT', 'JS'}                         % teacher 생성(처리량 측정 → 8/4 상태 결정 → 80/20 기록) / 점수망 학습·MATLAB 대조
                gate('require', {'A', 'B', 'SL', 'C'});
                run_joint_scorer(stages{s});
            case 'JC'                                 % 공동 선택 비교 (개발 3사건, 고정 시간축 + J-AI 실측 지연)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_joint_comparison();
            case 'PR'                                 % v3: 원문 재현 조건(지연 0) 무제어·원 제어 R, 11개 기록, dt 0.01·0.005
                gate('require', {'A', 'B', 'SL', 'C'});
                run_paper_repro();
            case 'JCA'                                % v3: 같은 설정 J-AI 실측 지연 (R·J-AI), 11개 기록 — 고정 시간축 결과는 JCX 재사용
                gate('require', {'A', 'B', 'SL', 'C'});
                run_joint_comparison(struct('events', 'all', 'fixed', false, 'actual', true, 'methods', {{'R', 'J-AI'}}, 'label', '_actualall'));
            case 'JCX'                                % 같은 설정으로 기존 11개 기록 전체 (계산시간이 허락할 때만)
                gate('require', {'A', 'B', 'SL', 'C'});
                run_joint_comparison(struct('events', 'all', 'actual', false));
            case 'E'
                gate('require', {'A', 'B', 'SL', 'C'});
                run_smoke_test();
            case 'F'
                gate('require', {'A', 'B', 'SL', 'C'});
                build_forecast_dataset('pilot');
                for sd = cfg.lstm.pilot_seeds(:)', train_forecaster('pilot', sd); end
                select_forecaster('pilot');
                fit_var_baseline('pilot');
                evaluate_forecasts('pilot', {'zero', 'persistence', 'var', 'lstm'});
                measure_runtime('ElCentro_1940', {'forecast_var', 'forecast_lstm'});
                freeze_config(root);
                run_benchmarks('F_pilot', {'R', 'FIX', 'SIMPLE-zero', 'SIMPLE-persistence', 'SIMPLE-var', 'AI-C1', 'AI-ideal-C1', 'PREVIEW-C1'}, dev, struct('models', models));
                for sd = cfg.lstm.pilot_seeds(:)'       % 세 시드의 제어 결과 분포 (시드 선택에는 쓰지 않음)
                    mf = struct('lstm', fullfile(root, 'checkpoints', sprintf('net_pilot_seed%d.mat', sd)));
                    run_benchmarks(sprintf('F_seed%d', sd), {'R', 'AI-C1'}, dev, struct('models', mf));
                end
                for x = cfg.latency.extra_info_sweep_s(:)'   % 추가 정보처리 지연 민감도
                    run_benchmarks(sprintf('F_extra%.1f', x), {'R', 'SIMPLE-var', 'AI-C1'}, dev, struct('models', models, 'override', struct('extra_info_s', x)));
                end
                cfg = pc_config(); L = cfg.latency.compute_s; fs = max([L.forecast_var, L.forecast_lstm]);   % 공통 지연을 맞춘 보조 비교 (실측값 다시 읽음)
                run_benchmarks('F_matched', {'R', 'SIMPLE-var', 'AI-C1'}, dev, struct('models', models, 'override', struct('forecast_s', fs)));
            case 'G'
                run_benchmarks('G_C2', {'R', 'AI-C1', 'AI-C2', 'PREVIEW-C2'}, dev, struct('models', models));
                note(logf, '- G: 센서 기반 상태추정(관측기)은 미구현 — 이상적 상태정보 조건 결과만');
            case 'H'
                run_benchmarks('H_dt0.005_dev', {'R', 'AI-C1'}, dev, struct('models', models, 'dt', cfg.plant.dt_check));
                evaluate_test();
            otherwise
                error('모르는 단계 %s', stages{s});
        end
        note(logf, sprintf('- %s 완료 (%.0f s)', stages{s}, toc(t0)));
    catch err
        note(logf, sprintf('- %s **실패** (%.0f s): %s', stages{s}, toc(t0), err.message));
        rep = error_report(err);                          % 하위 원인(cause)까지 모두 펼침
        ef = fullfile(root, 'logs', sprintf('error_%s.txt', stages{s}));
        fid = fopen(ef, 'w'); fprintf(fid, '%s\n', rep); fclose(fid);
        fprintf(2, '단계 %s 실패 — 상세 원인:\n%s\n(저장: %s)\n', stages{s}, rep, ef);
        return;
    end
end
fprintf('완료: %s\n', strjoin(stages, ','));
end

function rep = error_report(err, depth)
% 오류와 모든 하위 원인(Simulink MultipleErrors 포함)을 들여쓰기로 펼친다
if nargin < 2, depth = 0; end
pad = repmat('  ', 1, depth);
try
    r = getReport(err, 'extended', 'hyperlinks', 'off');
catch
    r = err.message;
end
rep = sprintf('%s[%s] %s', pad, err.identifier, strrep(r, newline, [newline pad]));
for k = 1:numel(err.cause)
    rep = sprintf('%s\n%s--- 원인 %d ---\n%s', rep, pad, k, error_report(err.cause{k}, depth + 1));
end
end

function note(f, s)
fid = fopen(f, 'a'); fprintf(fid, '%s\n', s); fclose(fid); fprintf('%s\n', s);
end

function verify_scales(root, cfg)
% Octave에서 만든 config/scales.json을 MATLAB으로 다시 계산해 같은지 확인 (상대 1e-9)
sc = jsondecode(fileread(fullfile(root, cfg.controller.scales_file)));
cfg.latency.timing_mode = 'nominal';            % 스케일은 고정 정규화 상수: compute_scales와 같은 nominal·계산 지연 0 정의
M = pc_method(cfg, 'R', struct('select_s', 0));
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
E = zeros(numel(sc.events), 3);
for e = 1:numel(sc.events)
    k = find(strcmp(man.event_id, sc.events{e})); acc = zeros(numel(k), 3);
    for j = 1:numel(k)
        [ax, ay] = load_record(cfg, man.record_id{k(j)}, cfg.plant.dt);
        o = run_closed_loop(ax, ay, cfg, M, struct('dt', cfg.plant.dt));
        acc(j,:) = [sqrt(mean(o.ux.^2)), sqrt(mean(o.uy.^2)), sqrt(mean(o.th.^2))];
    end
    E(e,:) = mean(acc, 1);
end
s = mean(E, 1); d = max(abs(s - [sc.sx sc.sy sc.st])./[sc.sx sc.sy sc.st]);
fprintf('scales.json 재계산 상대차 %.2e\n', d);
assert(d <= 1e-9, 'scales.json이 MATLAB 재계산과 다름 (%.2e)', d);
end

function freeze_config(root)
% AI 제어 비교 전에 설정·실측 지연·스케일을 config/frozen/에 동결 (이미 있으면 같은지만 확인)
fz = fullfile(root, 'config', 'frozen'); if ~exist(fz, 'dir'), mkdir(fz); end
fs = {'experiment.json', 'latency_measured.json', 'scales.json'};
for k = 1:numel(fs)
    a = fullfile(root, 'config', fs{k}); b = fullfile(fz, fs{k});
    if exist(b, 'file')
        assert(strcmp(fileread(a), fileread(b)), '동결 뒤 설정이 바뀜: %s (바꿨다면 이유를 기록하고 새 버전으로)', fs{k});
    else
        copyfile(a, b);
    end
end
fid = fopen(fullfile(fz, 'FROZEN.txt'), 'w'); fprintf(fid, '%s %s\n', datestr(now, 31), env_string()); fclose(fid);
end
