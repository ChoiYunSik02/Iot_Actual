%W5_SIM_COMPARE  Simulink 모델이 MATLAB 스크립트(w5_simulate) 결과를 재현하는지 확인
%
%   조건: 시나리오 B · PGA 0.6g · 실측 기록 3개 · 리드타임 0 / 10 s
%         전략 S0(사전동작 없음), S3(밸브+펌프 30 s)
%   기준: RMS 저감률 차이 1%p 이내, 스트로크 이용률 차이 0.02 이내

addpath('..');
[p, ~, tl] = w5_params();
if ~exist('w5_tlcd_eew.slx','file'), w5_build_slx; end
load_system('w5_tlcd_eew');
S  = load('w5_lookup.mat');  LT = S.LTB;
pga = 0.6;
b   = w5_building(p, pga, 'B');
xi0 = interp1(S.LTA.pga, S.LTA.best_xi, 0.2);
xi1 = 2^interp1(LT.pga, log2(LT.best_xi), pga);
g1  = interp1(LT.pga, LT.best_gamma, pga);
g0  = interp1(S.LTA.pga, S.LTA.best_gamma, 0.2);
rg  = diff(p.gamma_range)/p.T_pump;
rx  = (log2(64) - log2(0.25))/p.T_valve;

recs = {'gyeongju','pohang','elcentro'};
rows = {};
for ir = 1:3
    [ag, t, info] = w5_record(recs{ir}, pga, p.dt, p.T);  t = t(:)';  N = numel(t);
    U = w5_simulate(p,b,tl,t,ag,[],[],false).rms_disp;
    for Tl = [0 10]
        for st = {'S0','S3'}
            if strcmp(st{1},'S0'), g = [g0 g0 rg]; lx = [log2(xi0) log2(xi0) rx];
            else,                  g = [g0 g1 rg];       lx = [log2(xi0) log2(xi1) rx]; end
            gam = w5_setting(t, info.tS, Tl, g(1), g(2), g(3));
            lxi = w5_setting(t, info.tS, Tl, lx(1), lx(2), lx(3));
            tic; o1 = w5_simulate(p,b,tl,t,ag,gam,2.^lxi,true); t1 = toc;
            tic; o2 = w5_sim_run(p,b,tl,t,ag,info.tS,Tl,g,lx);   t2 = toc;
            r1 = 100*(1-o1.rms_disp/U);  r2 = 100*(1-o2.rms_disp/U);
            rows(end+1,:) = {recs{ir}, Tl, st{1}, r1, r2, r2-r1, o1.stroke_use, o2.stroke_use, t1, t2}; %#ok<SAGROW>
        end
    end
end
T = cell2table(rows, 'VariableNames', {'record','lead_s','strategy','red_script','red_simulink', ...
    'diff_pp','stroke_script','stroke_simulink','sec_script','sec_simulink'});
disp(T);
writetable(T, fullfile('..','..','5주차 발표','w5_simulink_check.csv'));
fprintf('max |diff| = %.3f %%p, max stroke diff = %.4f\n', max(abs(T.diff_pp)), ...
        max(abs(T.stroke_script - T.stroke_simulink)));
