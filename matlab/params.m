function p = params(preset)
%PARAMS  건물 · TLCD · 해석 파라미터를 한곳에서 정의합니다.
%
%   p = params()            기본값 (3층 전단건물)
%   p = params('3F')        3층  — 목표 1차 진동수 약 1.2 Hz
%   p = params('10F')       10층 상당 — 목표 약 0.5 Hz (비교군)
%
%   설계 파라미터 mu/alpha/gamma의 초기값은 아래 문헌의 검증값입니다.
%     Shah & Usman (2022), PLOS ONE, DOI 10.1371/journal.pone.0269910
%     (4층 강프레임 진동대 실험: 질량비 5%, 튜닝비 0.98, 길이비 0.8)

if nargin < 1, preset = '3F'; end

%% ── 건물 ────────────────────────────────────────────────
p.preset = preset;
switch upper(preset)
    case '3F'
        p.n      = 3;            % 층수
        p.m      = 100e3;        % 층당 질량 [kg]  (100 ton)
        p.k      = 28.7e6;       % 층간 강성 [N/m] → 1차 약 1.2 Hz
    case '10F'
        p.n      = 3;            % 3자유도로 축약하되 강성을 낮춰 장주기화
        p.m      = 100e3;
        p.k      = 5.0e6;        % → 1차 약 0.5 Hz
    otherwise
        error('params:preset', '알 수 없는 preset: %s', preset);
end
p.zeta = 0.02;                   % 1·2차 모드 감쇠비 (Rayleigh)

%% ── TLCD 설계 파라미터 ──────────────────────────────────
p.mu    = 0.05;                  % 질량비  (1차 모드질량 대비)
p.alpha = 0.80;                  % 길이비  B/L
p.gamma = 0.98;                  % 튜닝비  wf/w1
p.xi    = 4.0;                   % 손실계수 (고정 오리피스 기준값)
p.rho   = 1000;                  % 물 밀도 [kg/m^3]

% 준능동 밸브가 오갈 손실계수 범위
p.xi_lo = 1.0;                   % 밸브 열림 (감쇠 작음)
p.xi_hi = 20.0;                  % 밸브 닫힘 (감쇠 큼)

%% ── 해석 ────────────────────────────────────────────────
p.dt  = 1e-3;                    % 적분 시간간격 [s]
p.T   = 30;                      % 해석 시간 [s]
p.g   = 9.81;

%% ── 포화 · 지연 ─────────────────────────────────────────
p.stroke_limit = Inf;            % 물기둥 변위 한계 [m] (Inf = 한계 없음)
p.k_stop       = 100;            % 하드스톱 페널티 강성 배율 (× k_f)
p.delay        = 0;              % 제어 지연 [s]

end
