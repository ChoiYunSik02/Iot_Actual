function t = pack_forecast_target(Yx, Yy, scaler)
% PACK_FORECAST_TARGET  미래 X·Y (각 Hn) → 정규화 정답 벡터 2Hn x 1 = [X(1..Hn); Y(1..Hn)].
t = [(Yx(:) - scaler.mu(1))/scaler.sd(1); (Yy(:) - scaler.mu(2))/scaler.sd(2)];
end
