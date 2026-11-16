function X = forecast_input(wx, wy, mk, scaler)
% FORECAST_INPUT  창(원시 m/s²) → 네트워크 입력 3 x Wn (채널 x 시간: 정규화 X, 정규화 Y, 마스크).
%  유효 샘플만 학습 분할 평균·표준편차로 정규화하고, 마스크 0 칸은 정규화 뒤 0으로 둔다. 마스크는 표준화하지 않는다.
zx = (wx(:) - scaler.mu(1))/scaler.sd(1); zy = (wy(:) - scaler.mu(2))/scaler.sd(2);
m = mk(:) > 0.5;
zx(~m) = 0; zy(~m) = 0;
X = [zx'; zy'; double(m)'];
end
