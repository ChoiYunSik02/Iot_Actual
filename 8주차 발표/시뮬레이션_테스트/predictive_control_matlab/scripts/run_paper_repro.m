function T = run_paper_repro(opt)
% RUN_PAPER_REPRO  v3 §5: 원문 동일 조건 재현용 무제어·원 제어 R (지연 0, 원문 갱신 주기)
%  재현 조건: 센서·통신·연산 지연 0, 결정 = 적용 스텝(d_cmd = 0), 진동수·각도 2.6 s, 밸브 1 s, 원문 식 10-13의 R 법칙. 한 스텝 엔진 R = rstlcd_sim.m (B 관문).
%  운영 비교용 R(예측 준비 1스텝·R 1스텝, JC 고정 시간축)은 results/control_metrics_record_JC_fixed_all.csv에 따로 있다. 두 R을 섞지 않는다.
%  기록: 기존 11개 전체(원문 공통 8쌍 + 개발 3개). dt 0.01(주), 0.005(민감도, 원문이 dt를 밝히지 않음).
%  결과: results/PR_records<tag>.csv (무제어·R 절대 응답: m, rad), 같은 파일을 week08_submission/paper_comparison/에 복사
if nargin < 1, opt = struct(); end
if ~isfield(opt, 'dts'), opt.dts = [0.01 0.005]; end
if ~isfield(opt, 'max_seconds'), opt.max_seconds = inf; end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'scripts'));
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if ~isoct, pv = gate('require', {'A', 'B', 'SL', 'C'}); else, pv = run_provenance(); end
cfg = pc_config(); cfg.latency.timing_mode = 'nominal'; cfg.latency.sensor_s = 0; cfg.latency.comm_s = 0; cfg.latency.extra_info_s = 0;
cfg.latency.inject_select_s = 0; cfg.latency.inject_forecast_s = 0;
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
tag = out_tag(); if isfinite(opt.max_seconds), tag = [tag '_trunc']; end
f = fopen(fullfile(root, 'results', ['PR_records' tag '.csv']), 'w');
fprintf(f, '# 원문 재현 조건(지연 0) 무제어·R 절대 응답. 단위: 변위 m, 비틀림 rad. RMS = 기록 전체(끝 0 구간 10 s 포함). env=%s commit=%s digest=%s\n', env_string(), pv.commit, pv.digest);
fprintf(f, 'record_id,event_id,dt,method,ux_max,ux_rms,uy_max,uy_rms,th_max,th_rms,n_steps,d_cmd\n');
for dt = opt.dts
    for k = 1:numel(man.record_id)
        rid = man.record_id{k};
        [ax, ay] = load_record(cfg, rid, dt);
        if isfinite(opt.max_seconds), n = min(numel(ax), round(opt.max_seconds/dt) + 1); ax = ax(1:n); ay = ay(1:n); end
        for q = {'U', 'R'}
            M = pc_method(cfg, q{1}, struct('select_s', 0));
            o = run_closed_loop(ax, ay, cfg, M, struct('dt', dt, 'record_id', rid));
            fprintf(f, '%s,%s,%g,%s,%.9e,%.9e,%.9e,%.9e,%.9e,%.9e,%d,%d\n', rid, man.event_id{k}, dt, q{1}, o.metrics, numel(ax), o.rt.d_cmd);
        end
        fprintf('PR dt=%g %-20s done\n', dt, rid);
    end
end
fclose(f);
% 사용한 checkpoint·기준 파일 hash (v3 §2: 어떤 가중치로 실행했는지 남김)
ck = {'models/torch_pilot8_seed8401.pt', 'models/torch_pilot8_seed8401_weights.mat', 'models/torch_pilot8_seed8401.json', 'models/joint_scorer_seed8401.pt', ...
      'models/joint_scorer_seed8401.json', 'config/scales.json', 'config/experiment.json', 'data/record_manifest.csv', 'data/joint_teacher.csv'};
H = struct('env', env_string(), 'commit', pv.commit, 'digest', pv.digest, 'files', struct());
for q = 1:numel(ck)
    fp = fullfile(root, ck{q}); nm = matlab.lang.makeValidName(ck{q});
    if exist(fp, 'file'), H.files.(nm) = struct('path', ck{q}, 'sha256_16', sha16(fp), 'bytes', dir(fp).bytes); else, H.files.(nm) = struct('path', ck{q}, 'sha256_16', '파일 없음', 'bytes', 0); end
end
fh = fopen(fullfile(root, 'results', ['checkpoint_hashes' tag '.json']), 'w'); fprintf(fh, '%s', jsonencode(H)); fclose(fh);
od = fullfile(root, 'week08_submission', 'paper_comparison'); if ~exist(od, 'dir'), mkdir(od); end
copyfile(fullfile(root, 'results', ['PR_records' tag '.csv']), fullfile(od, ['PR_records' tag '.csv']));
copyfile(fullfile(root, 'results', ['checkpoint_hashes' tag '.json']), fullfile(od, ['checkpoint_hashes' tag '.json']));
T = fullfile(od, ['PR_records' tag '.csv']);
fprintf('원문 재현 조건 무제어·R → %s\n', T);
end

function h = sha16(fp)
% 파일 SHA-256 앞 16자리 (MATLAB: java MessageDigest, Octave: hash)
fid = fopen(fp, 'r'); by = fread(fid, inf, 'uint8=>uint8'); fclose(fid);
if exist('OCTAVE_VERSION', 'builtin') > 0
    h = hash('sha256', char(by')); h = h(1:16);
else
    md = java.security.MessageDigest.getInstance('SHA-256'); md.update(by); d = typecast(md.digest(), 'uint8');
    h = lower(reshape(dec2hex(d, 2)', 1, [])); h = h(1:16);
end
end
