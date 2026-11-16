function animate_tlcd(preset, quake, pga, opt)
%ANIMATE_TLCD  건물 흔들림과 U자관 물기둥 거동을 애니메이션으로 보여줍니다.
%
%   animate_tlcd                                  기본값으로 실행
%   animate_tlcd('10F','pohang',0.2)
%   animate_tlcd('10F','pohang',0.2, struct('save',true))
%
%   opt 필드
%     .save    true면 GIF/동영상 파일로 저장 (기본 false = 화면 재생)
%     .scale   변위 확대배율 (기본 15) — 실제 변위는 눈에 안 보일 만큼 작습니다
%     .Tshow   보여줄 시간 [s] (기본 15)
%     .fps     초당 프레임 (기본 25)
%
%   왼쪽은 무제어, 오른쪽은 TLCD 설치 건물입니다.
%   옥상 U자관의 물이 건물과 반대 위상으로 움직이는 것을 확인하세요.
%   물이 빨간 한계선에 닿으면 포화 — 감쇠기가 기능을 잃는 순간입니다.

if nargin < 1 || isempty(preset), preset = '10F';   end
if nargin < 2 || isempty(quake),  quake  = 'pohang'; end
if nargin < 3 || isempty(pga),    pga    = 0.2;      end
if nargin < 4, opt = struct(); end
if ~isfield(opt,'save'),  opt.save  = false; end
if ~isfield(opt,'scale'), opt.scale = 15;    end
if ~isfield(opt,'Tshow'), opt.Tshow = 15;    end
if ~isfield(opt,'fps'),   opt.fps   = 25;    end

%% ── 시뮬레이션 ─────────────────────────────────────────
p  = params(preset);
p.T = opt.Tshow;
b  = build_building(p);
tl = tlcd_design(p, b);
t  = (0:p.dt:p.T)';
ag = gen_ground(quake, pga, p.dt, p.T);

o0 = simulate_tlcd(p, b, t, ag, 'none');
o1 = simulate_tlcd(p, b, t, ag, 'passive');

fprintf('\n무제어  최대변위 %.1f mm | TLCD %.1f mm | 저감 %.1f%%\n', ...
        o0.peak_disp*1000, o1.peak_disp*1000, ...
        (1-o1.rms_disp/o0.rms_disp)*100);
fprintf('물기둥 사용률 %.2f (1.0 넘으면 포화)\n', o1.stroke_use);

%% ── 색상 (팀 디자인 시스템) ────────────────────────────
CD = [0.047 0.204 0.239];   % 딥틸
CM = [0.000 0.765 0.694];   % 민트
CR = [0.800 0.255 0.145];   % 코랄
CG = [0.55  0.58  0.58];    % 회색
CW = [0.35  0.70  0.95];    % 물색

%% ── 건물 도면 치수 (m) ─────────────────────────────────
hf = 3.0;                   % 층고
wb = 6.0;                   % 건물 폭
S  = opt.scale;             % 변위 확대배율

% U자관: 실제 치수를 쓰되 수직부는 물 높이의 2.5배로 그려 여유를 보여줍니다
Bq = tl.B;  hq = tl.h;
tubeH = 2.5*hq;
tw = 0.35;                  % 관 두께(그림용)

%% ── 프레임 인덱스 ──────────────────────────────────────
step = max(1, round(1/(opt.fps*p.dt)));
idx  = 1:step:numel(t);

%% ── 도형 준비 ──────────────────────────────────────────
fh = figure('Color','w','Position',[80 60 1280 760], ...
            'Visible', tern(opt.save,'off','on'));

ax = axes('Position',[0.03 0.34 0.64 0.60]);
hold(ax,'on'); axis(ax,'equal'); grid(ax,'off');
xlim(ax, [-10 24]); ylim(ax, [-1.5 13.5]);
set(ax,'XTick',[],'YTick',[],'Box','off','XColor','none','YColor','none');

xoff = [0, 14];             % 좌: 무제어, 우: TLCD
lbl  = {'무제어', 'TLCD 설치'};

H = struct();
for k = 1:2
    % 지반
    H.gnd(k) = plot(ax, xoff(k)+[-4 10], [0 0], '-', 'Color',CG, 'LineWidth',3);
    % 기둥 2개
    H.colL(k) = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2.5);
    H.colR(k) = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2.5);
    % 바닥판 3개
    for f = 1:3
        H.slab(k,f) = patch(ax, nan, nan, CD, 'EdgeColor','none');
    end
    text(ax, xoff(k)+wb/2, -1.0, lbl{k}, 'HorizontalAlignment','center', ...
         'FontSize',13, 'FontWeight','bold', 'Color',CD);
end

% U자관 (오른쪽 건물에만)
H.tubeOut = plot(ax, nan, nan, '-', 'Color',CD, 'LineWidth',2);
H.waterL  = patch(ax, nan, nan, CW, 'EdgeColor','none');
H.waterR  = patch(ax, nan, nan, CW, 'EdgeColor','none');
H.waterB  = patch(ax, nan, nan, CW, 'EdgeColor','none');
H.limL    = plot(ax, nan, nan, '--', 'Color',CR, 'LineWidth',1.2);
H.limR    = plot(ax, nan, nan, '--', 'Color',CR, 'LineWidth',1.2);
H.satTxt  = text(ax, xoff(2)+wb/2, 12.6, '', 'HorizontalAlignment','center', ...
                 'FontSize',14,'FontWeight','bold','Color',CR);

H.info = text(ax, -9.4, 12.9, '', 'FontSize',12, 'Color',CD, ...
              'VerticalAlignment','top','FontName','Arial');

title(ax, sprintf('%s형 지진파  PGA %.2fg   (변위 %d배 확대)', quake, pga, S), ...
      'FontSize',14, 'Color',CD);

%% ── U자관 확대 패널 ────────────────────────────────────
% 실제 비율(관 높이 0.5 m vs 건물 9 m)로는 물 움직임이 보이지 않으므로
% 별도 패널에 크게 그립니다. 좌표 단위는 물기둥 높이 hq 기준입니다.
ax3 = axes('Position',[0.70 0.38 0.28 0.55]);
hold(ax3,'on'); axis(ax3,'equal');
set(ax3,'XTick',[],'YTick',[],'Box','off','XColor','none','YColor','none');
UW = 2.6;  UT = 0.85;  UH = 3.0;          % 폭 / 관두께 / 수직부 높이 (hq 단위)
xlim(ax3, [-UW/2-UT, UW/2+UT]); ylim(ax3, [-0.9, UH+0.7]);
title(ax3, 'U자관 확대 (실제 비율 아님)', 'FontSize',12, 'Color',CD);

xL3 = -UW/2;  xR3 = UW/2;
% 관 외곽
plot(ax3, [xL3-UT/2 xL3-UT/2 xR3+UT/2 xR3+UT/2], [UH 0 0 UH], ...
     '-', 'Color',CD, 'LineWidth',3);
plot(ax3, [xL3+UT/2 xL3+UT/2 xR3-UT/2 xR3-UT/2], [UH UT UT UH], ...
     '-', 'Color',CD, 'LineWidth',3);
% 물 (좌 수직부 / 우 수직부 / 수평부)
H.zL = patch(ax3, nan, nan, CW, 'EdgeColor','none');
H.zR = patch(ax3, nan, nan, CW, 'EdgeColor','none');
patch(ax3, [xL3-UT/2 xR3+UT/2 xR3+UT/2 xL3-UT/2], [0 0 UT UT], CW, 'EdgeColor','none');
% 한계선 (물기둥이 여기 닿으면 포화)
plot(ax3, [xL3-UT/2-0.35 xL3+UT/2+0.35], [2 2], '--','Color',CR,'LineWidth',1.6);
plot(ax3, [xR3-UT/2-0.35 xR3+UT/2+0.35], [2 2], '--','Color',CR,'LineWidth',1.6);
text(ax3, 0, 2.35, '스트로크 한계', 'HorizontalAlignment','center', ...
     'FontSize',10,'Color',CR,'FontWeight','bold');
% 정지 수위선
plot(ax3, [xL3-UT/2-0.2 xL3+UT/2+0.2], [1 1], ':','Color',CG,'LineWidth',1.2);
plot(ax3, [xR3-UT/2-0.2 xR3+UT/2+0.2], [1 1], ':','Color',CG,'LineWidth',1.2);
H.zTxt = text(ax3, 0, -0.6, '', 'HorizontalAlignment','center', ...
              'FontSize',11, 'Color',CD, 'FontWeight','bold');
H.zArr = plot(ax3, nan, nan, '-', 'Color',CM, 'LineWidth',3);

%% ── 하단 시간이력 ──────────────────────────────────────
ax2 = axes('Position',[0.07 0.07 0.86 0.21]);
hold(ax2,'on'); grid(ax2,'on');
plot(ax2, t, o0.top*1000, '-', 'Color',CR, 'LineWidth',1.0);
plot(ax2, t, o1.top*1000, '-', 'Color',CM, 'LineWidth',1.0);
H.mark = plot(ax2, nan, nan, 'o', 'MarkerFaceColor',CD, 'MarkerEdgeColor','w', ...
              'MarkerSize',8);
H.vline = plot(ax2, [nan nan],[nan nan], '-', 'Color',[0 0 0 0.25], 'LineWidth',1);
xlabel(ax2,'시간 [s]'); ylabel(ax2,'최상층 변위 [mm]');
legend(ax2, {'무제어','TLCD'}, 'Location','northeast','Orientation','horizontal');
xlim(ax2,[0 p.T]);

%% ── 저장 준비 ──────────────────────────────────────────
if opt.save
    if ~exist('fig','dir'), mkdir fig; end
    vname = sprintf('fig/anim_%s_%s_%.2fg', preset, quake, pga);
    useVideo = true;
    try
        vw = VideoWriter([vname '.mp4'], 'MPEG-4');
    catch
        try
            vw = VideoWriter([vname '.avi'], 'Motion JPEG AVI');
        catch
            useVideo = false;
        end
    end
    if useVideo
        vw.FrameRate = opt.fps;
        open(vw);
    end
end

%% ── 애니메이션 루프 ────────────────────────────────────
for c = 1:numel(idx)
    i = idx(c);
    xg = ag(i)/9.81 * 0.6;                  % 지반 흔들림 (보기용)
    d0 = o0.x(:,i)*S;                       % 무제어 층변위
    d1 = o1.x(:,i)*S;                       % TLCD 층변위
    xf = o1.xf(i);                          % 물기둥 변위 (실제 스케일)

    for k = 1:2
        d = tern(k==1, d0, d1);
        x0 = xoff(k) + xg;
        set(H.gnd(k), 'XData', x0+[-4 10], 'YData',[0 0]);
        yv = (0:3)*hf;
        xL = x0 + [0; d(1); d(2); d(3)];
        xR = xL + wb;
        set(H.colL(k), 'XData', xL, 'YData', yv);
        set(H.colR(k), 'XData', xR, 'YData', yv);
        for f = 1:3
            xa = x0 + d(f);
            set(H.slab(k,f), 'XData', [xa xa+wb xa+wb xa], ...
                'YData', [yv(f+1)-0.18 yv(f+1)-0.18 yv(f+1)+0.18 yv(f+1)+0.18]);
        end
    end

    % ── U자관 (오른쪽 건물 옥상) ──
    xc = xoff(2) + xg + d1(3) + wb/2;       % 관 중심 (최상층 따라감)
    yb = 3*hf + 0.18;                       % 관 바닥
    xl = xc - Bq/2;  xr = xc + Bq/2;
    outline = [xl-tw/2, yb+tubeH; xl-tw/2, yb; xr+tw/2, yb; xr+tw/2, yb+tubeH];
    set(H.tubeOut, 'XData', outline(:,1), 'YData', outline(:,2));

    % 수위: 왼쪽은 -xf, 오른쪽은 +xf 만큼 변화
    wl = hq - xf;   wr = hq + xf;
    wl = max(0, min(tubeH, wl));  wr = max(0, min(tubeH, wr));
    set(H.waterL, 'XData', [xl-tw/2 xl+tw/2 xl+tw/2 xl-tw/2], ...
                  'YData', [yb yb yb+wl yb+wl]);
    set(H.waterR, 'XData', [xr-tw/2 xr+tw/2 xr+tw/2 xr-tw/2], ...
                  'YData', [yb yb yb+wr yb+wr]);
    set(H.waterB, 'XData', [xl-tw/2 xr+tw/2 xr+tw/2 xl-tw/2], ...
                  'YData', [yb yb yb+0.22 yb+0.22]);
    set(H.limL, 'XData', [xl-tw/2-0.2 xl+tw/2+0.2], 'YData', (yb+2*hq)*[1 1]);
    set(H.limR, 'XData', [xr-tw/2-0.2 xr+tw/2+0.2], 'YData', (yb+2*hq)*[1 1]);

    if abs(xf) >= o1.stroke_max*0.999
        set(H.satTxt, 'String', '⚠ 포화 — 감쇠기 기능 상실', ...
            'Position',[xoff(2)+wb/2+xg, 12.6]);
    else
        set(H.satTxt, 'String', '');
    end

    % ── U자관 확대 패널 갱신 ──
    u  = xf / hq;                       % 정지수위 대비 상대 변위 (한계 = ±1)
    uL = max(0, min(UH-0.05, 1 - u));   % 왼쪽 수위
    uR = max(0, min(UH-0.05, 1 + u));   % 오른쪽 수위
    set(H.zL, 'XData',[xL3-UT/2 xL3+UT/2 xL3+UT/2 xL3-UT/2], 'YData',[0 0 uL uL]);
    set(H.zR, 'XData',[xR3-UT/2 xR3+UT/2 xR3+UT/2 xR3-UT/2], 'YData',[0 0 uR uR]);
    if abs(u) >= 0.999
        set(H.zL,'FaceColor',CR); set(H.zR,'FaceColor',CR);
        set(H.zTxt,'String', sprintf('포화!  %.0f mm / 한계 %.0f mm', ...
            xf*1000, o1.stroke_max*1000), 'Color',CR);
    else
        set(H.zL,'FaceColor',CW); set(H.zR,'FaceColor',CW);
        set(H.zTxt,'String', sprintf('물기둥 %.0f mm  (한계 %.0f mm)', ...
            xf*1000, o1.stroke_max*1000), 'Color',CD);
    end
    % 건물 진행 방향 화살표 (위상차 확인용)
    vdir = sign(o1.v(3,i));
    set(H.zArr, 'XData', [0 vdir*0.9], 'YData', [UH+0.35 UH+0.35]);

    set(H.info, 'String', sprintf( ...
        't = %5.2f s\n지반가속도  %6.3f g\n무제어 변위 %6.1f mm\nTLCD  변위 %6.1f mm\n물기둥 변위 %6.1f mm  (한계 %.0f)', ...
        t(i), ag(i)/9.81, o0.top(i)*1000, o1.top(i)*1000, ...
        xf*1000, o1.stroke_max*1000));

    set(H.mark, 'XData', t(i), 'YData', o1.top(i)*1000);
    yl = ylim(ax2);
    set(H.vline, 'XData',[t(i) t(i)], 'YData', yl);

    drawnow limitrate;

    if opt.save && useVideo
        writeVideo(vw, getframe(fh));
    end

    % 특정 시각의 정지 이미지 저장 (opt.snapshot = 시간[s])
    if isfield(opt,'snapshot') && ~isempty(opt.snapshot)
        if any(abs(t(i) - opt.snapshot) < p.dt*step/2)
            sn = sprintf('fig/snap_%s_%s_t%.2f.png', preset, quake, t(i));
            exportgraphics(fh, sn, 'Resolution', 130);
            fprintf('정지 이미지 저장: %s\n', sn);
        end
    end
end

if opt.save
    if useVideo
        close(vw);
        fprintf('\n동영상 저장: %s\n', vw.Filename);
    end
    close(fh);
else
    fprintf('\n재생 완료. 창을 닫으려면 close all 입력.\n');
end
end

function y = tern(c,a,b)
if c, y = a; else, y = b; end
end
