function rt = pc_runtime(cfg, P, M, nt)
% PC_RUNTIME  시간축 설정을 정수 스텝으로 바꾼다 (계획서 5·6절).
%  센서 지연은 반올림, 연산·통신·추가 지연은 올림(계산 종료 전에 지령이 적용되지 않도록).
dt = P.dt;
rt = struct();
rt.r = round((1/cfg.sensor.ai_rate_hz)/dt);           % 플랜트 스텝 / AI 샘플
if abs(rt.r*dt - 1/cfg.sensor.ai_rate_hz) > 1e-12, error('pc_runtime: dt가 AI 샘플 간격의 약수가 아님'); end
rt.Wn = round(cfg.forecast.window_s*cfg.sensor.ai_rate_hz);
rt.Hn = round(cfg.forecast.horizon_s*cfg.sensor.ai_rate_hz);
rt.nupd = round(cfg.forecast.update_period_s/dt);
rt.update_period_s = cfg.forecast.update_period_s;
rt.first_after_trigger_s = cfg.forecast.first_after_trigger_s;
rt.min_eval_s = cfg.forecast.min_eval_s;
rt.trigger = cfg.sensor.trigger_mps2;
rt.d_s = round(M.sensor_s/dt);
rt.d_cmd = ceil((M.comm_s + M.extra_info_s + M.select_s)/dt - 1e-9);
rt.d_fc = ceil(M.forecast_s/dt - 1e-9);
if isfield(M, 'selectV_s'), sV = M.selectV_s; else, sV = M.select_s; end
rt.d_cmd_V = ceil((M.comm_s + M.extra_info_s + sV)/dt - 1e-9);   % J 빠른(밸브만) 결정의 앞당김
if isfield(M, 'R_s'), rR = M.R_s; else, rR = M.select_s; end
rt.d_cmd_R = ceil((M.comm_s + M.extra_info_s + rR)/dt - 1e-9);   % 원래 시각 R 경로(C1 default_path='ontime')의 결정 앞당김
rt.timing_mode = M.timing_mode;                     % 'actual' | 'nominal' (config latency.timing_note)
rt.comm_extra_s = M.comm_s + M.extra_info_s;      % 선택 계산이 끝난 뒤 도착까지 걸리는 시간
rt.inject_select_s = M.inject_select_s; rt.inject_forecast_s = M.inject_forecast_s;
rt.nmax100 = ceil(nt/rt.r) + 1;
rt.noise_std = cfg.sensor.noise_std_mps2;
if rt.noise_std > 0
    st = randn('state'); randn('state', cfg.sensor.noise_seed); %#ok<RAND>
    rt.noise = rt.noise_std*randn(4, nt);
    randn('state', st); %#ok<RAND>
else
    rt.noise = [];
end
end
