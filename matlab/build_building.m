function b = build_building(p)
%BUILD_BUILDING  전단건물의 질량·강성·감쇠 행렬과 모드 특성을 구성합니다.
%
%   b.M, b.K, b.C   n×n 행렬
%   b.w   [rad/s]   고유각진동수 (오름차순)
%   b.f   [Hz]      고유진동수
%   b.Phi           질량정규화 모드형상
%   b.M1  [kg]      1차 모드질량 (최상층 기준 정규화)

n = p.n;

% 질량행렬
b.M = p.m * eye(n);

% 전단건물 강성행렬 (삼중대각)
b.K = zeros(n);
for i = 1:n
    b.K(i,i) = b.K(i,i) + p.k;
    if i < n
        b.K(i,i)     = b.K(i,i) + p.k;
        b.K(i,i+1)   = -p.k;
        b.K(i+1,i)   = -p.k;
    end
end

% 고유치 해석
[V, D] = eig(b.K, b.M);
[w2, idx] = sort(diag(D));
V = V(:, idx);
b.w = sqrt(w2);
b.f = b.w / (2*pi);

% 질량정규화
for j = 1:n
    V(:,j) = V(:,j) / sqrt(V(:,j)' * b.M * V(:,j));
end
b.Phi = V;

% Rayleigh 감쇠: 1·2차 모드에 zeta 부여
w1 = b.w(1);  w2m = b.w(min(2,n));
A  = [1/(2*w1), w1/2; 1/(2*w2m), w2m/2];
ab = A \ [p.zeta; p.zeta];
b.C = ab(1)*b.M + ab(2)*b.K;
b.rayleigh = ab;

% 1차 모드질량 (최상층 성분을 1로 정규화한 기준)
phi1 = b.Phi(:,1) / b.Phi(end,1);
b.phi1 = phi1;
b.M1   = phi1' * b.M * phi1;

b.r = ones(n,1);          % 지반가속도 영향벡터
b.e = [zeros(n-1,1); 1];  % TLCD 설치 위치 (최상층)

end
