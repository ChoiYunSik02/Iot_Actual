function c = joint_timeline(c, budget)
% JOINT_TIMELINE  J 비교의 공통 고정 시간축 (계획 §8: 이상화 알고리즘 비교, 실행 가능성은 실측 지연으로 따로).
%  센서·통신·추가 지연 0, 예측 준비 1스텝, R 1스텝, 느린 결정 budget(1) s, 빠른 결정 budget(2) s — 모든 J 방식 공통.
c.latency.timing_mode = 'nominal';
c.latency.sensor_s = 0; c.latency.comm_s = 0; c.latency.extra_info_s = 0;
c.latency.inject_select_s = 0; c.latency.inject_forecast_s = 0;
cs = c.latency.compute_s; cs.R = 0.01; cs.select_J = budget(1); cs.select_JV = budget(2);
for f = {'forecast_zero', 'forecast_persistence', 'forecast_preview', 'forecast_lstmnat'}, cs.(f{1}) = 0.01; end
c.latency.compute_s = cs;
end
