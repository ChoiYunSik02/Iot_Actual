function M = paper_models()
%PAPER_MODELS  논문별 건물·TLCD 제원 (논문 본문에서 직접 추출한 값)
%
%   M = paper_models();   구조체 배열 반환
%
%   각 항목
%     name   표시 이름
%     f1     1차 고유진동수 [Hz]
%     zeta   구조 감쇠비 [-]
%     Mmod   1차 모드질량 [kg]
%     mu     질량비 (액체질량 / 모드질량)
%     alpha  길이비 B/L
%     xi     손실계수 (미보고 시 기본 4.0)
%     scale  'lab' 축소모형 / 'full' 실물
%     src    출처
%
%   ※ 출처 표기 규칙(학교 접근 경로)
%      PLOS ONE  : 오픈액세스
%      JIPR 2026 : 오픈액세스(SpringerOpen)
%      JOBE 2025 : ScienceDirect (학교 구독)

k = 0;

k = k + 1;
M(k).name  = 'PLOS ONE 2022 (4층 축소모형)';
M(k).short = sprintf('PLOS ONE 2022\n축소모형');
M(k).f1    = 1.30;        % 본문: 공진 1.30 Hz = 1차 고유진동수
M(k).zeta  = 0.02;        % 미보고 → 통상값 가정
M(k).Mmod  = 13.9;        % 층질량 4.825 kg × 4층의 1차 모드질량(최상층 정규화)
M(k).mu    = 0.05;        % 본문: 5% mass ratio
M(k).alpha = 0.80;        % 본문: length ratio 0.8
M(k).xi    = 4.0;         % orifice blocking ratio 0.5 → 대략값
M(k).scale = 'lab';
M(k).src   = 'PLOS ONE, 2022 · 오픈액세스';

k = k + 1;
M(k).name  = 'JIPR 2026 (6층 RC 실물)';
M(k).short = sprintf('JIPR 2026\n6층 실물');
M(k).f1    = 0.872;       % 본문: SDOF 고유진동수 0.872 Hz
M(k).zeta  = 0.01;        % 본문: damping ratio 1%
M(k).Mmod  = 1382.1e3;    % 본문: 1382.1 tons
M(k).mu    = 0.01;        % 본문: mass ratio 1%
M(k).alpha = 0.60;        % 본문: length ratio 0.6
M(k).xi    = 4.0;
M(k).scale = 'full';
M(k).src   = 'J. Infrastruct. Preserv. Resil., 2026 · 오픈액세스';

k = k + 1;
M(k).name  = 'JOBE 2025 (편심 프레임 실물)';
M(k).short = sprintf('JOBE 2025\n편심 실물');
M(k).f1    = 0.3373;      % 본문: 0.3373 Hz
M(k).zeta  = 0.02;        % 본문: modal damping 2%
M(k).Mmod  = 463178/0.02; % 본문: 액체질량 463,178 kg = 모드질량의 2%
M(k).mu    = 0.02;        % 본문: 2% of first modal mass
M(k).alpha = 0.80;        % 미보고 → 통상값 가정
M(k).xi    = 4.0;
M(k).scale = 'full';
M(k).src   = 'J. Building Engineering, 2025 · ScienceDirect';

k = k + 1;
M(k).name  = '본 연구 3층 (1.20 Hz)';
M(k).short = sprintf('본 연구 3층');
M(k).f1    = 1.200;
M(k).zeta  = 0.02;
M(k).Mmod  = 184.1e3;     % build_building 결과
M(k).mu    = 0.05;
M(k).alpha = 0.80;
M(k).xi    = 4.0;
M(k).scale = 'full';
M(k).src   = '본 연구 (3주차 모델)';

k = k + 1;
M(k).name  = '본 연구 장주기 (0.50 Hz)';
M(k).short = sprintf('본 연구 장주기');
M(k).f1    = 0.501;
M(k).zeta  = 0.02;
M(k).Mmod  = 184.1e3;
M(k).mu    = 0.05;
M(k).alpha = 0.80;
M(k).xi    = 4.0;
M(k).scale = 'full';
M(k).src   = '본 연구 (비교 모델)';

%% 형상 역산 — 각 모델의 TLCD 치수
g = 9.81; rho = 1000;
for i = 1:numel(M)
    w  = 2*pi*M(i).f1;
    M(i).L = 2*g / w^2;                    % 물기둥 전체 길이
    M(i).B = M(i).alpha * M(i).L;          % 수평부 길이
    M(i).h = (M(i).L - M(i).B) / 2;        % 수직부 물기둥 높이 = 스트로크 한계
    M(i).mf = M(i).mu * M(i).Mmod;         % 액체 질량
    M(i).A  = M(i).mf / (rho * M(i).L);    % 단면적
    M(i).D  = 2*sqrt(M(i).A/pi);           % 원형 환산 직경
    M(i).hD = M(i).h / M(i).D;             % 종횡비 (클수록 관다운 형상)
end
end
