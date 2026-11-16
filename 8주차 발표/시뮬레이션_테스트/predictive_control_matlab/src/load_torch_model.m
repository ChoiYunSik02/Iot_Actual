function model = load_torch_model(path, use_python)
% LOAD_TORCH_MODEL  PyTorch smoke 모델 읽기.
%  path       : 확장자 없는 경로 (예: models/torch_smoke_seed8401)
%  use_python : true  → Python(pc_infer.py)으로 추론할 준비 (forecaster 'torch')
%               false → <path>_weights.mat만 읽어 MATLAB 재구현(lstm_forward)으로 추론 (forecaster 'lstmnat')
%  Python 경로는 MATLAB pyenv 설정을 따른다 (scripts/run_torch_smoke.m 참고).
if nargin < 2, use_python = true; end
W = load([path '_weights.mat']);
meta = jsondecode(fileread([path '.json']));
model = struct('path', path, 'scaler', struct('mu', W.mu(:)', 'sd', W.sd(:)'), 'Hn', 400, 'W', W, 'meta', meta, 'mod', []);
if use_python
    pydir = fullfile(pc_root(), 'python');
    if count(py.sys.path, pydir) == 0, insert(py.sys.path, int32(0), pydir); end
    model.mod = py.importlib.import_module('pc_infer');
    model.mod.load(path, int32(1));                         % 스레드 1개 (지연 측정 일관성)
end
end
