function t = tlcd_design(p, b)
%TLCD_DESIGN  튜닝비로부터 TLCD 형상을 역산합니다.
%
%   고유진동수    wf = sqrt(2g / L)
%   목표          wf = gamma * w1
%   따라서        L  = 2g / wf^2
%                 B  = alpha * L
%                 h  = (L - B) / 2          한쪽 수직부 물기둥 높이
%                 mf = mu * M1              액체 총질량
%                 A  = mf / (rho * L)       단면적
%
%   t.stroke_max 는 물리적으로 가능한 최대 물기둥 변위(= h)입니다.
%   이 값을 넘으면 한쪽 수직부가 비고 반대쪽이 넘칩니다.

t.wf = p.gamma * b.w(1);
t.L  = 2*p.g / t.wf^2;
t.B  = p.alpha * t.L;
t.h  = (t.L - t.B) / 2;

t.mf = p.mu * b.M1;
t.A  = t.mf / (p.rho * t.L);
t.d  = 2*sqrt(t.A/pi);        % 원형 단면 가정 시 관 직경 [m]

t.kf = 2 * p.rho * t.A * p.g; % 복원강성
t.cf_coef = 0.5 * p.rho * t.A; % 감쇠항 계수 (× xi × |vf|)

t.stroke_max = t.h;           % 기하학적 한계
t.f = t.wf / (2*pi);

end
