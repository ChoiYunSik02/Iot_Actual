function D = build_forecast_dataset(stage)
% BUILD_FORECAST_DATASET  미래 파형 예측 학습 자료 (계획서 7절). 구조 시뮬레이션은 하지 않는다.
%  stage : 'smoke' (합성 200 = 160/40) | 'pilot' (합성 1,000 = 800/200 + 학습 지정 실제 사건)
%  입력 X : 3 x 500 (정규화 X, 정규화 Y, 마스크) — 온라인과 같은 make_window·forecast_input
%  정답 Y : 800 = 정규화 미래 4 s [X(1..400); Y(1..400)]
%  분할 : 원본(합성 생성 시드 / 실제 사건)을 먼저 train/val로 나눈 뒤 창을 만든다. 같은 사건 기록은 같은 분할.
%  정규화 : train 분할 원본의 트리거 이후 유효 샘플로 성분별 평균·표준편차 (전체 자료 통계는 쓰지 않음)
%  창 : 트리거 + 1 s 이후, 0.2 s 격자, 미래 4 s가 기록 안에 있는 기준시각. 원본당 최대 100개(분할 시드로 추출).
%  smoke에서 실제 기록은 학습에 넣지 않고 분리 진단용(real_val)으로만 만든다.
%  결과 : data/forecast_dataset_<stage>.mat, data/split_manifest_<stage>.csv
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
sc = cfg.data.(stage);
dt = 0.01; r = 1; Wn = round(cfg.forecast.window_s*100); Hn = round(cfg.forecast.horizon_s*100);
nupd = round(cfg.forecast.update_period_s/dt); n_first = round(cfg.forecast.first_after_trigger_s/dt);
% ---- 원본 목록과 분할 (창 만들기 전에 고정) ----
seeds = sc.seed0 + (0:sc.n_sources-1);
rng(cfg.data.split_seed, 'twister');
perm = randperm(sc.n_sources);
is_tr = false(1, sc.n_sources); is_tr(perm(1:sc.n_train)) = true;
src = struct('id', {}, 'kind', {}, 'event', {}, 'split', {}, 'x', {}, 'y', {}, 'scale', {});
for k = 1:sc.n_sources
    [x, y, meta] = gen_synthetic(seeds(k), dt);
    [x, y, s] = normalize_track(x, y, cfg, seeds(k));
    if is_tr(k), sp = 'train'; else, sp = 'val'; end
    src(end+1) = struct('id', sprintf('syn%05d', seeds(k)), 'kind', 'synthetic', 'event', sprintf('syn%05d', seeds(k)), ...
                        'split', sp, 'x', x, 'y', y, 'scale', s); %#ok<AGROW>
end
man = read_manifest(fullfile(root, cfg.paths.record_manifest));
for k = 1:numel(man.record_id)
    ev = man.event_id{k};
    if any(strcmp(ev, cfg.data.test_events)), continue; end          % 시험 사건은 절대 읽지 않음
    if any(strcmp(ev, cfg.data.real_train_events))
        if strcmp(stage, 'smoke'), sp = 'real_diag'; else, sp = 'train'; end
    elseif any(strcmp(ev, cfg.data.real_val_events))
        sp = 'real_val';
    else
        continue;
    end
    [x, y] = load_record(cfg, man.record_id{k}, dt);
    src(end+1) = struct('id', man.record_id{k}, 'kind', 'real', 'event', ev, 'split', sp, 'x', x, 'y', y, 'scale', 1); %#ok<AGROW>
end
% ---- train 분할 scaler ----
vx = []; vy = [];
for k = 1:numel(src)
    if ~strcmp(src(k).split, 'train'), continue; end
    tg = trig100(src(k).x, src(k).y, cfg.sensor.trigger_mps2);
    if tg < 0, continue; end
    vx = [vx; src(k).x(tg+1:end)]; vy = [vy; src(k).y(tg+1:end)]; %#ok<AGROW>
end
scaler = struct('mu', [mean(vx), mean(vy)], 'sd', [std(vx), std(vy)], 'source', 'train 분할, 트리거 이후 유효 샘플');
clear vx vy
% ---- 창 ----
splits = {'train', 'val', 'real_val', 'real_diag'};
for s = 1:numel(splits), C.(splits{s}) = struct('X', {{}}, 'Y', {{}}, 'src', {{}}, 'origin', {{}}); end
nwin = zeros(numel(src), 1);
for k = 1:numel(src)
    x = src(k).x; y = src(k).y; n = numel(x);
    tg = trig100(x, y, cfg.sensor.trigger_mps2);
    if tg < 0, continue; end
    q0 = ceil((tg + n_first)/nupd)*nupd;                 % 0.2 s 격자
    qs = q0:nupd:(n - 1 - Hn);
    if isempty(qs), continue; end
    if numel(qs) > sc.max_windows_per_source
        rng(cfg.data.split_seed + k, 'twister');
        qs = sort(qs(randperm(numel(qs), sc.max_windows_per_source)));
    end
    Xk = zeros(3, Wn, numel(qs), 'single'); Yk = zeros(2*Hn, numel(qs), 'single');
    for j = 1:numel(qs)
        [wx, wy, mk] = make_window(x, y, qs(j), tg, r, Wn);
        Xk(:,:,j) = single(forecast_input(wx, wy, mk, scaler));
        Yk(:,j) = single(pack_forecast_target(x(qs(j)+2:qs(j)+Hn+1), y(qs(j)+2:qs(j)+Hn+1), scaler));
    end
    sp = src(k).split; nwin(k) = numel(qs);
    C.(sp).X{end+1} = Xk; C.(sp).Y{end+1} = Yk; C.(sp).src{end+1} = repmat(k, numel(qs), 1); C.(sp).origin{end+1} = qs(:);
end
for s = 1:numel(splits)
    c = C.(splits{s});
    W.(splits{s}) = struct('X', cat(3, zeros(3, Wn, 0, 'single'), c.X{:}), 'Y', cat(2, zeros(2*Hn, 0, 'single'), c.Y{:}), ...
                           'src', cat(1, zeros(0,1), c.src{:}), 'origin', cat(1, zeros(0,1), c.origin{:}));
end
clear C
% ---- 실제 자료 가중 (학습 미니배치가 합성만으로 채워지지 않게, 복제 배수 기록) ----
rep = 1;
if strcmp(stage, 'pilot')
    isreal_tr = arrayfun(@(k) strcmp(src(k).kind, 'real'), W.train.src);
    nr = sum(isreal_tr); ns = sum(~isreal_tr); f = cfg.data.real_weight_fraction;
    if nr > 0 && nr/(nr + ns) < f
        rep = ceil(f/(1 - f)*ns/nr);
        idx = [find(~isreal_tr); repmat(find(isreal_tr), rep, 1)];
        W.train.X = W.train.X(:,:,idx); W.train.Y = W.train.Y(:,idx); W.train.src = W.train.src(idx); W.train.origin = W.train.origin(idx);
    end
    if size(W.train.X, 3) > sc.max_windows_total, error('창 수 %d > 상한 %d', size(W.train.X,3), sc.max_windows_total); end
end
D = struct('stage', stage, 'W', W, 'scaler', scaler, 'Wn', Wn, 'Hn', Hn, 'dt', dt, 'real_rep', rep, ...
           'sources', rmfield(src, {'x', 'y'}), 'n_windows_per_source', nwin, 'env', env_string(), ...
           'created', datestr(now, 31), 'cfg_data', cfg.data, 'order', 'X: [zX; zY; mask] x 500 시간, Y: [zX(1..400); zY(1..400)]');
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if isoct, tag = '_octave'; else, tag = ''; end          % Octave 예비 자료(난수 생성기 다름)는 이름을 구분해 학습에 섞이지 않게 함
out = fullfile(root, 'data', ['forecast_dataset_' stage tag '.mat']);
if isoct, save(out, '-struct', 'D', '-v7'); else, save(out, '-struct', 'D', '-v7.3'); end
fid = fopen(fullfile(root, 'data', ['split_manifest_' stage tag '.csv']), 'w');
fprintf(fid, 'source_id,kind,event_id,split,pga_scale,n_windows\n');
for k = 1:numel(src)
    fprintf(fid, '%s,%s,%s,%s,%g,%d\n', src(k).id, src(k).kind, src(k).event, src(k).split, src(k).scale, nwin(k));
end
fclose(fid);
fprintf('%s: train %d, val %d, real_val %d, real_diag %d 창 (실제 복제 x%d) → %s\n', stage, size(W.train.X,3), size(W.val.X,3), ...
        size(W.real_val.X,3), size(W.real_diag.X,3), rep, out);
end

function tg = trig100(x, y, thr)
tg = find(max(abs(x), abs(y)) > thr, 1) - 1;
if isempty(tg), tg = -1; end
end

function [x, y, s] = normalize_track(x, y, cfg, seed)
% 일정 PGA 트랙(7주차 재현): 성분별 최대 0.35 m/s². 변동 세기 트랙: 같은 정규화 뒤 0.5/1/2배 중 하나(시드 기반).
x = x/max(abs(x))*cfg.data.pga_const_mps2; y = y/max(abs(y))*cfg.data.pga_const_mps2; s = 1;
if strcmp(cfg.data.pga_track, 'variable')
    lv = cfg.data.pga_scales_variable; s = lv(mod(seed, numel(lv)) + 1);
    x = x*s; y = y*s;
end
end
