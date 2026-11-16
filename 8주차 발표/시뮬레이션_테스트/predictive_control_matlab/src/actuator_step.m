function [A, dev] = actuator_step(A, rel, i, P)
% ACTUATOR_STEP  펌프 램프·회전판 속도 제한·밸브 개도 (스텝 i).
%  rel : command_queue_step이 스텝 i에 내보낸 지령 [has_f f has_th th has_k kappa]
%  dev : [f; theta; kappa] — 이 스텝 플랜트에 쓰이는 실제 장치 상태
%  순서는 rstlcd_sim.m과 같다: 목표 반영 → 램프 진행 → 회전.
%  A가 비어 있으면 초기 상태(f0, 0°, kappa0)를 만든다.
if isempty(A)
    A = struct('f', P.F0, 'theta', 0, 'th_tgt', 0, 'kappa', P.KAPPA0, 'f_tgt', P.F0, ...
               'ramp_on', false, 'ramp_t0', 0, 'ramp_f0', P.F0, 'ramp_f1', P.F0);
    dev = [A.f; A.theta; A.kappa];
    if nargin < 2 || isempty(rel), return; end
end
dt = P.dt; t = i*dt;
if rel(1)
    A.f_tgt = min(max(rel(2), P.FR(1)), P.FR(2));
    A.ramp_on = true; A.ramp_t0 = t; A.ramp_f0 = A.f; A.ramp_f1 = A.f_tgt;
end
if rel(3), A.th_tgt = min(max(rel(4), P.TH_RANGE(1)), P.TH_RANGE(2)); end
if rel(5), A.kappa = rel(6); end
if A.ramp_on
    r = min(1.0, (t - A.ramp_t0)/P.DT_F); A.f = A.ramp_f0 + (A.ramp_f1 - A.ramp_f0)*r;
    if r >= 1.0, A.ramp_on = false; end
end
dth = min(max(A.th_tgt - A.theta, -P.ROT*dt), P.ROT*dt); A.theta = A.theta + dth;
dev = [A.f; A.theta; A.kappa];
end
