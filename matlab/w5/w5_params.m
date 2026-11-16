function [p, b, tl] = w5_params(naxes)
%W5_PARAMS  5주차 예측 선제 제어 실험용 6층 건물 + 밀폐형 TLCD(한 축) 파라미터.
%
%   4주차 보고서에 기록된 값으로 새로 구성한 모델입니다.
%     건물   6층 균등 전단건물, 1차 0.872 Hz, 1차 모드질량 1,382.1 t, 감쇠 2%
%     TLCD   밀폐형, 한 축 질량비 0.5% (6.91 t), B = 2.4 m, L = 4.0 m,
%            수직부 0.8 m (= 스트로크 한계), 공기실 공기스프링으로 진동수 맞춤
%
%   튜닝비 gamma 와 손실계수 xi 는 실험 중에 바뀌는 "설정값"이라 여기서는
%   기본값만 둡니다.

%% 건물 — 1차 진동수와 모드질량을 맞추도록 m, k 역산
if nargin < 1, naxes = 1; end
p.axes = naxes;                    % 1 = 한 축, 2 = X·Y 직교배치 (축마다 같은 TLCD)
if naxes == 2, p.tag = '_2axis'; p.figsub = '2축'; else, p.tag = ''; p.figsub = ''; end
p.n    = 6;
p.zeta = 0.02;
p.f1_target = 0.872;           % [Hz]
p.M1_target = 1382.1e3;        % [kg]

p.m = 1;  p.k = 1;
b0 = build_building(p);
p.m = p.M1_target / b0.M1;                         % M1 은 m 에 비례
p.k = p.m * (2*pi*p.f1_target / b0.w(1))^2;        % w1 은 sqrt(k/m) 에 비례
b  = build_building(p);
p.w1d = b.w(1);                    % TLCD 튜닝 기준 (설계 시점 건물 1차 각진동수)

%% 시나리오 B — 강진 시 강성 저하 (가정)
%   PGA 가 클수록 층강성이 줄어 주기가 길어진다고 가정합니다.
%   0.2g → 3%, 0.4g → 9%, 0.6g → 15% 강성 저하 (진동수 약 1.5 / 4.6 / 7.8% 저하)
%   ※ 비율은 가정값이며 문헌 근거 확인 필요. 4주차 재튜닝 시험의 "8% 저하"와 같은 규모.
p.soft = @(pga) min(0.15, 0.3*max(0, pga - 0.1));

%% 밀폐형 TLCD (한 축)
p.rho   = 1000;
p.g     = 9.81;
tl.mu   = 0.005;
tl.mf   = tl.mu * b.M1;            % 약 6.91 t
tl.L    = 4.0;
tl.B    = 2.4;
tl.alpha= tl.B / tl.L;             % 0.6
tl.h    = (tl.L - tl.B)/2;         % 0.8 m
tl.A    = tl.mf / (p.rho * tl.L);
tl.k_grav = 2 * p.rho * tl.A * p.g;   % 중력 복원강성 (개방형이면 이것만)
tl.stroke = tl.h;                  % 물기둥 변위 한계 [m]
tl.k_stop = 100;                   % 한계 초과 시 페널티 강성 배율

%% 기본 설정값 (예측 없이 운용할 때)
p.gamma0 = 0.98;
p.xi0    = NaN;                    % 설계표(w5_lookup)의 0.2g 최적값으로 채움

%% 액추에이터 속도 — 설정 범위 전체를 움직이는 데 걸리는 시간 [s]
p.gamma_range = [0.86 1.04];
p.T_valve = 0.05;                  % 밸브 (ms 단위)
p.T_air   = 3;                     % 공기실 압력 (수 초) — 가정
p.T_pump  = 30;                    % 펌프 수위 (수십 초) — 가정

%% 해석
p.dt = 0.005;
p.T  = 60;                         % 실측 기록 (진원시부터 60 s)

end
