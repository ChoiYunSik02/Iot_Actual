function R = compare_papers(quake, pga)
%COMPARE_PAPERS  논문별 건물 모델을 같은 지진파로 돌려 비교합니다.
%
%   R = compare_papers('elcentro', 0.2)
%
%   두 가지를 분리해서 봅니다.
%     ① 제진 성능  — 질량비·길이비·튜닝비로 결정되며 절대 질량과 무관
%     ② 실현 가능성 — 절대 질량과 진동수로 결정되는 관 형상(종횡비 h/D)
%
%   결과 그래프는 fig/ 에 저장됩니다.

if nargin < 1, quake = 'elcentro'; end
if nargin < 2, pga   = 0.2;        end

M = paper_models();
n = numel(M);

fprintf('\n========== 논문별 건물 모델 비교 (%s형 %.2fg) ==========\n', quake, pga);

%% ── ① 형상 역산 ──────────────────────────────────────
fprintf('\n---------- TLCD 형상 (ω=√(2g/L) 로 역산) ----------\n');
fprintf('%-28s %7s %9s %8s %8s %9s %8s %8s\n', ...
        '모델', 'f1[Hz]', '모드질량', 'L[m]', 'h[m]', '액체[ton]', 'D[m]', 'h/D');
for i = 1:n
    if M(i).Mmod < 1000, mstr = sprintf('%.1f kg', M(i).Mmod);
    else,                mstr = sprintf('%.0f ton', M(i).Mmod/1e3); end
    fprintf('%-28s %7.3f %9s %8.3f %8.3f %9.2f %8.2f %8.4f\n', ...
        M(i).name, M(i).f1, mstr, M(i).L, M(i).h, M(i).mf/1e3, M(i).D, M(i).hD);
end
fprintf('\n  h/D = 물기둥 높이 / 관 직경. 작을수록 넓고 얕은 수조에 가깝습니다.\n');

%% ── ② 동일 지진파 시뮬레이션 ─────────────────────────
fprintf('\n---------- 제진 성능 (동일 지진파) ----------\n');
fprintf('%-28s %10s %10s %10s %10s\n', '모델', 'RMS저감[%]', '최대저감[%]', '물기둥[mm]', '사용률');
R = struct();
for i = 1:n
    [p, b] = build_sdof(M(i).f1, M(i).zeta, M(i).Mmod, M(i).mu, M(i).alpha, M(i).xi);
    p.T = 30;
    t  = (0:p.dt:p.T)';
    ag = gen_ground(quake, pga, p.dt, p.T);

    o0 = simulate_tlcd(p, b, t, ag, 'none');
    o1 = simulate_tlcd(p, b, t, ag, 'passive');

    R(i).name    = M(i).name;
    R(i).red_rms = (1 - o1.rms_disp/o0.rms_disp)*100;
    R(i).red_pk  = (1 - o1.peak_disp/o0.peak_disp)*100;
    R(i).xf      = o1.peak_xf;
    R(i).use     = o1.stroke_use;
    R(i).hD      = M(i).hD;
    R(i).f1      = M(i).f1;
    R(i).Mmod    = M(i).Mmod;
    R(i).scale   = M(i).scale;

    mark = '';
    if R(i).use > 1.0, mark = '  <-- 포화'; end
    fprintf('%-28s %10.1f %10.1f %10.1f %10.2f%s\n', ...
        M(i).name, R(i).red_rms, R(i).red_pk, R(i).xf*1000, R(i).use, mark);
end

fprintf('\n  ※ 저감률은 질량비·길이비로 결정되므로 축소모형과 실물이 비슷하게 나옵니다.\n');
fprintf('    차이는 성능이 아니라 "그 형상을 실제로 만들 수 있는가"에서 갈립니다.\n');

%% ── 그래프 ───────────────────────────────────────────
if ~exist('fig','dir'), mkdir fig; end
CD = [0.047 0.204 0.239]; CM = [0 0.765 0.694]; CR = [0.80 0.255 0.145];
CW = [0.55 0.78 0.92];

fh = figure('Visible','off','Position',[60 60 1250 820]);

% (a) 관 형상 — 각 모델을 같은 폭으로 정규화해 종횡비만 비교
subplot(2,2,[1 2]); hold on; axis equal off;
xoff = 0;
for i = 1:n
    w = 1.0;                       % 정규화 폭
    ht = max(0.02, M(i).hD) * 6;   % 종횡비를 높이로 환산(보기용 6배)
    ht = min(ht, 3.2);
    % 관 외곽
    plot(xoff+[0 0 w w], [ht 0 0 ht], '-', 'Color', CD, 'LineWidth', 2);
    % 물
    patch(xoff+[0 w w 0], [0 0 ht*0.55 ht*0.55], CW, 'EdgeColor','none');
    text(xoff+w/2, -0.28, sprintf('h/D = %.3f', M(i).hD), ...
         'HorizontalAlignment','center','FontSize',10,'FontWeight','bold', ...
         'Color', tern(M(i).hD < 0.02, CR, CD));
    nm = strrep(M(i).name, ' (', sprintf('\n('));
    text(xoff+w/2, -0.62, nm, 'HorizontalAlignment','center','FontSize',9,'Color',CD);
    xoff = xoff + w + 0.55;
end
title('관 형상 비교 — 종횡비 h/D (폭을 같게 정규화)', 'FontSize',13,'Color',CD);
ylim([-1.1 3.4]);

% (b) 저감률
subplot(2,2,3);
bar([R.red_rms], 'FaceColor', CM, 'EdgeColor','none'); grid on;
set(gca,'XTickLabel', 1:n); xlabel('모델 번호'); ylabel('RMS 저감률 [%]');
title(sprintf('제진 성능 (%s형 %.2fg)', quake, pga), 'FontSize',12,'Color',CD);

% (c) 실현 가능성 — 종횡비
subplot(2,2,4);
hb = bar([R.hD], 'FaceColor', CD, 'EdgeColor','none'); grid on; hold on;
yline(0.02, '--', 'Color', CR, 'LineWidth',1.5);
set(gca,'XTickLabel', 1:n); xlabel('모델 번호'); ylabel('종횡비 h/D [-]');
title('실현 가능성 — 클수록 관다운 형상', 'FontSize',12,'Color',CD);

fn = sprintf('fig/compare_papers_%s_%.2fg.png', quake, pga);
exportgraphics(fh, fn, 'Resolution', 150); close(fh);
fprintf('\n그래프 저장: %s\n', fn);
end

function y = tern(c,a,b)
if c, y = a; else, y = b; end
end
