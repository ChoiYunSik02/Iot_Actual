function S = plant_step(S, ag_next, dev, P, has_device)
% PLANT_STEP  Newmark 평균가속도법 한 스텝 (스텝 i → i+1). rstlcd_sim.m과 같은 식.
%  ag_next   : [agx; agy] (스텝 i+1 지반가속도, m/s²). Newmark 끝점 하중이라 플랜트 물리에만 쓴다.
%  dev       : [f; theta; kappa] 스텝 i의 실제 장치 상태 (actuator_step 출력)
%  has_device: false면 무제어 U (장치 질량 대신 단위 질량·강성 자리표시, rstlcd_sim.m과 같음)
%  계산량을 줄이려고 장치와 무관한 부분(P.Ab, P.Kb)을 미리 만들어 두고, 장치 2x2 블록만 더한다.
if nargin < 5, has_device = true; end
dt = P.dt;
u = S.u; v = S.v; a = S.a;
w1 = v + 0.5*dt*a; w2 = u + dt*v + 0.25*dt^2*a;
Mv = P.Mb;
A = P.Ab;
rhs = -P.C0*w1 - P.Kb*w2;
if has_device
    f = dev(1); theta = dev(2); kap = dev(3);
    c_ = abs(cos(theta)); s_ = abs(sin(theta));
    mx = P.M_RS*max(c_,1e-6); my = P.M_RS*max(s_,1e-6); w2d = (2*pi*f)^2;
    kx = mx*w2d*c_; ky = my*w2d*s_;
    cc = P.c_scale*0.5*P.RHO*P.Av^2/P.Ah*tlcd_delta(P, kap);
    I = [P.tx P.IDX]; Kd = [kx, -kx; -kx, kx-1]; cd = cc*abs(v(P.IDX)-v(P.tx)); Cd = [cd, -cd; -cd, cd];
    A(I,I) = A(I,I) + diag([0, mx-1]) + 0.5*dt*Cd + 0.25*dt^2*Kd;
    rhs(I) = rhs(I) - Cd*w1(I) - Kd*w2(I); Mv(P.IDX) = mx;
    I = [P.ty P.IDY]; Kd = [ky, -ky; -ky, ky-1]; cd = cc*abs(v(P.IDY)-v(P.ty)); Cd = [cd, -cd; -cd, cd];
    A(I,I) = A(I,I) + diag([0, my-1]) + 0.5*dt*Cd + 0.25*dt^2*Kd;
    rhs(I) = rhs(I) - Cd*w1(I) - Kd*w2(I); Mv(P.IDY) = my;
end
rhs = rhs - Mv .* (P.E*ag_next(:));
a1 = A \ rhs;
S.u = u + dt*v + 0.25*dt^2*(a + a1); S.v = v + 0.5*dt*(a + a1); S.a = a1;
S.i = S.i + 1;
end
