% COMPUTE_SCALES  목적함수 J의 고정 RMS 스케일 sx, sy, st (계획서 9절).
%  정의: config controller.scales_events 사건(예측기 학습용 실제 사건, 제어 개발 사건 El Centro·포항·고베 제외)의
%        R 응답 최상층 RMS를 기록 → 사건 평균 → 사건 동일 가중 평균.
%  시험 사건의 U나 미래 최대값은 쓰지 않는다. 결과: config/scales.json (한 번 만들면 동결; 덮어쓰려면 파일을 직접 지운다)
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
out = fullfile(root, cfg.controller.scales_file);
if exist(out, 'file'), error('compute_scales: %s 이미 있음 (동결). 다시 만들려면 이유를 report/progress.md에 적고 삭제', out); end
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
evs = cfg.controller.scales_events;
cfg.latency.timing_mode = 'nominal';   % 고정 정규화 상수: 계산시간을 시간축에 넣지 않는 정의 (verify_scales와 같음)
M = pc_method(cfg, 'R', struct('select_s', 0));
E = zeros(numel(evs), 3); nrec = zeros(numel(evs), 1); ids = {};
for e = 1:numel(evs)
    k = find(strcmp(man.event_id, evs{e}));
    acc = zeros(numel(k), 3);
    for j = 1:numel(k)
        [ax, ay] = load_record(cfg, man.record_id{k(j)}, cfg.plant.dt);
        o = run_closed_loop(ax, ay, cfg, M, struct('dt', cfg.plant.dt, 'record_id', man.record_id{k(j)}));
        acc(j,:) = [sqrt(mean(o.ux.^2)), sqrt(mean(o.uy.^2)), sqrt(mean(o.th.^2))];
        ids{end+1} = man.record_id{k(j)}; %#ok<SAGROW>
        fprintf('%s %s  rms = %.4e %.4e %.4e\n', evs{e}, man.record_id{k(j)}, acc(j,:));
    end
    E(e,:) = mean(acc, 1); nrec(e) = numel(k);
end
s = mean(E, 1);
sc = struct('sx', s(1), 'sy', s(2), 'st', s(3), 'events', {evs}, 'records', {ids}, 'n_records_per_event', nrec, ...
            'method', 'R, dt=cfg.plant.dt, timing nominal, 계산 지연 0', 'env', env_string(), 'created', datestr(now, 31));
fid = fopen(out, 'w'); fprintf(fid, '%s', jsonencode(sc)); fclose(fid);
fprintf('scales: sx=%.4e sy=%.4e st=%.4e  → %s\n', s, out);
