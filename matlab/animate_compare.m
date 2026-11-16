function animate_compare(idx, quake, pga, opt)
%ANIMATE_COMPARE  논문별 건물 모델을 나란히 애니메이션으로 비교합니다.
%
%   animate_compare                         기본: [1 2 4] (축소모형·JIPR·우리 3층)
%   animate_compare([1 2 4], 'pohang', 0.2)
%   animate_compare([1 2 4], 'pohang', 0.2, struct('save',true))
%
%   idx : paper_models() 의 모델 번호 벡터 (2~4개)
%
%   각 모델마다
%     · 건물이 흔들리는 모습 (변위 확대)
%     · U자관 — 실제 종횡비 h/D 를 반영해 그립니다 (납작한 정도가 그대로 보임)
%     · 물이 한계에 닿으면 빨갛게 바뀌며 "포화" 표시
%   아래에는 최상층 변위 시간이력을 함께 그립니다.

if nargin < 1 || isempty(idx),   idx   = [1 2 4];  end
if nargin < 2 || isempty(quake), quake = 'pohang'; end
if nargin < 3 || isempty(pga),   pga   = 0.2;      end
if nargin < 4, opt = struct(); end
if ~isfield(opt,'save'),  opt.save  = false; end
if ~isfield(opt,'Tshow'), opt.Tshow = 12;    end
if ~isfield(opt,'fps'),   opt.fps   = 25;    end

M = paper_models();
nm = numel(idx);
assert(nm >= 2 && nm <= 4, 'idx 는 2~4개여야 합니다');

CD = [0.047 0.204 0.239]; CM = [0 0.765 0.694]; CR = [0.80 0.255 0.145];
CW = [0.55 0.78 0.92];    CG = [0.60 0.63 0.63];

%% ── 각 모델 시뮬레이션 ─────────────────────────────
S = struct();
for j = 1:nm
    m = M(idx(j));
    [p, b] = build_sdof(m.f1, m.zeta, m.Mmod, m.mu, m.alpha, m.xi);
    p.T = opt.Tshow;
    t  = (0:p.dt:p.T)';
    ag = gen_ground(quake, pga, p.dt, p.T);
    o0 = simulate_tlcd(p, b, t, ag, 'none');
    o1 = simulate_tlcd(p, b, t, ag, 'passive');
    S(j).m = m; S(j).t = t; S(j).ag = ag;
    S(j).x0 = o0.top; S(j).x1 = o1.top;
    S(j).xf = o1.xf;  S(j).lim = o1.stroke_max;
    S(j).red = (1 - o1.rms_disp/o0.rms_disp)*100;
    S(j).scale = 0.9 / max(abs(o1.top));     % 각 모델 변위를 같은 크기로 정규화
    fprintf('%-28s RMS 저감 %5.1f%% | 물기둥 %6.1f mm / 한계 %6.1f mm | h/D %.4f\n', ...
        m.name, S(j).red, max(abs(o1.xf))*1000, o1.stroke_max*1000, m.hD);
end
t = S(1).t;

%% ── 도형 준비 ──────────────────────────────────────
fh = figure('Color','w','Position',[60 50 340*nm+120 800], ...
            'Visible', tern(opt.save,'off','on'));
ax = axes('Position',[0.04 0.36 0.92 0.58]); hold(ax,'on');
axis(ax,'equal'); set(ax,'XTick',[],'YTick',[],'XColor','none','YColor','none');
W = 6; GAP = 3.6;                       % 모델 간 간격
xlim(ax, [-2, nm*(W+GAP)]); ylim(ax, [-2.6 10.5]);

H = struct();
for j = 1:nm
    x0 = (j-1)*(W+GAP);
    % 지반
    H.gnd(j) = plot(ax, x0+[-1 W+1], [0 0], '-', 'Color',CG, 'LineWidth',3);
    % 건물 기둥 2개 + 슬래브
    H.cL(j) = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2.5);
    H.cR(j) = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2.5);
    H.slab(j) = patch(ax, nan, nan, CD, 'EdgeColor','none');
    % U자관 — 폭은 동일, 높이는 실제 종횡비 h/D 반영
    H.tube(j) = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2);
    H.wL(j) = patch(ax, nan, nan, CW, 'EdgeColor','none');
    H.wR(j) = patch(ax, nan, nan, CW, 'EdgeColor','none');
    H.wB(j) = patch(ax, nan, nan, CW, 'EdgeColor','none');
    H.lim(j) = plot(ax, nan, nan, '--', 'Color',CR, 'LineWidth',1.2);
    % 라벨
    text(ax, x0+W/2, -1.3, S(j).m.short, 'HorizontalAlignment','center', ...
         'FontSize',11,'FontWeight','bold','Color',CD);
    text(ax, x0+W/2, -2.15, sprintf('h/D = %.3f   RMS 저감 %.0f%%', S(j).m.hD, S(j).red), ...
         'HorizontalAlignment','center','FontSize',9.5, ...
         'Color', tern(S(j).m.hD < 0.02, CR, CD));
    H.sat(j) = text(ax, x0+W/2, 9.7, '', 'HorizontalAlignment','center', ...
                    'FontSize',11,'FontWeight','bold','Color',CR);
end
title(ax, sprintf('%s형 지진파 %.2fg — 건물 변위는 모델별로 정규화, U자관은 실제 종횡비', quake, pga), ...
      'FontSize',12.5,'Color',CD);

%% ── 하단 시간이력 ──────────────────────────────────
ax2 = axes('Position',[0.07 0.07 0.88 0.21]); hold(ax2,'on'); grid(ax2,'on');
cols = [CR; CM; CD; CG];
for j = 1:nm
    plot(ax2, t, S(j).x1*1000, '-', 'Color', cols(min(j,4),:), 'LineWidth',1.1);
end
H.mk = plot(ax2, nan, nan, 'ko', 'MarkerFaceColor','k', 'MarkerSize',6);
H.vl = plot(ax2, [nan nan], [nan nan], '-', 'Color',[0 0 0 0.25]);
xlabel(ax2,'시간 [s]'); ylabel(ax2,'최상층 변위 [mm]');
lgd = cell(1, nm);
for j = 1:nm, lgd{j} = strrep(S(j).m.short, sprintf('\n'), ' '); end
legend(ax2, lgd, 'Location','northeast','Orientation','horizontal','FontSize',8);
xlim(ax2,[0 t(end)]);

%% ── 저장 준비 ──────────────────────────────────────
useVideo = false;
if opt.save
    if ~exist('fig','dir'), mkdir fig; end
    try
        vw = VideoWriter(sprintf('fig/anim_compare_%s_%.2fg.mp4', quake, pga), 'MPEG-4');
        vw.FrameRate = opt.fps; open(vw); useVideo = true;
    catch
        useVideo = false;
    end
end

%% ── 애니메이션 ─────────────────────────────────────
dt = t(2)-t(1);
step = max(1, round(1/(opt.fps*dt)));
hf = 3.0;                                % 건물 층고(그림)
for i = 1:step:numel(t)
    for j = 1:nm
        x0 = (j-1)*(W+GAP);
        xg = S(j).ag(i)/9.81 * 0.5;
        d  = S(j).x1(i) * S(j).scale;    % 정규화 변위
        % 건물
        set(H.gnd(j), 'XData', x0+xg+[-1 W+1], 'YData',[0 0]);
        set(H.cL(j), 'XData', x0+xg+[0 d], 'YData',[0 hf*2]);
        set(H.cR(j), 'XData', x0+xg+[W W+d], 'YData',[0 hf*2]);
        set(H.slab(j), 'XData', x0+xg+d+[0 W W 0], 'YData', hf*2+[-0.2 -0.2 0.2 0.2]);
        % U자관 — 폭 Wt 고정, 물기둥 높이는 h/D 에 비례
        Wt = W*0.62;  xc = x0+xg+d+W/2;  yb = hf*2+0.2;
        hh = max(0.22, min(3.0, S(j).m.hD*7));       % 종횡비 → 그림 높이
        xl = xc-Wt/2; xr = xc+Wt/2;  tw = Wt*0.30;
        set(H.tube(j), 'XData', [xl-tw/2 xl-tw/2 xr+tw/2 xr+tw/2], ...
                       'YData', [yb+hh*2.2 yb yb yb+hh*2.2]);
        u  = S(j).xf(i)/S(j).lim;                    % -1~1 정규화
        uL = max(0, min(hh*2.1, hh*(1-u)));
        uR = max(0, min(hh*2.1, hh*(1+u)));
        set(H.wL(j), 'XData',[xl-tw/2 xl+tw/2 xl+tw/2 xl-tw/2], 'YData',[yb yb yb+uL yb+uL]);
        set(H.wR(j), 'XData',[xr-tw/2 xr+tw/2 xr+tw/2 xr-tw/2], 'YData',[yb yb yb+uR yb+uR]);
        set(H.wB(j), 'XData',[xl-tw/2 xr+tw/2 xr+tw/2 xl-tw/2], 'YData',[yb yb yb+hh*0.28 yb+hh*0.28]);
        set(H.lim(j), 'XData',[xl-tw xr+tw], 'YData',(yb+hh*2)*[1 1]);
        if abs(u) >= 0.999
            set(H.wL(j),'FaceColor',CR); set(H.wR(j),'FaceColor',CR);
            set(H.sat(j),'String','포화');
        else
            set(H.wL(j),'FaceColor',CW); set(H.wR(j),'FaceColor',CW);
            set(H.sat(j),'String','');
        end
    end
    set(H.mk, 'XData', t(i), 'YData', S(1).x1(i)*1000);
    set(H.vl, 'XData',[t(i) t(i)], 'YData', ylim(ax2));
    drawnow limitrate;
    if useVideo, writeVideo(vw, getframe(fh)); end
    if isfield(opt,'snapshot') && any(abs(t(i)-opt.snapshot) < dt*step/2)
        exportgraphics(fh, sprintf('fig/snap_compare_t%.2f.png', t(i)), 'Resolution',130);
        fprintf('정지 이미지 저장: fig/snap_compare_t%.2f.png\n', t(i));
    end
end

if useVideo
    close(vw);
    fprintf('\n동영상 저장: %s\n', vw.Filename);
end
if opt.save, close(fh); end
end

function y = tern(c,a,b)
if c, y = a; else, y = b; end
end
