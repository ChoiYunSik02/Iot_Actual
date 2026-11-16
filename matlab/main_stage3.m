function R = main_stage3(preset, quake, pga)
%MAIN_STAGE3  3단계 — 제어 지연 스윕
%
%   R = main_stage3('10F', 'pohang', 0.2)
%
%   준능동 밸브 제어의 계측 지연을 0에서 200ms까지 늘리며
%   성능이 어디서부터 무너지는지 찾습니다.
%   비교 기준: 무제어 · 고정 TLCD(지연 무관) · 준능동(지연 있음)

if nargin < 1, preset = '10F';   end
if nargin < 2, quake  = 'pohang'; end
if nargin < 3, pga    = 0.2;      end

delays = [0 5 10 20 30 50 75 100 150 200] / 1000;   % [s]

p  = params(preset);
b  = build_building(p);
t  = (0:p.dt:p.T)';
ag = gen_ground(quake, pga, p.dt, p.T);

o0 = simulate_tlcd(p, b, t, ag, 'none');
o1 = simulate_tlcd(p, b, t, ag, 'passive');
base_red = (1 - o1.rms_disp/o0.rms_disp)*100;

fprintf('\n========== 3단계 : 제어 지연 영향 (%s, %s형 %.2fg) ==========\n', ...
        preset, quake, pga);
fprintf('무제어 RMS         : %.2f mm\n', o0.rms_disp*1000);
fprintf('고정 TLCD RMS      : %.2f mm  (저감 %.1f%%)  ← 지연과 무관한 기준선\n', ...
        o1.rms_disp*1000, base_red);

red = zeros(size(delays));  stab = true(size(delays));
fprintf('\n%10s %12s %12s %14s\n','지연[ms]','RMS[mm]','RMS저감[%]','고정대비[%p]');
for i = 1:numel(delays)
    pd = p;  pd.delay = delays(i);
    o2 = simulate_tlcd(pd, b, t, ag, 'semiactive');
    red(i) = (1 - o2.rms_disp/o0.rms_disp)*100;
    stab(i) = isfinite(o2.rms_disp) && o2.rms_disp < 10*o0.rms_disp;
    mark = '';
    if ~stab(i),                 mark = '  <-- 발산';
    elseif red(i) < base_red,    mark = '  <-- 고정보다 나쁨';
    end
    fprintf('%10.0f %12.2f %12.1f %14.1f%s\n', delays(i)*1000, ...
            o2.rms_disp*1000, red(i), red(i)-base_red, mark);
end

% 허용 지연: 준능동이 고정 TLCD보다 나은 마지막 지점
iok = find(red >= base_red, 1, 'last');
if isempty(iok)
    fprintf('\n  → 준능동이 고정 TLCD를 이기는 구간 없음 (제어 법칙 재검토 필요)\n');
else
    fprintf('\n  → 허용 최대 지연 : 약 %.0f ms\n', delays(iok)*1000);
    fprintf('    이보다 큰 지연에서는 밸브를 고정해 두는 편이 낫습니다.\n');
end

%% 그래프
if ~exist('fig','dir'), mkdir fig; end
fh = figure('Visible','off','Position',[100 100 900 500]);
plot(delays*1000, red, '-o', 'Color',[.05 .20 .24], 'LineWidth',1.8, 'MarkerSize',6);
hold on; grid on;
yline(base_red, '--', 'Color',[0 .76 .69], 'LineWidth',1.6);
xlabel('제어 지연 [ms]'); ylabel('RMS 저감률 [%]');
legend('준능동 TLCD','고정 TLCD 기준선','Location','southwest');
title(sprintf('제어 지연 영향 — %s, %s형 %.2fg', preset, quake, pga));
fn = sprintf('fig/stage3_delay_%s_%s.png', preset, quake);
exportgraphics(fh, fn, 'Resolution', 150);
close(fh);
fprintf('\n그래프 저장: %s\n', fn);

R = struct('delays',delays,'red',red,'base_red',base_red,'stable',stab);
end
