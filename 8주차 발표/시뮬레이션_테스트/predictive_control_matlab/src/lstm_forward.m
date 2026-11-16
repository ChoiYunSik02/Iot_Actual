function y = lstm_forward(Wt, X)
% LSTM_FORWARD  PyTorch에서 학습한 작은 LSTM의 MATLAB 재구현 순전파 (Deep Learning Toolbox 불필요).
%  Wt : python/pc_lstm.py가 저장한 <out>_weights.mat (W_ih 4Hx3, W_hh 4HxH, b 4Hx1, W1, b1, W2, b2)
%  X  : 3 x T (forecast_input 출력: 정규화 X, 정규화 Y, 마스크)
%  y  : 800 x 1 (정규화 [X(1..400); Y(1..400)])
%  게이트 순서는 PyTorch와 같은 i, f, g, o. 창마다 초기 상태 0 (stateless).
Hn = size(Wt.W_hh, 2); h = zeros(Hn, 1); c = zeros(Hn, 1);
Wx = Wt.W_ih*X + Wt.b;                     % 입력 항을 한꺼번에 계산
for t = 1:size(X, 2)
    g = Wx(:, t) + Wt.W_hh*h;
    i = 1./(1 + exp(-g(1:Hn))); f = 1./(1 + exp(-g(Hn+1:2*Hn)));
    gg = tanh(g(2*Hn+1:3*Hn)); o = 1./(1 + exp(-g(3*Hn+1:4*Hn)));
    c = f.*c + i.*gg; h = o.*tanh(c);
end
y = Wt.W2*max(Wt.W1*h + Wt.b1, 0) + Wt.b2;
end
