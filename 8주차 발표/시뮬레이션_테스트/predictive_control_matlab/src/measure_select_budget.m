function [c, b] = measure_select_budget(c)
% MEASURE_SELECT_BUDGET  설정 c(후보 집합·지평)에서 C1 선택 계산시간 p95를 El Centro 지연 0 실행으로 재서 예산으로 넣는다.
%  measure_runtime과 같은 규칙(첫 결정 제외 후 95번째 백분위). 후보 수나 지평이 바뀌면 계산시간이 달라지므로 변형마다 다시 잰다.
cm = c; cm.latency.timing_mode = 'nominal';
[ax, ay] = load_record(cm, 'ElCentro_1940', cm.plant.dt);
z = struct('sensor_s', 0, 'comm_s', 0, 'extra_info_s', 0, 'select_s', 0, 'forecast_s', 0);
o = run_closed_loop(ax, ay, cm, pc_method(cm, 'SIMPLE-zero', z), struct('dt', cm.plant.dt));
t = o.timeline(o.timeline(:,4) == 1, 18); t = sort(t(2:end));
b = t(max(1, ceil(0.95*numel(t))));
c.latency.compute_s.select_C1 = b;
end
