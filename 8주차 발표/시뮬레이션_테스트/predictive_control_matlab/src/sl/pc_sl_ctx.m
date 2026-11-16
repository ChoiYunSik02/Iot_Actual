function ctx = pc_sl_ctx(name)
% PC_SL_CTX  Simulink 블록(System object)이 setupImpl에서 읽는 실행 맥락 (base 작업공간 변수).
%  ctx = struct(cfg, M, P(rt 포함), model, preview, nt) — scripts/run_simulink_case.m이 만든다.
if nargin < 1 || isempty(name), name = 'pc_ctx'; end
ctx = evalin('base', name);
end
