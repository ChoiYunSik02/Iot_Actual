function res = test_lstm_shapes()
% TEST_LSTM_SHAPES  계획서 5·8절: 3x500 'CTB' 입력, batch 차원, 800 출력 펼침 순서를 작은 알려진 배열로 단위시험 (MATLAB 전용).
%  1) 학습 안 한 같은 구조 네트워크로 batch 예측과 단건 예측이 같은지
%  2) minibatchpredict(trainnet 경로)와 predict(dlarray, 온라인 경로)가 같은지
%  3) forecast_lstm 출력 400x2가 [X(1..400); Y(1..400)] 순서인지 (마지막 FC 가중치를 조작해 확인)
%  4) 창 기반 stateless: 같은 창을 두 번 넣으면 같은 출력 (상태 누적 없음)
if exist('OCTAVE_VERSION', 'builtin') > 0, error('MATLAB 전용'); end
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
rng(1);
layers = [sequenceInputLayer(3), lstmLayer(64, 'OutputMode', 'last'), fullyConnectedLayer(128), reluLayer, fullyConnectedLayer(800)];
net = dlnetwork(layers);
X = randn(3, 500, 4, 'single'); X(3,:,:) = 1; X(3,1:100,2) = 0;
Yb = minibatchpredict(net, X, 'InputDataFormats', 'CTB', 'OutputDataFormats', 'CB');
ok1 = isequal(size(Yb), [800 4]);
Y2 = extractdata(predict(net, dlarray(X(:,:,2), 'CTB')));
ok2 = max(abs(Y2 - Yb(:,2))) < 1e-5;
Y2b = extractdata(predict(net, dlarray(X(:,:,2), 'CTB')));
ok4 = isequal(Y2, Y2b);
% 출력 순서: 마지막 FC를 상수 출력으로 바꿔 [1..800]이 나오게 한 뒤 unpack
fc = net.Layers(end);
W = zeros(800, 128, 'single'); b = single((1:800)');
newfc = fullyConnectedLayer(800, 'Name', fc.Name, 'Weights', W, 'Bias', b);
try
    net2 = replaceLayer(net, fc.Name, newfc);
    if ~net2.Initialized, net2 = initialize(net2); end
catch
    net2 = dlnetwork(replaceLayer(layerGraph(net), fc.Name, newfc));   % 옛 버전 경로
end
model = struct('net', net2, 'scaler', struct('mu', [0 0], 'sd', [1 1]), 'Hn', 400);
Y = forecast_lstm(model, zeros(500,1), zeros(500,1), ones(500,1));
ok3 = isequal(size(Y), [400 2]) && all(Y(:,1) == (1:400)') && all(Y(:,2) == (401:800)');
res = struct('batch_shape', ok1, 'predict_vs_minibatch', ok2, 'output_order', ok3, 'stateless', ok4);
disp(res);
assert(ok1 && ok2 && ok3 && ok4, 'test_lstm_shapes 실패');
fprintf('LSTM 배열 형식 단위시험 통과 (%s)\n', env_string());
end
