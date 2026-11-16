function R = main_stage2(preset, quakes)
%MAIN_STAGE2  2단계 — PGA 스윕으로 "성능 절벽"을 찾습니다.
%
%   R = main_stage2('10F', {'gyeongju','pohang','elcentro'})
%
%   지진 세기를 0.05g에서 0.5g까지 올리며
%     · RMS 저감률
%     · 물기둥 사용률 (1.0 초과 = 포화)
%     · 포화 시간 비율
%   을 기록하고, 저감률이 꺾이는 지점을 절벽으로 판정합니다.

if nargin < 1, preset = '10F'; end
if nargin < 2, quakes = {'gyeongju','pohang','elcentro'}; end

pgas = [0.05 0.075 0.1 0.15 0.2 0.25 0.3 0.375 0.45 0.5];

p = params(preset);
b = build_building(p);
t = (0:p.dt:p.T)';

fprintf('\n========== 2단계 : 포화 한계 탐색 (%s) ==========\n', preset);
tl = tlcd_design(p, b);
fprintf('스트로크 한계 h = %.1f cm\n', tl.h*100);

R = struct();
for q = 1:numel(quakes)
    kind = quakes{q};
    red = zeros(size(pgas));  use = zeros(size(pgas));  sat = zeros(size(pgas));
    for i = 1:numel(pgas)
        ag = gen_ground(kind, pgas(i), p.dt, p.T);
        o0 = simulate_tlcd(p, b, t, ag, 'none');
        o1 = simulate_tlcd(p, b, t, ag, 'passive');
        red(i) = (1 - o1.rms_disp/o0.rms_disp)*100;
        use(i) = o1.stroke_use;
        sat(i) = o1.sat_ratio*100;
    end
    R.(kind) = struct('pga',pgas,'red',red,'use',use,'sat',sat);

    fprintf('\n---------- %s형 ----------\n', kind);
    fprintf('%8s %12s %12s %12s\n','PGA[g]','RMS저감[%]','물기둥사용률','포화시간[%]');
    for i = 1:numel(pgas)
        mark = '';
        if use(i) > 1.0, mark = '  <-- 포화'; end
        fprintf('%8.3f %12.1f %12.2f %12.1f%s\n', pgas(i), red(i), use(i), sat(i), mark);
    end

    % 절벽 판정: 저감률이 최댓값 대비 20% 이상 떨어지기 시작하는 첫 지점
    [rmax, imax] = max(red);
    icliff = find(red(imax:end) < rmax*0.8, 1) + imax - 1;
    if isempty(icliff)
        fprintf('  → 검토 범위(최대 %.2fg) 내에서 절벽 미발생\n', max(pgas));
    else
        fprintf('  → 성능 절벽: PGA %.3fg 부근 (최대 저감 %.1f%% → %.1f%%)\n', ...
                pgas(icliff), rmax, red(icliff));
    end
end

%% 그래프
if ~exist('fig','dir'), mkdir fig; end
cols = [.75 .25 .15; 0 .76 .69; .05 .20 .24];
fh = figure('Visible','off','Position',[100 100 1000 700]);

subplot(2,1,1); hold on; grid on;
for q = 1:numel(quakes)
    d = R.(quakes{q});
    plot(d.pga, d.red, '-o', 'Color', cols(q,:), 'LineWidth',1.6, 'MarkerSize',5);
end
ylabel('RMS 저감률 [%]'); legend(quakes,'Location','southwest');
title(sprintf('성능 절벽 탐색 — %s (스트로크 한계 %.1f cm)', preset, tl.h*100));

subplot(2,1,2); hold on; grid on;
for q = 1:numel(quakes)
    d = R.(quakes{q});
    plot(d.pga, d.use, '-o', 'Color', cols(q,:), 'LineWidth',1.6, 'MarkerSize',5);
end
yline(1.0,'r--','LineWidth',1.4);
xlabel('PGA [g]'); ylabel('물기둥 사용률 [-]');
legend([quakes, {'포화 한계'}],'Location','northwest');

fn = sprintf('fig/stage2_cliff_%s.png', preset);
exportgraphics(fh, fn, 'Resolution', 150);
close(fh);
fprintf('\n그래프 저장: %s\n', fn);
end
