function v = act_pack(A)
% ACT_PACK  장치 상태 struct → 9x1 벡터 (Simulink 신호용). act_unpack의 역.
%  [f theta th_tgt kappa f_tgt ramp_on ramp_t0 ramp_f0 ramp_f1]
v = [A.f; A.theta; A.th_tgt; A.kappa; A.f_tgt; double(A.ramp_on); A.ramp_t0; A.ramp_f0; A.ramp_f1];
end
