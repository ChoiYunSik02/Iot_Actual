function w5_build_slx()
%W5_BUILD_SLX  예측 선제 제어 Simulink 모델(w5_tlcd_eew.slx)을 기본 블록만으로 생성합니다.
%
%   구성 (Simscape 등 추가 제품 없음)
%     From Workspace   지반가속도 ag(t)
%     Clock + Compare  경보 시각 tA = tS − Tlead 이후 목표값으로 전환 (Switch)
%     Rate Limiter     액추에이터 속도 한계 (펌프 · 공기압 · 밸브)
%     MATLAB Function  건물 6자유도 + TLCD 1자유도 가속도, Δ-DBG 밸브, 스트로크 하드스톱
%     Integrator × 2   가속도 → 속도 → 변위
%     To Workspace     응답 저장
%
%   변수는 Simulink.SimulationInput.setVariable 로 넣습니다 (w5_sim_run 참고).

mdl = 'w5_tlcd_eew';
if bdIsLoaded(mdl), close_system(mdl, 0); end
here = fileparts(mfilename('fullpath'));
f = fullfile(here, [mdl '.slx']);
if exist(f, 'file'), delete(f); end
new_system(mdl);  open_system(mdl);
set_param(mdl, 'Solver','ode4', 'FixedStep','dt', 'StopTime','Tend', ...
          'SaveOutput','off', 'SaveTime','off', 'ReturnWorkspaceOutputs','on');

A = @(blk, varargin) add_block(blk, [mdl '/' varargin{1}], varargin{2:end});

%% 입력
A('simulink/Sources/From Workspace', 'ag', 'VariableName','agTS', 'Position',[40 40 120 70]);
A('simulink/Sources/Clock', 'Clock', 'Position',[40 140 70 170]);
A('simulink/Sources/Constant', 'tA', 'Value','tA', 'Position',[40 200 90 230]);
A('simulink/Logic and Bit Operations/Relational Operator', 'alarm', 'Operator','>=', 'Position',[120 150 160 210]);

%% 액추에이터 2개: 튜닝비(펌프 또는 공기압), 밸브 기준 손실계수(log2)
acts = {'gam','g0','g1','rate_g', 220;  'lxi','lxi0','lxi1','rate_xi', 340};
for i = 1:2
    [nm, s0, s1, rt, y] = acts{i,:};
    A('simulink/Sources/Constant', [nm '_0'], 'Value',s0, 'Position',[200 y 250 y+25]);
    A('simulink/Sources/Constant', [nm '_1'], 'Value',s1, 'Position',[200 y+60 250 y+85]);
    A('simulink/Signal Routing/Switch', [nm '_sw'], 'Criteria','u2 > Threshold', ...
      'Threshold','0.5', 'Position',[290 y 330 y+85]);
    A('simulink/Discontinuities/Rate Limiter', [nm '_rate'], 'RisingSlewLimit',rt, ...
      'FallingSlewLimit',['-' rt], 'InitialCondition',s0, 'Position',[370 y+25 420 y+60]);
    add_line(mdl, [nm '_1/1'], [nm '_sw/1']);
    add_line(mdl, 'alarm/1',   [nm '_sw/2']);
    add_line(mdl, [nm '_0/1'], [nm '_sw/3']);
    add_line(mdl, [nm '_sw/1'], [nm '_rate/1']);
end
add_line(mdl, 'Clock/1', 'alarm/1');  add_line(mdl, 'tA/1', 'alarm/2');
A('simulink/User-Defined Functions/Fcn', 'pow2', 'Expression','2^u', 'Position',[460 380 510 410]);
add_line(mdl, 'lxi_rate/1', 'pow2/1');

%% 동역학
A('simulink/User-Defined Functions/MATLAB Function', 'plant', 'Position',[580 60 720 220]);
A('simulink/Continuous/Integrator', 'v', 'InitialCondition','zeros(7,1)', 'Position',[780 80 810 110]);
A('simulink/Continuous/Integrator', 'x', 'InitialCondition','zeros(7,1)', 'Position',[860 80 890 110]);
A('simulink/Sinks/To Workspace', 'out_x', 'VariableName','xout', 'SaveFormat','Array', 'Position',[950 80 1010 110]);

ch = find(sfroot, '-isa','Stateflow.EMChart', 'Path',[mdl '/plant']);
ch.Script = strjoin({
 'function acc = plant(x, v, ag, gam, xib, M, K0, C0, Lv, mf, cA, w1d, stroke, kstop)'
 '% 건물 6층 + TLCD (7자유도) 가속도 — w5_simulate.m 과 같은 식'
 'kf = mf*(gam*w1d)^2;'
 'K = K0;  K(7,7) = kf;'
 '% Δ-DBG: 최상층 변위 증분 부호 = 최상층 속도 부호'
 'if v(6)*v(7) <= 0, xi = 2.0*xib; else, xi = 0.6*xib; end'
 'C = C0;  C(7,7) = cA*xi*abs(v(7));'
 'Fs = zeros(7,1);  ov = abs(x(7)) - stroke;'
 'if ov > 0, Fs(7) = -kstop*kf*ov*sign(x(7)); end'
 'acc = M \ (Lv*ag + Fs - C*v - K*x);'
 }, newline);
for nmP = {'M','K0','C0','Lv','mf','cA','w1d','stroke','kstop'}
    d = find(ch, '-isa','Stateflow.Data', 'Name', nmP{1});
    d.Scope = 'Parameter';
end

add_line(mdl, 'x/1', 'plant/1', 'autorouting','on');
add_line(mdl, 'v/1', 'plant/2', 'autorouting','on');
add_line(mdl, 'ag/1', 'plant/3', 'autorouting','on');
add_line(mdl, 'gam_rate/1', 'plant/4', 'autorouting','on');
add_line(mdl, 'pow2/1', 'plant/5', 'autorouting','on');
add_line(mdl, 'plant/1', 'v/1');
add_line(mdl, 'v/1', 'x/1');
add_line(mdl, 'x/1', 'out_x/1');

save_system(mdl, f);  close_system(mdl);
fprintf('saved %s\n', f);
end
