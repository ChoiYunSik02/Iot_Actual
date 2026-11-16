function mdl = build_simulink(dt)
% BUILD_SIMULINK  models/rs_tlcd_predictive_control.slx 생성 (계획서 4절 서브시스템 구조).
%  각 서브시스템 = MATLAB System 블록(Interpreted execution) 하나. 블록은 MATLAB 스텝 엔진(run_closed_loop)과
%  같은 스텝 함수를 같은 순서로 호출한다. 디지털 지연은 정수 샘플 큐(블록 내부), 연속 Transport Delay는 쓰지 않는다.
%  실행: scripts/run_simulink_case.m (base 작업공간 변수 pc_ctx, gm_now, gm_next, pc_tstop을 만든 뒤 sim)
%   GroundMotion → Plant30Story ─x→ SensorAndLatency → ObservationBuffer → Forecaster ┐
%                                  └→ StateEstimator ───────────────────────────────→ CommandSelector
%                                     → CommandQueue → Actuators ─dev→ Plant30Story (갱신, 직접 통과 없음)
%                                                         └Avec→ Unit Delay → SensorAndLatency
%   Evaluator: 응답·장치·지령을 기록만 한다(제어기로 되먹임 없음). 성능 평가는 시뮬레이션 뒤 오프라인.
if exist('OCTAVE_VERSION', 'builtin') > 0, error('build_simulink: MATLAB + Simulink 필요'); end
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root, 'src'), fullfile(root, 'src', 'sl'));
cfg = pc_config(); if nargin < 1, dt = cfg.plant.dt; end
mdl = 'rs_tlcd_predictive_control';
f = fullfile(root, 'models', [mdl '.slx']);
if ~exist(fileparts(f), 'dir'), mkdir(fileparts(f)); end   % 빈 폴더는 git에 없을 수 있음
if bdIsLoaded(mdl), close_system(mdl, 0); end
new_system(mdl);
ts = sprintf('%.17g', dt);
set_param(mdl, 'Solver', 'FixedStepDiscrete', 'FixedStep', ts, 'StartTime', '0', 'StopTime', 'pc_tstop', ...
          'SaveOutput', 'off', 'SaveTime', 'off', 'ReturnWorkspaceOutputs', 'on', 'AlgebraicLoopMsg', 'error');
% ---- GroundMotion ----
gm = sub(mdl, 'GroundMotion', [30 40 150 110]);
add_block('simulink/Sources/From Workspace', [gm '/now'], 'VariableName', 'gm_now', 'SampleTime', ts, ...
          'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value', 'Position', [40 30 120 60]);
add_block('simulink/Sources/From Workspace', [gm '/next'], 'VariableName', 'gm_next', 'SampleTime', ts, ...
          'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value', 'Position', [40 90 120 120]);
outp(gm, 'ag_now', 1, [200 38 230 52]); outp(gm, 'ag_next', 2, [200 98 230 112]);
add_line(gm, 'now/1', 'ag_now/1'); add_line(gm, 'next/1', 'ag_next/1');
% ---- Plant30Story ----
pl = sub(mdl, 'Plant30Story', [230 160 360 230]);
inp(pl, 'ag_next', 1, [20 30 50 44]); inp(pl, 'dev', 2, [20 80 50 94]);
sysb(pl, 'plant', 'PCPlant', '', ts, [120 30 220 100]);
outp(pl, 'x', 1, [300 38 330 52]); outp(pl, 'top', 2, [300 78 330 92]);
add_line(pl, 'ag_next/1', 'plant/1'); add_line(pl, 'dev/1', 'plant/2');
add_line(pl, 'plant/1', 'x/1'); add_line(pl, 'plant/2', 'top/1');
% ---- 제어 쪽 단계 ----
st = {'SensorAndLatency', 'PCSensor', 3, 1; 'ObservationBuffer', 'PCBuffer', 1, 1; 'Forecaster', 'PCForecaster', 1, 1; ...
      'StateEstimator', 'PCEstimator', 1, 1; 'CommandSelector', 'PCSelector', 2, 1; 'CommandQueue', 'PCQueue', 1, 1; ...
      'Actuators', 'PCActuator', 1, 2};   % {서브시스템, System object 클래스(입출력 수 고정), 입력 수, 출력 수}
pos = [430 40; 600 40; 770 40; 600 160; 940 120; 1110 120; 1280 120];
for k = 1:size(st, 1)
    p = sub(mdl, st{k,1}, [pos(k,1) pos(k,2) pos(k,1)+120 pos(k,2)+70]);
    for j = 1:st{k,3}, inp(p, sprintf('in%d', j), j, [20 20+40*j 50 34+40*j]); end
    sysb(p, 'sys', st{k,2}, '', ts, [110 30 210 30+40*max(st{k,3}, st{k,4})]);
    for j = 1:st{k,3}, add_line(p, sprintf('in%d/1', j), sprintf('sys/%d', j)); end
    for j = 1:st{k,4}
        outp(p, sprintf('out%d', j), j, [280 20+40*j 310 34+40*j]); add_line(p, sprintf('sys/%d', j), sprintf('out%d/1', j));
    end
end
A0 = act_pack(actuator_step([], [], [], struct('F0', cfg.device.f0_hz, 'KAPPA0', cfg.device.kappa0)));   % 초기 장치 상태
add_block('simulink/Discrete/Unit Delay', [mdl '/ActuatorStateDelay'], 'InitialCondition', mat2str(A0(:)), ...
          'SampleTime', ts, 'Position', [1280 260 1320 290]);
% ---- Evaluator (기록 전용) ----
ev = sub(mdl, 'Evaluator', [1460 220 1580 300]);
names = {'top', 'sl_top'; 'dev', 'sl_dev'; 'cmd', 'sl_cmd'};
for j = 1:3
    inp(ev, names{j,1}, j, [20 20+50*j 50 34+50*j]);
    add_block('simulink/Sinks/To Workspace', [ev '/' names{j,2}], 'VariableName', names{j,2}, 'SaveFormat', 'Array', ...
              'SampleTime', ts, 'Position', [120 15+50*j 200 40+50*j]);
    add_line(ev, [names{j,1} '/1'], [names{j,2} '/1']);
end
% ---- 연결 ----
L = {'GroundMotion/2', 'Plant30Story/1'; 'Actuators/1', 'Plant30Story/2'; ...
     'Plant30Story/1', 'SensorAndLatency/1'; 'ActuatorStateDelay/1', 'SensorAndLatency/2'; 'GroundMotion/1', 'SensorAndLatency/3'; ...
     'SensorAndLatency/1', 'ObservationBuffer/1'; 'ObservationBuffer/1', 'Forecaster/1'; 'SensorAndLatency/1', 'StateEstimator/1'; ...
     'StateEstimator/1', 'CommandSelector/1'; 'Forecaster/1', 'CommandSelector/2'; 'CommandSelector/1', 'CommandQueue/1'; ...
     'CommandQueue/1', 'Actuators/1'; 'Actuators/2', 'ActuatorStateDelay/1'; ...
     'Plant30Story/2', 'Evaluator/1'; 'Actuators/1', 'Evaluator/2'; 'CommandSelector/1', 'Evaluator/3'};
for k = 1:size(L, 1), add_line(mdl, L{k,1}, L{k,2}, 'autorouting', 'on'); end
save_system(mdl, f);
fprintf('Simulink 모델 저장: %s (%s)\n', f, version);
end

function p = sub(mdl, name, pos)
p = [mdl '/' name];
add_block('built-in/Subsystem', p, 'Position', pos);
end

function inp(p, name, n, pos)
add_block('built-in/Inport', [p '/' name], 'Port', num2str(n), 'Position', pos);
end

function outp(p, name, n, pos)
add_block('built-in/Outport', [p '/' name], 'Port', num2str(n), 'Position', pos);
end

function sysb(p, name, cls, stage, ts, pos)
b = [p '/' name];
add_block('simulink/User-Defined Functions/MATLAB System', b, 'System', cls, 'Position', pos);
set_param(b, 'SimulateUsing', 'Interpreted execution');
if ~isempty(stage), set_param(b, 'Stage', ['''' stage '''']); end
set_param(b, 'Ts', ts);
end
