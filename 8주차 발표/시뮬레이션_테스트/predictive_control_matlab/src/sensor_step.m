function [SS, obsv] = sensor_step(SS, S, Avec, ag_now, i, P)
% SENSOR_STEP  측정·잡음·센서 지연 (정수 스텝 대기열).
%  스텝 i에 측정한 값은 스텝 i + d_s에 도착한다. 출력은 이번 스텝에 도착한 관측 1개(없으면 valid=0).
%  obsv = [valid; stamp; m(9); u(92); v(92); a(92); Avec(9)]   (길이 296)
%   m     : plant_measure 순서. 제어기가 쓰는 센서값.
%   u,v,a : 이상적 상태정보 조건(초기 개발)에서만 StateEstimator가 쓰는 플랜트 내부 상태 사본.
%   Avec  : 스텝 i 시작 시점(스텝 i-1 갱신 후)의 장치 상태 (장치 상태 센서 가정)
%  SS가 비어 있으면 초기화한다: SS = sensor_step([], [], [], [], [], P)
if isempty(SS)
    SS = struct('d', P.rt.d_s, 'buf', zeros(296, P.rt.d_s + 1), 'filled', false(1, P.rt.d_s + 1), ...
                'noise_std', P.rt.noise_std, 'noise', P.rt.noise);
    obsv = zeros(296,1);
    return;
end
m = plant_measure(S, ag_now, P);
if SS.noise_std > 0
    m([1 2 6 7]) = m([1 2 6 7]) + SS.noise(:, i+1);
end
cur = [1; i; m; S.u; S.v; S.a; Avec(:)];
% 원형 대기열: 칸 k = mod(stamp, d+1)
k = mod(i, SS.d + 1) + 1;
kout = mod(i - SS.d, SS.d + 1) + 1;
if SS.d == 0
    obsv = cur;
else
    SS.buf(:, k) = cur; SS.filled(k) = true;
    if i - SS.d >= 0 && SS.filled(kout)
        obsv = SS.buf(:, kout);
    else
        obsv = zeros(296,1);
    end
end
end
