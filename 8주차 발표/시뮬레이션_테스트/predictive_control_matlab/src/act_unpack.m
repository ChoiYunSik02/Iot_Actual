function A = act_unpack(v)
% ACT_UNPACK  9x1 벡터 → 장치 상태 struct. act_pack의 역.
A = struct('f', v(1), 'theta', v(2), 'th_tgt', v(3), 'kappa', v(4), 'f_tgt', v(5), ...
           'ramp_on', v(6) > 0.5, 'ramp_t0', v(7), 'ramp_f0', v(8), 'ramp_f1', v(9));
end
