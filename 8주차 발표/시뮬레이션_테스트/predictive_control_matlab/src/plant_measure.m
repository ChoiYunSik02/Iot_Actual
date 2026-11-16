function m = plant_measure(S, ag_now, P)
% PLANT_MEASURE  스텝 i의 측정 벡터 (센서에 들어가는 값, 잡음 전).
%  m = [agx agy ux uy th accx_abs accy_abs vrel_x vrel_y]'
%   ux, uy, th : 최상층 변위·비틀림각
%   acc*_abs   : 최상층 절대가속도 (a + ag)
%   vrel_*     : 액주 상대속도 (v_d − v_top), 원문 밸브 법칙(식 12)의 입력
m = [ag_now(1); ag_now(2); S.u(P.tx); S.u(P.ty); S.u(P.tth); ...
     S.a(P.tx) + ag_now(1); S.a(P.ty) + ag_now(2); S.v(P.IDX) - S.v(P.tx); S.v(P.IDY) - S.v(P.ty)];
end
