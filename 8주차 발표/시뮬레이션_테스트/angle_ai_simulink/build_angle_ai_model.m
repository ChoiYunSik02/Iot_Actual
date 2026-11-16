function build_angle_ai_model()
% Simulink 모델 rs_tlcd_angle_ai.slx 생성.
% 구성: 지진 입력(From Workspace) -> [제어기: 원문 펌프·밸브 + 회전각 정책] -> [플랜트: 30층 편심 건물 + RS-TLCD] -> 단위지연(상태 x_k) 되먹임
% 정책 선택: 기본 작업공간 변수 POLICY (1=R 원문, 2=AI, 3=최근 1.3 s 방향)
mdl='rs_tlcd_angle_ai';
if bdIsLoaded(mdl), close_system(mdl,0); end
if exist([mdl '.slx'],'file'), delete([mdl '.slx']); end
new_system(mdl); open_system(mdl);
set_param(mdl,'Solver','FixedStepDiscrete','FixedStep','SIM_DT','StopTime','SIM_TEND','SaveOutput','off','SaveTime','off','SaveState','off','ReturnWorkspaceOutputs','off');
add_block('simulink/Sources/From Workspace',[mdl '/지진 입력 ag'],'VariableName','SIM_AG','SampleTime','SIM_DT','Interpolate','off','OutputAfterFinalValue','Holding final value','Position',[40 120 140 160]);
add_block('simulink/Sources/Clock',[mdl '/시간'],'Position',[40 40 70 70]);
add_block('simulink/Sources/Constant',[mdl '/정책 POLICY'],'Value','POLICY','SampleTime','SIM_DT','Position',[40 200 110 230]);
add_block('simulink/Discrete/Unit Delay',[mdl '/상태 x_k'],'InitialCondition','zeros(184,1)','SampleTime','SIM_DT','Position',[560 300 620 340]);
add_block('simulink/User-Defined Functions/MATLAB Function',[mdl '/제어기 (펌프·밸브 원문, 회전각 정책)'],'Position',[250 60 430 240]);
add_block('simulink/User-Defined Functions/MATLAB Function',[mdl '/플랜트 (30층 편심 건물 + RS-TLCD)'],'Position',[520 100 700 240]);
add_block('simulink/Signal Routing/Selector',[mdl '/옥상 X·Y·θ'],'InputPortWidth','184','Indices','[30 61 92]','Position',[700 300 760 340]);
add_block('simulink/Sinks/To Workspace',[mdl '/응답 저장'],'VariableName','SIM_Y','SaveFormat','Array','SampleTime','SIM_DT','Position',[800 300 880 340]);
add_block('simulink/Sinks/To Workspace',[mdl '/지령 저장'],'VariableName','SIM_U','SaveFormat','Array','SampleTime','SIM_DT','Position',[520 20 600 50]);
rt=sfroot; m=rt.find('-isa','Simulink.BlockDiagram','Name',mdl);
c1=m.find('-isa','Stateflow.EMChart','Name','제어기 (펌프·밸브 원문, 회전각 정책)');
c1.Script=sprintf(['function u = ctrl(t, x, ag, pol)\n%% 원문 펌프(식 10·11)·밸브(식 12)·회전 속도 제한 + 회전 목표각 정책\n' ...
 'coder.extrinsic(''sim_ctrl_step'');\nu = zeros(4,1);\nu = sim_ctrl_step(t, x, ag, pol);\n']);
c2=m.find('-isa','Stateflow.EMChart','Name','플랜트 (30층 편심 건물 + RS-TLCD)');
c2.Script=sprintf(['function xn = plant(x, ag, u)\n%% 이산 상태공간: x_{k+1} = Ad(f,θ) x_k + Bd [ag; F_TLCD]\n' ...
 'coder.extrinsic(''sim_plant_step'');\nxn = zeros(184,1);\nxn = sim_plant_step(x, ag, u);\n']);
C='제어기 (펌프·밸브 원문, 회전각 정책)'; Pn='플랜트 (30층 편심 건물 + RS-TLCD)';
add_line(mdl,'시간/1',[C '/1'],'autorouting','on');
add_line(mdl,'상태 x_k/1',[C '/2'],'autorouting','on');
add_line(mdl,'지진 입력 ag/1',[C '/3'],'autorouting','on');
add_line(mdl,'정책 POLICY/1',[C '/4'],'autorouting','on');
add_line(mdl,'상태 x_k/1',[Pn '/1'],'autorouting','on');
add_line(mdl,'지진 입력 ag/1',[Pn '/2'],'autorouting','on');
add_line(mdl,[C '/1'],[Pn '/3'],'autorouting','on');
add_line(mdl,[Pn '/1'],'상태 x_k/1','autorouting','on');
add_line(mdl,'상태 x_k/1','옥상 X·Y·θ/1','autorouting','on');
add_line(mdl,'옥상 X·Y·θ/1','응답 저장/1','autorouting','on');
add_line(mdl,[C '/1'],'지령 저장/1','autorouting','on');
save_system(mdl); fprintf('MODEL_BUILT\n');
end
