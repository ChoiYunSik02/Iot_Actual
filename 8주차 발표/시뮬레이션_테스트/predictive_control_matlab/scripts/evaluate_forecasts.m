function T = evaluate_forecasts(stage, which, torch_path)
% EVALUATE_FORECASTS  예측 진단 (계획서 8절): 0.2·0.5·1·2·4 s 누적 구간 RMSE, 진폭 오차(4 s 최대 절댓값 차, m/s²), 최대 발생시점 오차, 시간 정렬.
%  which : {'zero','persistence','var','lstm','torch','lstmnat'} 중 일부 (기본 전부 가능한 것)
%  torch_path : PyTorch 모델 경로(확장자 없이). 'torch'(Python 호출)·'lstmnat'(MATLAB 재구현)에 사용
%  분할 : val(합성 검증), real_val(실제 개발 사건, 분리 진단). test는 다루지 않는다.
%  시험 파형을 사후 이동시켜 오차를 줄이지 않는다(시간 정렬은 진단값으로만 보고).
%  결과 : results/forecast_metrics_<stage>.csv (원본 평균 → 사건 평균 → 전체 평균)
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config(); D = load_dataset(root, stage); Hn = D.Hn; sc = D.scaler;
isoct = exist('OCTAVE_VERSION', 'builtin') > 0;
if nargin < 2
    which = {'zero', 'persistence', 'var'};
    if ~isoct && exist(fullfile(root, 'models', 'forecaster_selected.mat'), 'file'), which{end+1} = 'lstm'; end
end
mods = struct();
if any(strcmp(which, 'var'))
    if isoct, tag = '_octave'; else, tag = ''; end
    mods.var = load(fullfile(root, 'models', ['var_' stage tag '.mat']));
end
if any(strcmp(which, 'lstm')), S = load(fullfile(root, 'models', 'forecaster_selected.mat')); mods.lstm = S.model; end
if any(strcmp(which, 'torch')), mods.torch = load_torch_model(torch_path, true); end
if any(strcmp(which, 'lstmnat')), mods.lstmnat = load_torch_model(torch_path, false); end
hz = [0.2 0.5 1 2 4]; nh = round(hz*100);
ftag = ''; if any(strcmp(which, 'torch')) || any(strcmp(which, 'lstmnat')), ftag = '_torch'; end
fid = fopen(fullfile(root, 'results', ['forecast_metrics_' stage ftag out_tag() '.csv']), 'w');
fprintf(fid, 'env,split,predictor,level,id,n_windows,rmse_0.2s,rmse_0.5s,rmse_1s,rmse_2s,rmse_4s,amp_err_mps2,peak_time_err_s,xcorr_lag_s\n');
T = {};
for sp = {'val', 'real_val'}
    W = D.W.(sp{1}); if isempty(W.src), continue; end
    for p = 1:numel(which)
        nw = size(W.X, 3); Mt = zeros(nw, 9);
        for j = 1:nw
            z = double(W.X(:,:,j));
            wx = z(1,:)'*sc.sd(1) + sc.mu(1); wy = z(2,:)'*sc.sd(2) + sc.mu(2); mk = z(3,:)';
            wx(mk < 0.5) = 0; wy(mk < 0.5) = 0;
            Yt = unpack_forecast_target(double(W.Y(:,j)), sc, Hn);
            switch which{p}
                case 'lstm', Yh = forecast_lstm(mods.lstm, wx, wy, mk);
                case 'torch', Yh = forecast_torch(mods.torch, wx, wy, mk);
                case 'lstmnat', m_ = mods.lstmnat; Yh = unpack_forecast_target(lstm_forward(m_.W, forecast_input(wx, wy, mk, m_.scaler)), m_.scaler, m_.Hn);
                case 'var',  Yh = forecast_simple('var', wx, wy, mk, mods.var, Hn);
                otherwise,   Yh = forecast_simple(which{p}, wx, wy, mk, [], Hn);
            end
            Mt(j,:) = window_metrics(Yh, Yt, nh);
        end
        srcs = unique(W.src);
        Ms = zeros(numel(srcs), 9); ev = cell(numel(srcs), 1);
        for k = 1:numel(srcs)
            Ms(k,:) = nanmean_(Mt(W.src == srcs(k), :)); ev{k} = D.sources(srcs(k)).event;
            fprintf(fid, '%s,%s,%s,source,%s,%d,%s\n', env_string(), sp{1}, which{p}, D.sources(srcs(k)).id, sum(W.src == srcs(k)), num2str_list(Ms(k,:)));
        end
        [ue, ~, ie] = unique(ev);
        Me = zeros(numel(ue), 9);
        for e = 1:numel(ue)
            Me(e,:) = nanmean_(Ms(ie == e, :));
            fprintf(fid, '%s,%s,%s,event,%s,%d,%s\n', env_string(), sp{1}, which{p}, ue{e}, sum(ismember(W.src, srcs(ie == e))), num2str_list(Me(e,:)));
        end
        Ma = nanmean_(Me);
        fprintf(fid, '%s,%s,%s,all,ALL,%d,%s\n', env_string(), sp{1}, which{p}, nw, num2str_list(Ma));
        T(end+1,:) = {sp{1}, which{p}, Ma}; %#ok<AGROW>
        fprintf('%-8s %-12s RMSE 0.2/1/4 s = %.4f %.4f %.4f  진폭 %.3f m/s²  최대시점 %.2f s  지연 %.2f s\n', sp{1}, which{p}, Ma([1 3 5 6 7 8]));
    end
end
fclose(fid);
end

function m = window_metrics(Yh, Yt, nh)
% 두 성분 평균. 시간 0.01 s 격자.
m = zeros(1, 9);
for h = 1:numel(nh)
    m(h) = mean(sqrt(mean((Yh(1:nh(h),:) - Yt(1:nh(h),:)).^2, 1)));
end
a = zeros(1,2); pt = zeros(1,2); lg = zeros(1,2);
for c = 1:2
    [mt, it] = max(abs(Yt(:,c))); [mh, ih] = max(abs(Yh(:,c)));
    a(c) = mh - mt;                                   % 절대 진폭 오차 (기록 끝 0 구간에서 상대 오차가 발산하므로)
    if mh > 0, pt(c) = (ih - it)*0.01; else, pt(c) = NaN; end   % 예측이 0이면 최대 시점 정의 안 됨
    lg(c) = best_lag(Yh(:,c), Yt(:,c), 100)*0.01;
end
m(6) = mean(a); m(7) = mean(pt); m(8) = mean(lg); m(9) = 0;
end

function L = best_lag(a, b, maxlag)
% a(t) ≈ b(t - L) 가 되는 L (양수 = 예측이 늦음), |L| ≤ maxlag
best = -inf; L = 0; n = numel(a);
if all(a == 0), return; end
for l = -maxlag:maxlag
    if l >= 0, x = a(1+l:n); y = b(1:n-l); else, x = a(1:n+l); y = b(1-l:n); end
    c = sum(x.*y)/sqrt(max(sum(x.^2)*sum(y.^2), eps));
    if c > best, best = c; L = l; end
end
end

function m = nanmean_(X)
m = zeros(1, size(X, 2));
for c = 1:size(X, 2), v = X(:,c); v = v(~isnan(v)); if isempty(v), m(c) = NaN; else, m(c) = mean(v); end, end
end

function s = num2str_list(v)
s = sprintf('%.6g,', v(1:8)); s = s(1:end-1);
end
