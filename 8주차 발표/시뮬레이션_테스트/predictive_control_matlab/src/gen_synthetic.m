function [x, y, meta] = gen_synthetic(seed, dt)
% GEN_SYNTHETIC  합성 지진 X·Y 한 쌍 (생성 시드 하나 = 원본 하나).
%  분포는 페이퍼/논문_및_AI결과_모음_20261022/5_실험코드/gen_labels_v2.py synthetic()과 같다:
%   백색잡음 → Kanai-Tajimi(fg, zg) × Clough-Penzien 고역 통과, Jennings 포락선, X-Y 상관 rho, 세기비, 성분 교환.
%  난수 생성기가 numpy와 달라 같은 시드라도 개별 파형은 Python 판과 다르다.
%  정규화는 여기서 하지 않는다(build_forecast_dataset이 트랙별로 처리).
if nargin < 2, dt = 0.01; end
rng(seed, 'twister');
U = @(a, b) a + (b - a)*rand();
dur = U(15, 40); n = floor(dur/dt); t = (0:n-1)'*dt;
t1 = U(1, 4); t2 = dur*U(0.3, 0.6); dec = U(0.15, 0.5);
env = (t < t1).*(t/t1).^2 + (t >= t1 & t < t2) + (t >= t2).*exp(-dec*(t - t2));
fg = exp(U(log(0.5), log(8.0))); zg = U(0.2, 0.6);
a = kt_filter(n, fg, zg, dt);
b = kt_filter(n, fg*U(0.8, 1.25), zg, dt);
rho = U(0, 0.6);
x = a; y = rho*a + sqrt(1 - rho^2)*b;
y = y*U(0.5, 1.0);
swap = rand() < 0.5;
if swap, tmp = x; x = y; y = tmp; end
x = x.*env; y = y.*env;
meta = struct('kind', 'synthetic', 'seed', seed, 'fg', fg, 'zg', zg, 'dur', dur, 'rho', rho, 'swap', swap);
end

function z = kt_filter(n, fg, zg, dt)
nf = floor(n/2) + 1;
w = 2*pi*(0:nf-1)'/(n*dt);
wg = 2*pi*fg; wf = 2*pi*fg/10;
kt = (wg^4 + 4*zg^2*wg^2*w.^2)./((wg^2 - w.^2).^2 + 4*zg^2*wg^2*w.^2);
cp = w.^4./((wf^2 - w.^2).^2 + 4*0.6^2*wf^2*w.^2);
Z = fft(randn(n, 1));
H = sqrt(kt.*cp);
Hf = [H; flipud(H(2:end - (mod(n,2) == 0)))];     % 실수 신호용 대칭 (rfft/irfft와 같은 결과)
z = real(ifft(Z.*Hf));
end
