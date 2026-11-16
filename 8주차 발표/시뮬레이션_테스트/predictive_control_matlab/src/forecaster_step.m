function [FS, fcv] = forecaster_step(FS, bufv, i, P)
% FORECASTER_STEP  0.2 s마다 미래 4 s X·Y 지반가속도 예측 (작업자 1개, 계산 지연 반영).
%  - 예측 기준시각(origin) = 창의 가장 최근 관측 시각(t_obs). 반환 시각(ready)에 첫 샘플을 붙이지 않는다.
%  - 준비 시각(ready): nominal = 시작 + d_fc,  actual = 시작 + max(d_fc, ceil(실측 계산시간/dt)).
%    계산이 끝나기 전에는 쓸 수 없다. 작업 중(아직 준비 전)에 오는 갱신 시각은 건너뛰고 miss_busy로 센다.
%  - 실측 계산시간이 갱신 주기(0.2 s)를 넘으면 miss_deadline으로 센다. 그 예측은 원래 기준시각 그대로(새 예측으로 취급하지 않고) 쓴다.
%  fcv = [valid; origin; ready; Yx(400); Yy(400)]  (길이 803). 가장 최근에 '준비된' 예측.
%  FS 초기화: FS = forecaster_step(struct('kind',..,'model',..,'preview',..), [], [], P)
rt = P.rt; Hn = rt.Hn;
if ~isfield(FS, 'ready_init')
    FS.ready_init = true;
    FS.pending = []; FS.latest = zeros(3 + 2*Hn, 1);
    FS.miss_busy = 0; FS.miss_deadline = 0; FS.n_run = 0;
    FS.log = zeros(0, 5);   % [tick_step origin_stamp ready_step wall_s(주입 포함) used(1)/busy(-1)/NaN(0)]
    fcv = FS.latest;
    return;
end
FS = promote(FS, i);                 % 이번 스텝에 끝나는 작업을 먼저 반영 (작업자 비움)
if mod(i, rt.nupd) == 0 && bufv(1) > 0.5
    if ~isempty(FS.pending)
        FS.miss_busy = FS.miss_busy + 1;
        FS.log(end+1,:) = [i, bufv(2), NaN, NaN, -1];
    else
        Wn = rt.Wn;
        wx = bufv(4:3+Wn); wy = bufv(4+Wn:3+2*Wn); mk = bufv(4+2*Wn:3+3*Wn);
        origin = bufv(2);
        t0 = tic;
        Y = run_forecaster(FS, wx, wy, mk, origin, P);
        wall = toc(t0) + rt.inject_forecast_s;
        FS.n_run = FS.n_run + 1;
        if wall > rt.update_period_s, FS.miss_deadline = FS.miss_deadline + 1; end
        if strcmp(rt.timing_mode, 'actual')
            ready = i + max(rt.d_fc, ceil(wall/P.dt - 1e-9));
        else
            ready = i + rt.d_fc;
        end
        if any(~isfinite(Y(:)))
            FS.log(end+1,:) = [i, origin, NaN, wall, 0];
        else
            FS.pending = struct('origin', origin, 'ready', ready, 'Y', Y);
            FS.log(end+1,:) = [i, origin, ready, wall, 1];
        end
    end
end
FS = promote(FS, i);                 % 지연 0이면 같은 스텝에 쓸 수 있음
fcv = FS.latest;
end

function FS = promote(FS, i)
if ~isempty(FS.pending) && i >= FS.pending.ready
    pd = FS.pending;
    FS.latest = [1; pd.origin; pd.ready; pd.Y(:,1); pd.Y(:,2)];
    FS.pending = [];
end
end

function Y = run_forecaster(FS, wx, wy, mk, origin, P)
switch FS.kind
    case {'zero', 'persistence', 'var'}
        Y = forecast_simple(FS.kind, wx, wy, mk, FS.model, P.rt.Hn);
    case 'lstm'
        Y = forecast_lstm(FS.model, wx, wy, mk);
    case 'torch'                                   % PyTorch 모델, Python 호출 (변환·호출 시간 포함)
        Y = forecast_torch(FS.model, wx, wy, mk);
    case 'lstmnat'                                 % 같은 가중치의 MATLAB 재구현 (Python 없이)
        Y = unpack_forecast_target(lstm_forward(FS.model.W, forecast_input(wx, wy, mk, FS.model.scaler)), FS.model.scaler, FS.model.Hn);
    case 'preview'
        % 실현 불가 참고군: 기준시각 뒤의 실제 입력 (100 Hz 격자, 기록 끝 뒤는 0)
        q = origin + P.rt.r*(1:P.rt.Hn)';
        Y = zeros(P.rt.Hn, 2); ok = q + 1 <= numel(FS.preview.agx);
        Y(ok,1) = FS.preview.agx(q(ok)+1); Y(ok,2) = FS.preview.agy(q(ok)+1);
    otherwise
        error('forecaster_step: kind %s', FS.kind);
end
end
