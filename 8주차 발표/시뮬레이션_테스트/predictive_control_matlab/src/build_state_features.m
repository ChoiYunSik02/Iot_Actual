function X = build_state_features(CS, C, fcv, i, g, kind, kR, P)
% BUILD_STATE_FEATURES  공동 후보 점수망 입력 (계획 §5.3). 행 = 후보, 열 = 상태(86) + 후보(12) = 98.
%  도착한 관측(시각 s)·준비된 예측(fcv)·보낸 지령만 쓴다 (이상적 상태정보: 관측 시각의 플랜트 상태 사본).
%  상태 1-6   최상층 X·Y 변위, 비틀림, 각 속도
%       7-10  장치 일반좌표 IDX·IDY 변위·속도
%       11-19 장치 실제 f·θ·κ, 목표 f·θ·κ, 목표 − 실제
%       20-25 관측 나이, 예측 나이, 적용 격자까지 시간, 대기 지령 수, 펌프 램프 남은 시간, 회전 남은 시간
%       26-29 대기 지령(적용 전, 보낸 순서상 마지막 값) f·θ·κ (없으면 현재 목표), 가장 이른 대기 지령까지 남은 시간
%       30-37 실제 X·Y·비틀림 최대, 제곱합 (관측 s까지), 그림자 R 비틀림 제곱합·최대 (같은 관측 시각)
%       38-85 예측 요약: 0.5 s 8구간 × (X 평균·RMS·최대|·|, Y 평균·RMS·최대|·|)  (zero·persistence도 같은 변환)
%       86    예측 유효
%  후보 87-98 f θ κ, 각 − 현재 목표, 마스크 f·θ·κ(숫자), isR, isHold, 빠른 결정
%  단위: m, m/s, rad, rad/s, Hz, s. 표준화는 점수망(학습 train 통계)이 한다.
%  κ 법칙(R 후보) 값은 현재 관측의 법칙 값 kR로 둔다.
s = CS.s; xs = CS.xs; A = CS.As; dt = P.dt;
st = zeros(1, 86);
st(1:6) = [xs.u(P.tx), xs.u(P.ty), xs.u(P.tth), xs.v(P.tx), xs.v(P.ty), xs.v(P.tth)];
st(7:10) = [xs.u(P.IDX), xs.u(P.IDY), xs.v(P.IDX), xs.v(P.IDY)];
st(11:19) = [A.f, A.theta, A.kappa, A.f_tgt, A.th_tgt, CS.k_last, A.f_tgt - A.f, A.th_tgt - A.theta, CS.k_last - A.kappa];
rr = 0; if A.ramp_on, rr = max(0, P.DT_F - (s - A.ramp_t0)*dt); end
Q = CS.issued(CS.issued(:,1) >= i, :); np = size(Q, 1);
st(20:25) = [(i - s)*dt, 0, (g - i)*dt, np, rr, abs(A.th_tgt - A.theta)/P.ROT];
pq = [CS.f_last, CS.th_last, CS.k_last]; tq = 0;     % CS.*_last = 보낸 마지막 지령 (대기 중이면 그 값)
if np > 0, tq = (min(Q(:,1)) - i)*dt; end
st(26:29) = [pq, tq];
sQ = 0; sM = 0; if ~isempty(CS.shadow), sQ = CS.shadow.Q; sM = CS.shadow.M; end
st(30:37) = [CS.Mx, CS.My, CS.Ma, CS.Qx, CS.Qy, CS.Qa, sQ, sM];
if fcv(1) > 0.5
    st(21) = (i - fcv(2))*dt;
    Hn = P.rt.Hn; Yx = fcv(4:3+Hn); Yy = fcv(4+Hn:3+2*Hn); m = Hn/8; q = 37;
    for k = 1:8
        w = (k-1)*m + (1:m);
        st(q+(1:6)) = [mean(Yx(w)), sqrt(mean(Yx(w).^2)), max(abs(Yx(w))), mean(Yy(w)), sqrt(mean(Yy(w).^2)), max(abs(Yy(w)))];
        q = q + 6;
    end
    st(86) = 1;
end
n = numel(C); X = zeros(n, 98);
for a = 1:n
    c = C(a);
    mf = ~isnan(c.f); mt = ~isnan(c.th); mkn = isnumeric(c.k_mode);
    fv = CS.f_last; if mf, fv = c.f; end
    tv = CS.th_last; if mt, tv = c.th; end
    if mkn, kv = c.k_mode; else, kv = kR; end
    X(a, :) = [st, fv, tv, kv, fv - CS.f_last, tv - CS.th_last, kv - CS.k_last, mf, mt, mkn, c.isR, c.isHold, kind == 2];
end
end
