function o = run_simulink_case(agx, agy, method, opt)
% RUN_SIMULINK_CASE  Simulink 모델로 한 기록 실행. run_closed_loop와 같은 출력 형식(ux, uy, th, f_dev, theta, kappa, timeline).
%  method : pc_method 이름,  opt.dt, opt.model(예측기), opt.override
if nargin < 4, opt = struct(); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'src', 'sl'));
cfg = pc_config();
if ~isfield(opt, 'dt'), opt.dt = cfg.plant.dt; end
if ~isfield(opt, 'model'), opt.model = []; end
if ~isfield(opt, 'override'), opt.override = struct(); end
if isfield(opt, 'cfg'), cfg = opt.cfg; end
mdl = 'rs_tlcd_predictive_control';
f = fullfile(root, 'models', [mdl '.slx']);
if ~exist(f, 'file'), build_simulink(opt.dt); end
load_system(f);
if abs(str2double(get_param(mdl, 'FixedStep')) - opt.dt) > 1e-15, close_system(mdl, 0); build_simulink(opt.dt); load_system(f); end
agx = agx(:); agy = agy(:); nt = numel(agx);
M = pc_method(cfg, method, opt.override);
[P, ~] = plant_init(cfg, opt.dt); P.rt = pc_runtime(cfg, P, M, nt);
ctx = struct('cfg', cfg, 'M', M, 'P', P, 'model', opt.model, 'preview', [], 'nt', nt);
if strcmp(M.forecaster, 'preview'), ctx.preview = struct('agx', agx, 'agy', agy); end
t = (0:nt-2)'*opt.dt;
assignin('base', 'pc_ctx', ctx);
assignin('base', 'gm_now', [t, agx(1:nt-1), agy(1:nt-1)]);
assignin('base', 'gm_next', [t, agx(2:nt), agy(2:nt)]);
assignin('base', 'pc_tstop', (nt-2)*opt.dt);
assignin('base', 'pc_sl_logs', struct());
t0 = tic;
so = sim(mdl);
wall = toc(t0);
top = as_rows(so.get('sl_top'), 3); dev = as_rows(so.get('sl_dev'), 3);   % To Workspace 'Array'는 [c x 1] 신호를 c x 1 x N으로 저장
if size(top, 1) ~= nt - 1, error('run_simulink_case: 기록 길이 %d ≠ 기대 %d', size(top, 1), nt - 1); end
L = evalin('base', 'pc_sl_logs');
% run_closed_loop 형식: 인덱스 1 = 스텝 0. Simulink 출력 시각 t_i의 top = 스텝 i 상태, dev = 스텝 i 장치 상태.
n = size(top, 1);
o = struct('method', method, 'dt', opt.dt, 'wall_s', wall, 'n_logged', n);
o.ux = top(:,1); o.uy = top(:,2); o.th = top(:,3);
o.f_dev = [0; dev(1:end-1,1)]; o.theta = [0; dev(1:end-1,2)]; o.kappa = [0; dev(1:end-1,3)];
if strcmp(M.select, 'U'), o.f_dev(:) = 0; o.theta(:) = 0; o.kappa(:) = 0; end
if isfield(L, 'timeline'), o.timeline = L.timeline; else, o.timeline = zeros(0, 20); end
if isfield(L, 'forecast'), o.forecast = L.forecast; end
if isfield(L, 'queue'), o.queue = L.queue; end
end

function X = as_rows(X, c)
% 기록 배열을 N x c로 맞춘다 (c x 1 x N 또는 c x N이면 바꾼다)
if ndims(X) == 3
    X = reshape(X, c, [])';
elseif size(X, 2) ~= c && size(X, 1) == c
    X = X';
end
end
