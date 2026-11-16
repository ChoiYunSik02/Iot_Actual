function m = response_metrics(ux, uy, th)
% RESPONSE_METRICS  6지표 [ux_max ux_rms uy_max uy_rms th_max th_rms] (전체 기록, 최상층). run_validation.m과 같은 정의.
m = [max(abs(ux)), sqrt(mean(ux.^2)), max(abs(uy)), sqrt(mean(uy.^2)), max(abs(th)), sqrt(mean(th.^2))];
end
