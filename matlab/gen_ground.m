function [ag, t] = gen_ground(kind, pga, dt, T, seed)
%GEN_GROUND  Kanai-Tajimi 필터 기반 합성 지진파를 생성합니다.
%
%   [ag, t] = gen_ground(kind, pga, dt, T, seed)
%
%   kind : 'gyeongju' | 'pohang' | 'elcentro'
%   pga  : 목표 최대지반가속도 [g]
%
%   ── 중요 ─────────────────────────────────────────────────
%   실측 기록을 아직 확보하지 못했으므로, 각 지진의 보고된 지배 주기와
%   지속시간을 재현한 *합성 대체파*입니다. 논문·최종보고서에는 반드시
%   실측 기록(기상청 / PEER NGA-West2)으로 교체해야 합니다.
%
%   지배 주기 근거
%     경주 2016  ML5.8  약 0.1초 (3Hz 이상), 지속시간 짧음
%     포항 2017  ML5.4  0.5~0.6초 (약 2Hz), 진원 9km로 얕음
%     El Centro 1940    장주기 성분 포함, 지속시간 김
%   ─────────────────────────────────────────────────────────

if nargin < 5, seed = 42; end
rng(seed);

t = (0:dt:T)';
N = numel(t);

switch lower(kind)
    case 'gyeongju'                     % 고주파 · 단지속
        wg = 2*pi*5.0;  zg = 0.60;  t_rise = 1.0;  t_dur = 4.0;  decay = 1.2;
    case 'pohang'                       % 중간주파 · 단지속 · 얕은 진원
        wg = 2*pi*2.0;  zg = 0.50;  t_rise = 1.5;  t_dur = 6.0;  decay = 0.8;
    case 'elcentro'                     % 장주기 성분 · 장지속
        wg = 2*pi*1.5;  zg = 0.40;  t_rise = 2.0;  t_dur = 18.0; decay = 0.25;
    otherwise
        error('gen_ground:kind', '알 수 없는 지진파 종류: %s', kind);
end

% 백색잡음을 Kanai-Tajimi 2차 필터에 통과
%   xf'' + 2*zg*wg*xf' + wg^2*xf = -w(t)
%   출력  y = 2*zg*wg*xf' + wg^2*xf
% Control System Toolbox(tf/lsim)를 쓰지 않고 직접 적분합니다.
% 이 PC에는 MATLAB과 Simulink 본체만 설치되어 있어 툴박스 함수를 쓸 수 없습니다.
wn = randn(N,1);
y  = zeros(N,1);
xf = 0;  vf = 0;
for i = 1:N
    af = -2*zg*wg*vf - wg^2*xf - wn(i);
    vf = vf + af*dt;
    xf = xf + vf*dt;
    y(i) = 2*zg*wg*vf + wg^2*xf;
end

% Jennings 형 포락함수 (상승 - 정상 - 지수감쇠)
env = ones(N,1);
i1 = t < t_rise;
i3 = t > (t_rise + t_dur);
env(i1) = (t(i1)/t_rise).^2;
env(i3) = exp(-decay * (t(i3) - (t_rise + t_dur)));

ag = y .* env;

% 기저선 보정 후 목표 PGA로 스케일링
ag = ag - mean(ag);
ag = ag / max(abs(ag)) * pga * 9.81;   % [m/s^2]

end
