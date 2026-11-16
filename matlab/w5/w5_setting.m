function s = w5_setting(t, tS, Tlead, s0, s1, rate)
%W5_SETTING  경보를 받은 뒤 액추에이터가 설정값을 옮겨 가는 궤적.
%
%   경보 시각 tA = tS − Tlead  (Tlead < 0 이면 흔들림보다 늦은 경보)
%   tA 부터 속도 rate [단위/s] 로 s0 → s1 이동 (Simulink 의 Rate Limiter 와 같음)
%   경보 전 구간에는 건물이 정지해 있으므로 해석을 tA 까지 늘릴 필요가 없음

tA = tS - Tlead;
d  = s1 - s0;
s  = s0 + sign(d) * min(abs(d), rate * max(0, t - tA));
end
