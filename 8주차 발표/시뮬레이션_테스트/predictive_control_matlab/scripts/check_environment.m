function E = check_environment()
% CHECK_ENVIRONMENT  계획서 3절 / 13절 A: 실제 실행 환경 기록 (버전을 가정하지 않는다).
%  기록: version, ver, 라이선스(Simulink, Deep Learning, MPC, Parallel), GPU, 메모리, 필수 파일·해시.
%  결과: logs/environment<tag>.json, 화면 요약. 필수 조건 미충족은 E.blockers에 적는다.
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
E = struct('env', env_string(), 'time', datestr(now, 31), 'computer', computer, 'blockers', {{}}, 'notes', {{}});
E.provenance = run_provenance();
if isoct
    E.version = OCTAVE_VERSION; E.products = {};
    E.blockers{end+1} = 'Octave: Simulink·Deep Learning Toolbox 없음 — 예비 점검 전용';
else
    E.version = version; v = ver; E.products = {v.Name};
    lic = {'Simulink', 'Simulink'; 'Neural_Network_Toolbox', 'Deep Learning Toolbox'; ...
           'MPC_Toolbox', 'Model Predictive Control Toolbox'; 'Distrib_Computing_Toolbox', 'Parallel Computing Toolbox'};
    for k = 1:size(lic, 1)
        has = license('test', lic{k,1}) && any(strcmp(E.products, lic{k,2}));
        E.(['has_' strrep(lower(lic{k,2}), ' ', '_')]) = has;
    end
    if ~E.has_simulink, E.blockers{end+1} = 'Simulink 없음 — B·C의 Simulink 대조 불가 (MATLAB 스텝 엔진만)'; end
    if ~E.has_deep_learning_toolbox, E.notes{end+1} = 'Deep Learning Toolbox 없음 — E·F LSTM 단계 미충족(현재 보류), A~D에는 영향 없음'; end
    E.gpu = false;
    try
        if exist('canUseGPU', 'file') && canUseGPU, g = gpuDevice; E.gpu = true; E.gpu_name = g.Name; E.gpu_mem_gb = g.AvailableMemory/2^30; end
    catch err
        E.notes{end+1} = ['GPU 확인 실패: ' err.message];
    end
    try
        [~, sys] = memory; E.mem_total_gb = sys.PhysicalMemory.Total/2^30; E.mem_avail_gb = sys.PhysicalMemory.Available/2^30;
    catch
        E.notes{end+1} = 'memory() 미지원 (Windows 외)';
    end
    E.n_cores = feature('numcores');
end
% 필수 파일
need = {cfg.paths.reference_engine, cfg.paths.validation_ref, cfg.paths.record_manifest, cfg.controller.scales_file};
E.files = struct('path', need, 'exists', false, 'sha16', '');
for k = 1:numel(need)
    p = fullfile(root, need{k}); E.files(k).exists = exist(p, 'file') > 0;
    if E.files(k).exists
        h = code_hash_one(p); E.files(k).sha16 = h;
    else
        E.blockers{end+1} = ['파일 없음: ' need{k}];
    end
end
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
E.n_records = numel(man.record_id); E.n_events = numel(unique(man.event_id));
E.test_events = cfg.data.test_events;
if isempty(cfg.data.test_events), E.notes{end+1} = '시험 사건 없음: 모든 결과는 개발 실험 (계획서 7절)'; end
f = fullfile(root, 'logs', ['environment' out_tag() '.json']);
fid = fopen(f, 'w'); fprintf(fid, '%s', jsonencode(E)); fclose(fid);
fprintf('환경: %s\n', E.env);
fprintf('  실행 브랜치 %s, 커밋 %s (작업트리 변경 %s), 코드 digest %s, 설정 %s\n', E.provenance.branch, E.provenance.commit, ...
        mat2str(E.provenance.dirty), E.provenance.digest, E.provenance.config_hash);
if ~isoct
    fprintf('  Simulink %d / Deep Learning %d / MPC %d / Parallel %d / GPU %d / 코어 %d\n', E.has_simulink, ...
            E.has_deep_learning_toolbox, E.has_model_predictive_control_toolbox, E.has_parallel_computing_toolbox, E.gpu, E.n_cores);
end
fprintf('  기록 %d개 / 사건 %d개, 시험 사건 %d개\n', E.n_records, E.n_events, numel(cfg.data.test_events));
for k = 1:numel(E.blockers), fprintf('  [미충족] %s\n', E.blockers{k}); end
for k = 1:numel(E.notes), fprintf('  [참고] %s\n', E.notes{k}); end
fprintf('  → %s\n', f);
end

function s = code_hash_one(p)
fid = fopen(p, 'r'); b = fread(fid, inf, '*uint8'); fclose(fid);
if exist('OCTAVE_VERSION', 'builtin') > 0
    s = hash('sha256', char(b'));
else
    md = java.security.MessageDigest.getInstance('SHA-256');
    s = lower(reshape(dec2hex(typecast(md.digest(b), 'uint8'), 2)', 1, []));
end
s = s(1:16);
end
