function S = compute_scores(recs, methods, cfg)
% COMPUTE_SCORES  저감률·사건 집계·R 대비 효과량 (계획서 1·12절).
%  recs : struct 배열 (record_id, event_id, method, metrics(1x6), burden(1x3))
%  r(e,j,p) = 100(1 - response/response_U) → 사건 안 기록 평균 → 사건별 6지표 평균 → 사건 동일 가중 평균
%  ΔS = S_m - S_R (%p). 사건 단위 paired bootstrap(cfg.evaluation) 95% 구간 — 사건이 적으면 탐색적.
ids = {recs.record_id}; evs = {recs.event_id}; mt = {recs.method};
rid = unique(ids(strcmp(mt, 'U')));
ue = unique(evs(ismember(ids, rid)));
S = struct('events', {ue}, 'methods', {methods});
nE = numel(ue); nM = numel(methods);
red_ev = nan(nE, 6, nM);          % 사건 x 지표 x 방식
for m = 1:nM
    for e = 1:nE
        rr = rid(ismember(rid, ids(strcmp(evs, ue{e}))));
        acc = nan(numel(rr), 6);
        for k = 1:numel(rr)
            iu = find(strcmp(ids, rr{k}) & strcmp(mt, 'U'), 1);
            im = find(strcmp(ids, rr{k}) & strcmp(mt, methods{m}), 1);
            if isempty(im), continue; end
            acc(k,:) = 100*(1 - recs(im).metrics./recs(iu).metrics);
        end
        if all(~isnan(acc(:))), red_ev(e,:,m) = mean(acc, 1); end
    end
end
S.red_event = red_ev;                         % 사건별 6지표 저감률
S.score_event = reshape(mean(red_ev, 2), nE, nM);   % 사건 x 방식
S.S = mean(S.score_event, 1);                 % 방식별 전체 점수
iR = find(strcmp(methods, 'R'), 1);
S.dS = nan(1, nM); S.ci = nan(2, nM); S.n_better = nan(1, nM); S.n_worse = nan(1, nM);
S.worst_dS = nan(1, nM); S.tor_worse_events = nan(1, nM); S.tor_worst_pp = nan(1, nM);
if ~isempty(iR)
    B = cfg.evaluation.bootstrap_n; rng(cfg.evaluation.bootstrap_seed, 'twister');
    bi = randi(nE, nE, B);
    for m = 1:nM
        d = S.score_event(:, m) - S.score_event(:, iR);
        S.dS(m) = mean(d);
        bs = mean(d(bi), 1); bs = sort(bs);
        S.ci(:, m) = [bs(max(1, round(0.025*B))); bs(min(B, round(0.975*B)))];
        S.n_better(m) = sum(d > 0); S.n_worse(m) = sum(d < 0); S.worst_dS(m) = min(d);
        dt = reshape(red_ev(:, 5:6, m) - red_ev(:, 5:6, iR), nE, 2);   % 비틀림 최대·RMS 저감률 차 (음수 = 악화)
        S.tor_worse_events(m) = sum(any(dt < 0, 2)); S.tor_worst_pp(m) = min(dt(:));
    end
end
end
