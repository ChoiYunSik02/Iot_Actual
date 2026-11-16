function [p, b] = build_sdof(f1, zeta, Mmod, mu, alpha, xi)
%BUILD_SDOF  논문 제원(진동수·감쇠비·모드질량)으로 등가 1자유도 모델을 만듭니다.
%
%   [p, b] = build_sdof(f1, zeta, Mmod, mu, alpha, xi)
%
%   simulate_tlcd 이 요구하는 p(파라미터)·b(구조행렬) 구조체를 그대로 반환하므로
%   기존 시뮬레이터를 고치지 않고 논문 모델을 돌릴 수 있습니다.

w1 = 2*pi*f1;

p = params('3F');          % 기본값을 가져온 뒤 필요한 항목만 덮어씁니다
p.n     = 1;
p.m     = Mmod;
p.k     = Mmod * w1^2;
p.zeta  = zeta;
p.mu    = mu;
p.alpha = alpha;
p.gamma = 0.98;            % 튜닝비 — 논문 대부분 최적 튜닝 사용
p.xi    = xi;

b.M = Mmod;
b.K = Mmod * w1^2;
b.C = 2 * zeta * w1 * Mmod;      % 1자유도는 Rayleigh 대신 직접 계산
b.w = w1;
b.f = f1;
b.Phi = 1 / sqrt(Mmod);
b.phi1 = 1;
b.M1 = Mmod;                      % 모드질량 = 입력값
b.r = 1;
b.e = 1;
b.rayleigh = [2*zeta*w1, 0];
end
