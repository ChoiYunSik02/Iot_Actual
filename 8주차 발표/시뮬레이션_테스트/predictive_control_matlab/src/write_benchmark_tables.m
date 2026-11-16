function write_benchmark_tables(root, tag, recs, S, methods, cfg)
% WRITE_BENCHMARK_TABLES  run_benchmarks 결과 표 3개 (기록별·사건별·요약). results/benchmarks_<tag>.mat에서 다시 만들 수 있다.
env = env_string(); names = cfg.evaluation.metrics;
f = fopen(fullfile(root, 'results', ['control_metrics_record_' tag '.csv']), 'w');
fprintf(f, 'env,record_id,event_id,method,%s,%s,rotation_deg,pump_change_hz,valve_switches,wall_s\n', strjoin(names', ','), strjoin(strcat('red_', names'), ','));
for k = 1:numel(recs)
    iu = find(strcmp({recs.record_id}, recs(k).record_id) & strcmp({recs.method}, 'U'), 1);
    rd = 100*(1 - recs(k).metrics./recs(iu).metrics);
    fprintf(f, '%s,%s,%s,%s,%s%s,%.6g,%.6g,%d,%.3f\n', env, recs(k).record_id, recs(k).event_id, recs(k).method, ...
            sprintf('%.6e,', recs(k).metrics), [sprintf('%.4f,', rd(1:5)) sprintf('%.4f', rd(6))], ...
            recs(k).burden(1), recs(k).burden(2), recs(k).burden(3), recs(k).wall_s);
end
fclose(f);
f = fopen(fullfile(root, 'results', ['control_metrics_event_' tag '.csv']), 'w');
fprintf(f, 'env,event_id,method,%s,score6,dS_vs_R_pp\n', strjoin(strcat('red_', names'), ','));
iR = find(strcmp(methods, 'R'), 1);
for m = 1:numel(methods)
    for e = 1:numel(S.events)
        d = NaN; if ~isempty(iR), d = S.score_event(e, m) - S.score_event(e, iR); end
        fprintf(f, '%s,%s,%s,%s%.4f,%.4f\n', env, S.events{e}, methods{m}, sprintf('%.4f,', S.red_event(e,:,m)), S.score_event(e, m), d);
    end
end
fclose(f);
f = fopen(fullfile(root, 'results', ['comparison_summary_' tag '.csv']), 'w');
fprintf(f, 'env,method,n_events,S_pct,dS_vs_R_pp,ci95_lo,ci95_hi,n_better,n_worse,worst_event_dS_pp,torsion_worse_events,torsion_worst_pp,note\n');
for m = 1:numel(methods)
    fprintf(f, '%s,%s,%d,%.4f,%.4f,%.4f,%.4f,%d,%d,%.4f,%d,%.4f,%s\n', env, methods{m}, numel(S.events), S.S(m), S.dS(m), S.ci(1,m), S.ci(2,m), ...
            S.n_better(m), S.n_worse(m), S.worst_dS(m), S.tor_worse_events(m), S.tor_worst_pp(m), ...
            '개발 사건(시험 아님); 사건 수가 적어 bootstrap 구간은 탐색적');
end
fclose(f);
end
