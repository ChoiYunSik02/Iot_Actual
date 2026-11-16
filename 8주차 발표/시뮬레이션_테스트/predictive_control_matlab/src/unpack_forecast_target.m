function Y = unpack_forecast_target(t, scaler, Hn)
% UNPACK_FORECAST_TARGET  정규화 벡터 2Hn x 1 → Hn x 2 [X Y] (m/s²). pack_forecast_target의 역.
t = t(:);
Y = [t(1:Hn)*scaler.sd(1) + scaler.mu(1), t(Hn+1:2*Hn)*scaler.sd(2) + scaler.mu(2)];
end
