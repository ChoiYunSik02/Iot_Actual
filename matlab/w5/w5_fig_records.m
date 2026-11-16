%W5_FIG_RECORDS  실측 기록과 P파 · S파 · 현장 센서 경보 시각 (발표용)
%
%   P파 도착 = 진앙거리 / 6.0 km/s,  S파 도착 = 진앙거리 / 3.5 km/s
%   현장 센서 경보 = P파 + 4.5 s (논문 17: P파 후 4~5 s)

addpath('..');
p = w5_params();
fn = 'Malgun Gothic';
recs = {'pohang','gyeongju'};
ttl  = {'포항 2017 ML5.4 — 부산 관측소 (98 km)','경주 2016 ML5.8 — 부산 관측소 (58 km)'};
f = figure('Color','w','Position',[100 100 1100 520]);
tiledlayout(2,1,'TileSpacing','compact','Padding','compact');
for i = 1:2
    [ag, t, info] = w5_record(recs{i}, 1, p.dt, p.T);      % 형태만 보이도록 PGA 1로 정규화
    tP = info.dist/6.0;  tS = info.tS;  tA = tP + 4.5;
    nexttile; hold on; box off;
    plot(t, ag/9.81, 'Color', [0.35 0.35 0.33], 'LineWidth', 0.8);
    xline(tP, '-',  sprintf('P파 %.1f s', tP), 'Color', [0.165 0.471 0.839], 'LineWidth', 1.5, 'FontName', fn);
    xline(tA, '--', sprintf('현장 경보 %.1f s', tA), 'Color', [0.106 0.686 0.478], 'LineWidth', 1.5, 'FontName', fn, 'LabelVerticalAlignment','middle');
    xline(tS, '-',  sprintf('S파 %.1f s', tS), 'Color', [0.922 0.408 0.204], 'LineWidth', 1.5, 'FontName', fn);
    title(sprintf('%s  ·  현장 센서 리드타임 %.1f s', ttl{i}, tS - tA), 'FontName', fn);
    ylabel('정규화 가속도', 'FontName', fn);  xlim([0 50]);
    set(gca, 'FontName', fn);
end
xlabel('진원시부터 시간 [s]', 'FontName', fn);
exportgraphics(f, fullfile('..','..','5주차 발표','그림','w5_fig0_records.png'), 'Resolution', 200);
