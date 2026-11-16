function b = w5_building(p, pga, scenario)
%W5_BUILDING  시나리오별 건물. 'A' = 강성 일정, 'B' = 강진 시 강성 저하(가정).
q = p;
if upper(scenario) == 'B', q.k = p.k * (1 - p.soft(pga)); end
b = build_building(q);
end
