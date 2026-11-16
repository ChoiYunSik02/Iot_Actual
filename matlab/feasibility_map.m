function feasibility_map()
%FEASIBILITY_MAP  TLCD 실현 가능성 지도
%
%   가로축 = 건물 1차 진동수, 세로축 = 1차 모드질량
%   등고선 = 종횡비 h/D (물기둥 높이 / 관 직경)
%
%   왜 이 지도가 필요한가
%     제진 성능은 질량비로 결정되어 축소모형이든 실물이든 비슷하게 나옵니다.
%     갈리는 것은 "그 형상을 실제로 만들 수 있는가"이고, 그것은 진동수와
%     절대 질량이 함께 정합니다. 이 두 축을 한 장에 놓고 봅니다.
%
%   기준선
%     논문에 실린 실물 사례가 h/D = 0.025 (JIPR 2026), 0.038 (JOBE 2025) 이므로
%     0.02 부근을 실물 하한으로 봅니다. 그보다 작으면 관이 아니라 얕은 수조입니다.

g = 9.81; rho = 1000;
mu_ref = 0.05; alpha_ref = 0.80;   % 등고선 기준 (본 연구 설계값)

f = logspace(log10(0.2), log10(3.0), 260);      % 0.2 ~ 3 Hz
Mm = logspace(log10(10), log10(3e7), 260);      % 10 kg ~ 30,000 ton
[F, MM] = meshgrid(f, Mm);

L  = 2*g ./ (2*pi*F).^2;
h  = (1 - alpha_ref) * L / 2;
A  = (mu_ref * MM) ./ (rho * L);
D  = 2*sqrt(A/pi);
hD = h ./ D;

M = paper_models();

CD = [0.047 0.204 0.239]; CM = [0 0.765 0.694]; CR = [0.80 0.255 0.145];

fh = figure('Visible','off','Position',[60 60 1150 760]);
ax = axes; hold(ax,'on');

lv = [0.005 0.01 0.02 0.05 0.1 0.2 0.5 1.0];
[C, hc] = contourf(F, MM, hD, lv, 'LineColor',[1 1 1], 'LineWidth',0.6);
set(ax,'XScale','log','YScale','log','ColorScale','log');
clabel(C, hc, lv, 'FontSize',9, 'Color',[0.15 0.15 0.15], 'LabelSpacing', 320);
colormap(ax, flipud(bone));
cb = colorbar; cb.Label.String = '종횡비 h/D  (클수록 관다운 형상)';

% 실물 하한선 0.02
[C2, h2] = contour(F, MM, hD, [0.02 0.02], 'Color', CR, 'LineWidth', 2.4);
clabel(C2, h2, 'FontSize',10, 'Color',CR, 'FontWeight','bold');

% 논문·본 연구 모델 표시
for i = 1:numel(M)
    isOur = contains(M(i).name, '본 연구');
    col = CR * isOur + CM * (~isOur);
    plot(M(i).f1, M(i).Mmod, 'o', 'MarkerSize',11, 'LineWidth',2, ...
         'MarkerEdgeColor','w', 'MarkerFaceColor', col);
    lbl = sprintf('%s\nh/D=%.3f  (\\mu=%.0f%%)', M(i).short, M(i).hD, M(i).mu*100);
    if M(i).f1 > 1.05
        ha = 'right'; dx = 0.93;
    else
        ha = 'left';  dx = 1.07;
    end
    va = 'middle'; dy = 1.0;
    if M(i).Mmod < 100,  va = 'bottom'; dy = 2.2; end    % 축소모형 라벨은 위로
    if M(i).Mmod > 1e7,  va = 'top';    dy = 0.72; end   % 최상단 라벨은 아래로
    text(M(i).f1*dx, M(i).Mmod*dy, lbl, 'FontSize',9.5, 'Color',CD, ...
         'HorizontalAlignment', ha, 'VerticalAlignment', va, 'FontWeight','bold', ...
         'BackgroundColor','w', 'Margin',1.5);
end

xlabel('건물 1차 고유진동수 [Hz]'); ylabel('1차 모드질량 [kg]');
title({'TLCD 실현 가능성 지도', ...
       sprintf('등고선: 종횡비 h/D (기준 \\mu=%.0f%%, \\alpha=%.1f) · 빨간선 = 실물 하한 0.02', ...
               mu_ref*100, alpha_ref)}, 'FontSize',13, 'Color',CD);
grid on; box on;
xlim([0.2 3.0]); ylim([10 3e7]);

if ~exist('fig','dir'), mkdir fig; end
exportgraphics(fh, 'fig/feasibility_map.png', 'Resolution', 150);
close(fh);

fprintf('\n========== 실현 가능성 지도 ==========\n');
fprintf('%-28s %8s %12s %9s %s\n','모델','f1[Hz]','모드질량[t]','h/D','판정');
for i = 1:numel(M)
    if M(i).hD >= 0.05,     v = '여유';
    elseif M(i).hD >= 0.02, v = '실물 사례 수준';
    else,                   v = '불가 — 얕은 수조';
    end
    fprintf('%-28s %8.3f %12.1f %9.4f %s\n', M(i).name, M(i).f1, M(i).Mmod/1e3, M(i).hD, v);
end
fprintf('\n그래프 저장: fig/feasibility_map.png\n');
end
