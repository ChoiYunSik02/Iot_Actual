function [wx, wy, mk] = make_window(gx, gy, qn, trig_stamp, r, Wn)
% MAKE_WINDOW  100 Hz 관측 열에서 끝이 qn(100 Hz 샘플 번호, 0부터)인 Wn 창을 만든다.
%  온라인(obsbuffer_step)과 학습 자료(build_forecast_dataset)가 같은 함수를 쓴다.
%  gx, gy     : 100 Hz 관측 (gx(q+1) = 샘플 q). qn보다 뒤 샘플은 읽지 않는다.
%  trig_stamp : 트리거 측정 시각(플랜트 스텝), 없으면 음수. r = 플랜트 스텝 / AI 샘플
%  mask = 1 : 샘플 시각 ≥ 트리거 시각이고 기록 시작 이후. 나머지는 값 0, mask 0.
qs = (qn - Wn + 1:qn)';
ok = qs >= 0;
if trig_stamp >= 0, ok = ok & (qs*r >= trig_stamp); else, ok(:) = false; end
wx = zeros(Wn,1); wy = zeros(Wn,1); mk = double(ok);
idx = qs(ok) + 1;
wx(ok) = gx(idx); wy(ok) = gy(idx);
end
