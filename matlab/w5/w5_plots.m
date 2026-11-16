%W5_PLOTS  w5_results.mat → 발표용 그림 + 요약표 (5주차 발표/그림)

load(['w5_results' p.tag '.mat']);  L = load(['w5_lookup' p.tag '.mat']);
figdir = fullfile('..','..','5주차 발표','그림',p.figsub);
fn = 'Malgun Gothic';
% S0 = 기준(회색), S1~S4 = 범주 팔레트 1~4번 + 마커로 2중 구분
col = [0.55 0.55 0.53; hex2rgb('#2a78d6'); hex2rgb('#eb6834'); hex2rgb('#1baf7a'); hex2rgb('#eda100')];
mk  = {'o','s','^','d','v'};
lbl = {'S0 사전동작 없음','S1 밸브 프리셋','S2 펌프 재튜닝 (30 s)','S3 밸브+펌프','S4 밸브+공기압 (3 s)'};

% 저감률은 기록 3개 평균, 스트로크는 기록 중 최대 (한 기록이라도 넘으면 위험)
agg = @(c,v) (c==8)*max(v) + (c~=8)*mean(v);
meanOf = @(is,pga,err,k,col_) arrayfun(@(Lt) agg(col_, R(R(:,1)==is & R(:,2)==pga & R(:,5)==err & R(:,6)==k & R(:,4)==Lt, col_)), leads);

%% 그림 1 — 리드타임 vs 저감률 (시나리오 A·B × PGA 0.4·0.6g, 정확한 예보)
for metric = [7 8]
    f = figure('Color','w','Position',[100 100 1100 720]);
    tiledlayout(2,2,'TileSpacing','compact','Padding','compact');
    for is = 1:2
        for pga = [0.4 0.6]
            nexttile; hold on; grid on; box off;
            for k = 1:5
                y = meanOf(is,pga,1,k,metric);
                plot(leads, y, '-', 'Color', col(k,:), 'LineWidth', 2, ...
                     'Marker', mk{k}, 'MarkerSize', 7, 'MarkerFaceColor', col(k,:));
            end
            if metric == 8, yline(1,'--','물기둥 한계','Color',[0.4 0.4 0.4],'FontName',fn); end
            xline(0,':','Color',[0.5 0.5 0.5]);
            ttl = {'A 강성 일정','B 강진 시 강성 저하(가정)'};
            title(sprintf('%s · PGA %.1fg', ttl{is}, pga), 'FontName', fn);
            xlabel('리드타임 [s]  (음수 = 흔들림 뒤 경보)','FontName',fn);
            if metric == 7, ylabel('RMS 변위 저감률 [%]','FontName',fn);
            else,           ylabel('최대 스트로크 이용률 (기록 중 최대)','FontName',fn); end
            set(gca,'FontName',fn,'GridAlpha',0.15,'XTick',leads);
        end
    end
    lg = legend(lbl,'FontName',fn,'Orientation','horizontal','NumColumns',3);
    lg.Layout.Tile = 'north';
    nm = {'','','','','','','w5_fig1_leadtime_reduction.png','w5_fig2_leadtime_stroke.png'};
    exportgraphics(f, fullfile(figdir, nm{metric}), 'Resolution', 200);
end

%% 그림 3 — 리드타임 × 예보 오차 (S1 밸브, 시나리오 A, PGA 0.6g): 최대 스트로크 이용률
f = figure('Color','w','Position',[100 100 820 380]);
G = zeros(numel(errs), numel(leads));
for ie = 1:numel(errs)
    G(ie,:) = meanOf(1,0.6,errs(ie),2,8);
end
imagesc(G); axis tight;
m = max(abs(G(:)-1));  caxis(1 + [-m m]);      % 1.0 = 물기둥 한계가 중립색
neg = hex2rgb('#eb6834'); pos = hex2rgb('#2a78d6'); mid = [0.92 0.92 0.90];
cm = [interp1([0 1],[neg; mid],linspace(0,1,64)); interp1([0 1],[mid; pos],linspace(0,1,64))];
colormap(flipud(cm)); cb = colorbar; cb.Label.String = '최대 스트로크 이용률 (1 초과 = 한계)'; cb.Label.FontName = fn;
set(gca,'XTick',1:numel(leads),'XTickLabel',leads,'YTick',1:numel(errs), ...
    'YTickLabel',{'과소 ×0.5','정확 ×1','과대 ×2'},'FontName',fn);
for ie = 1:numel(errs), for il = 1:numel(leads)
    text(il, ie, sprintf('%.2f', G(ie,il)), 'HorizontalAlignment','center','FontName',fn,'FontSize',9);
end, end
xlabel('리드타임 [s]','FontName',fn); ylabel('예측 PGA','FontName',fn);
s0v = meanOf(1,0.6,1,1,8);  title(sprintf('S1 밸브 프리셋 · 시나리오 A · 실제 PGA 0.6g (사전동작 없으면 %.2f)', s0v(1)),'FontName',fn);
exportgraphics(f, fullfile(figdir,'w5_fig3_error_heatmap.png'), 'Resolution', 200);

%% 그림 4 — 설정표: 예측 PGA → 최적 xi · gamma
f = figure('Color','w','Position',[100 100 900 340]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on; grid on;
plot(L.LTA.pga, L.LTA.best_xi,'-o','Color',col(2,:),'LineWidth',2,'MarkerFaceColor',col(2,:));
plot(L.LTB.pga, L.LTB.best_xi,'--s','Color',col(3,:),'LineWidth',2,'MarkerFaceColor',col(3,:));
set(gca,'YScale','log','FontName',fn); xlabel('예측 PGA [g]'); ylabel('최적 기준 손실계수 \xi');
title(sprintf('밸브 — 최적 \\xi %g ~ %g', min(L.LTA.best_xi), max(L.LTA.best_xi)),'FontName',fn);
nexttile; hold on; grid on;
plot(L.LTA.pga, L.LTA.best_gamma,'-o','Color',col(2,:),'LineWidth',2,'MarkerFaceColor',col(2,:));
plot(L.LTB.pga, L.LTB.best_gamma,'--s','Color',col(3,:),'LineWidth',2,'MarkerFaceColor',col(3,:));
set(gca,'FontName',fn); xlabel('예측 PGA [g]'); ylabel('최적 튜닝비 \gamma');
title(sprintf('펌프 — 최적 \\gamma %.2f ~ %.2f', min([L.LTA.best_gamma L.LTB.best_gamma]), max([L.LTA.best_gamma L.LTB.best_gamma])),'FontName',fn);  ylim([0.86 1.04]);
legend({'A 강성 일정','B 강성 저하(가정)'},'FontName',fn,'Location','southwest');
exportgraphics(f, fullfile(figdir,'w5_fig4_lookup.png'), 'Resolution', 200);

%% 요약 — 필요 리드타임 (60 s 이득의 90% 에 도달하는 최소 리드타임)
fid = fopen(fullfile('..','..','5주차 발표',['w5_summary' p.tag '.txt']),'w','n','UTF-8');
fprintf(fid,'5주차 예측 선제 제어 — 요약 (실측 기록 3개: 저감률 평균, 스트로크 최대, 정확한 예보)\n\n');
for is = 1:2, for pga = pgas
    base = meanOf(is,pga,1,1,7);  s0 = meanOf(is,pga,1,1,8);
    fprintf(fid,'[%s] PGA %.1fg  S0 저감 %.1f%%  stroke %.2f\n', scens{is}, pga, base(1), s0(1));
    for k = 2:5
        y = meanOf(is,pga,1,k,7);  s = meanOf(is,pga,1,k,8);
        gain = y - base;  i90 = find(gain >= 0.9*gain(end), 1);
        if gain(end) <= 0.1, need = '이득 없음'; else, need = sprintf('%g s', leads(i90)); end
        fprintf(fid,'   %-22s 60s: %5.1f%% (S0 대비 %+5.1f%%p), stroke %.2f, 필요 리드타임 %s\n', ...
            lbl{k}, y(end), gain(end), s(end), need);
    end
    fprintf(fid,'\n');
end, end
fclose(fid);
disp('plots + summary written');

function c = hex2rgb(h)
c = sscanf(h(2:end),'%2x%2x%2x',[1 3]) / 255;
end
