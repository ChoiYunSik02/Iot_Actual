function Y = forecast_torch(model, wx, wy, mk)
% FORECAST_TORCH  PyTorch LSTM 추론을 MATLAB에서 Python 호출로 실행 (pc_infer.py).
%  model.path : 모델 경로(확장자 없이), model.scaler, model.Hn, model.mod (py 모듈, load_torch_model이 채움)
%  입력 변환(MATLAB → numpy) · 호출 · 출력 변환(numpy → MATLAB) 시간이 모두 forecaster_step의 실측 계산시간에 들어간다.
X = forecast_input(wx, wy, mk, model.scaler);              % 3 x 500
y = model.mod.infer(model.path, py.numpy.array(X(:)'));     % 열 우선 펼침 → Python에서 (500, 3)
Y = unpack_forecast_target(double(y)', model.scaler, model.Hn);
end
