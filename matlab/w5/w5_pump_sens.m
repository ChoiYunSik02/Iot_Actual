%W5_PUMP_SENS  펌프 속도에 따라 필요 리드타임이 어떻게 바뀌는가 (시나리오 B, S2)
%
%   w5_main 의 펌프 속도 30 s 는 가정값이라, 30 / 60 / 120 / 300 s 로 바꿔 봅니다.

addpath('..');
if ~exist('AXES','var'), AXES = 1; end
[p, ~, tl] = w5_params(AXES);
S = load(['w5_lookup' p.tag '.mat']);  LT = S.LTB;
recs  = {'gyeongju','pohang','elcentro'};
leads = [-3 0 2 5 10 15 30 45 60 90 120];
Tp    = [30 60 120 300];
pga   = 0.6;
g_span = diff(p.gamma_range);
xi0 = interp1(S.LTA.pga, S.LTA.best_xi, 0.2);
g1  = interp1(LT.pga, LT.best_gamma, pga);
g0  = interp1(S.LTA.pga, S.LTA.best_gamma, 0.2);   % 기본 튜닝비 = 0.2g 최적값

b = w5_building(p, pga, 'B');
red = zeros(numel(Tp), numel(leads));  red0 = 0;
for ir = 1:numel(recs)
    [ag, t, info] = w5_record(recs{ir}, pga, p.dt, p.T, p.axes);  t = t(:)';  N = numel(t);  tS = info.tS;
    U  = w5_simulate(p,b,tl,t,ag,[],[],false).rms_disp;
    o0 = w5_simulate(p,b,tl,t,ag,g0*ones(1,N),xi0*ones(1,N),true);
    red0 = red0 + 100*(1-o0.rms_disp/U)/numel(recs);
    for ip = 1:numel(Tp), for il = 1:numel(leads)
        gam = w5_setting(t,tS,leads(il),g0,g1,g_span/Tp(ip));
        o = w5_simulate(p,b,tl,t,ag,gam,xi0*ones(1,N),true);
        red(ip,il) = red(ip,il) + 100*(1-o.rms_disp/U)/numel(recs);
    end, end
end
save(['w5_pump_sens' p.tag '.mat'],'red','red0','leads','Tp');

fn = 'Malgun Gothic';
col = [0.165 0.471 0.839; 0.922 0.408 0.204; 0.106 0.686 0.478; 0.929 0.631 0];
mk = {'o','s','^','d'};
f = figure('Color','w','Position',[100 100 900 420]); hold on; grid on; box off;
yline(red0,'--','S0 사전동작 없음','Color',[0.5 0.5 0.5],'FontName',fn,'LabelHorizontalAlignment','left');
for ip = 1:numel(Tp)
    plot(leads, red(ip,:), '-', 'Color', col(ip,:), 'LineWidth', 2, 'Marker', mk{ip}, ...
         'MarkerSize', 7, 'MarkerFaceColor', col(ip,:));
end
xline(0,':','Color',[0.5 0.5 0.5]);
legend([{'S0'}, arrayfun(@(x) sprintf('펌프 전 범위 %d s',x), Tp, 'UniformOutput', false)], ...
       'FontName',fn,'Location','east');
xlabel('리드타임 [s]','FontName',fn); ylabel('RMS 변위 저감률 [%]','FontName',fn);
title('펌프 속도별 리드타임과 저감률 (S2 · 시나리오 B · PGA 0.6g)','FontName',fn);
set(gca,'FontName',fn,'XTick',leads,'GridAlpha',0.15);
exportgraphics(f, fullfile('..','..','5주차 발표','그림',p.figsub,'w5_fig5_pump_speed.png'), 'Resolution', 200);

for ip = 1:numel(Tp)
    gain = red(ip,:) - red0;  i90 = find(gain >= 0.9*gain(end), 1);
    fprintf('T_pump %3d s : gain@120s %+5.2f%%p, need %g s\n', Tp(ip), gain(end), leads(i90));
end
