function R = main_stage1(preset, quake, pga)
%MAIN_STAGE1  1단계 — 무제어 / 고정 TLCD / 준능동 TLCD 3자 비교
%
%   R = main_stage1('3F', 'pohang', 0.2)
%
%   TLCD 형상을 먼저 출력하고, 세 경우의 응답을 비교한 뒤
%   시간이력 그래프를 fig/ 폴더에 저장합니다.

if nargin < 1, preset = '3F';       end
if nargin < 2, quake  = 'elcentro'; end
if nargin < 3, pga    = 0.2;        end

p  = params(preset);
b  = build_building(p);
tl = tlcd_design(p, b);

fprintf('\n========== 1단계 : 3자 비교 ==========\n');
fprintf('건물 preset : %s   층수 %d   층질량 %.0f ton   층강성 %.1f MN/m\n', ...
        preset, p.n, p.m/1e3, p.k/1e6);
fprintf('고유진동수  : 1차 %.3f Hz (주기 %.3f s)\n', b.f(1), 1/b.f(1));
fprintf('1차 모드질량: %.1f ton\n', b.M1/1e3);

fprintf('\n---------- TLCD 형상 (mu=%.2f, alpha=%.2f, gamma=%.2f) ----------\n', ...
        p.mu, p.alpha, p.gamma);
fprintf('  목표 진동수 wf    : %.3f rad/s  (%.3f Hz)\n', tl.wf, tl.f);
fprintf('  물기둥 전체길이 L : %.3f m\n', tl.L);
fprintf('  수평부 길이  B    : %.3f m\n', tl.B);
fprintf('  수직부 높이  h    : %.3f m   <-- 스트로크 한계\n', tl.h);
fprintf('  액체 질량   mf    : %.2f ton\n', tl.mf/1e3);
fprintf('  단면적      A     : %.4f m^2  (원형 환산 직경 %.2f m)\n', tl.A, tl.d);
if tl.h < 0.15
    fprintf('  [경고] 수직부 높이가 %.1f cm 로 지나치게 작습니다.\n', tl.h*100);
    fprintf('         단주기 구조물에서 TLCD 튜닝이 어렵다는 문헌 지적과 일치합니다.\n');
end

%% 시뮬레이션
t  = (0:p.dt:p.T)';
ag = gen_ground(quake, pga, p.dt, p.T);

o0 = simulate_tlcd(p, b, t, ag, 'none');
o1 = simulate_tlcd(p, b, t, ag, 'passive');
o2 = simulate_tlcd(p, b, t, ag, 'semiactive');

fprintf('\n---------- 응답 비교 (%s형, PGA %.2fg) ----------\n', quake, pga);
fprintf('%-14s %12s %12s %12s %10s\n', '', '최대변위[mm]', 'RMS변위[mm]', '최대가속[m/s2]', '물기둥사용률');
show('무제어',       o0, o0);
show('고정 TLCD',    o1, o0);
show('준능동 TLCD',  o2, o0);

%% 그래프
if ~exist('fig','dir'), mkdir fig; end
fh = figure('Visible','off','Position',[100 100 1100 800]);

subplot(3,1,1);
plot(t, ag/9.81, 'Color',[.4 .4 .4]); grid on;
ylabel('지반가속도 [g]'); title(sprintf('%s형 지진파 (PGA %.2fg)', quake, pga));

subplot(3,1,2);
plot(t, o0.top*1000, 'Color',[.75 .25 .15], 'LineWidth',1.0); hold on;
plot(t, o1.top*1000, 'Color',[0 .76 .69], 'LineWidth',1.0);
plot(t, o2.top*1000, 'Color',[.05 .20 .24], 'LineWidth',1.0);
grid on; ylabel('최상층 변위 [mm]');
legend('무제어','고정 TLCD','준능동 TLCD','Location','northeast');

subplot(3,1,3);
plot(t, o1.xf*1000, 'Color',[0 .76 .69], 'LineWidth',1.0); hold on;
plot(t, o2.xf*1000, 'Color',[.05 .20 .24], 'LineWidth',1.0);
yline( o1.stroke_max*1000, 'r--', 'LineWidth',1.2);
yline(-o1.stroke_max*1000, 'r--', 'LineWidth',1.2);
grid on; ylabel('물기둥 변위 [mm]'); xlabel('시간 [s]');
legend('고정','준능동','스트로크 한계','Location','northeast');

fn = sprintf('fig/stage1_%s_%s_%.2fg.png', preset, quake, pga);
exportgraphics(fh, fn, 'Resolution', 150);
close(fh);
fprintf('\n그래프 저장: %s\n', fn);

R = struct('p',p,'b',b,'tl',tl,'none',o0,'passive',o1,'semi',o2);
end

function show(name, o, ref)
red = @(a,r) (1 - a/r)*100;
if strcmp(name,'무제어')
    fprintf('%-14s %12.2f %12.2f %12.3f %10s\n', name, ...
        o.peak_disp*1000, o.rms_disp*1000, o.peak_acc, '-');
else
    fprintf('%-14s %12.2f %12.2f %12.3f %10.2f\n', name, ...
        o.peak_disp*1000, o.rms_disp*1000, o.peak_acc, o.stroke_use);
    fprintf('%-14s %11.1f%% %11.1f%% %11.1f%%\n', '  (저감률)', ...
        red(o.peak_disp,ref.peak_disp), red(o.rms_disp,ref.rms_disp), ...
        red(o.peak_acc,ref.peak_acc));
end
end
