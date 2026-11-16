function Y = forecast_lstm(model, wx, wy, mk)
% FORECAST_LSTM  학습된 LSTM 예측 (Deep Learning Toolbox 필요, MATLAB 전용).
%  입력 창을 학습 분할 scaler로 정규화(유효 샘플만) → 마스크 0 칸은 0 → 3 x 500 'CTB'로 전달.
%  출력 800 = [X(1..400); Y(1..400)] 순서 (pack_forecast_target과 같은 순서) → 역정규화.
%  창 기반 stateless 추론: 매 호출마다 상태를 초기화한 네트워크에 창 전체를 넣는다.
X = forecast_input(wx, wy, mk, model.scaler);
dlX = dlarray(single(X), 'CTB');
Yn = double(extractdata(predict(model.net, dlX)));
Y = unpack_forecast_target(Yn(:), model.scaler, model.Hn);
end
