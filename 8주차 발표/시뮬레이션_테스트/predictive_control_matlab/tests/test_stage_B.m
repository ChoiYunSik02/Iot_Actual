function res = test_stage_B(varargin)
% TEST_STAGE_B  한 스텝 엔진(run_closed_loop, 지연 0) 대 기준 엔진 rstlcd_sim.m · Python 기준값(validation_ref.mat).
%  완료 조건(계획서 13절 B): 기존 대조 사례 재현.
%  비교: El Centro·포항·고베 × U·R·FIX(=FA, 0.34857 Hz·45°)
%   (a) rstlcd_sim.m 대비: 시계열 정규화 최대 오차 ≤ 1e-12, 장치 상태 동일
%   (b) validation_ref.mat(Python) 대비: run_validation.m과 같은 기준 (U ≤ 1e-6, 제어 ≤ 1e-3, κ 불일치 0스텝, 6지표 ≤ 1e-3)
%  결과: results/stage_B_check.csv
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config();
eng = fullfile(root, cfg.paths.reference_engine); addpath(fileparts(eng));
ref = load(fullfile(root, cfg.paths.validation_ref));
cfg.latency.timing_mode = 'nominal';
z = struct('sensor_s', 0, 'comm_s', 0, 'extra_info_s', 0, 'select_s', 0, 'forecast_s', 0);
recs = {'ElCentro', 'Pohang', 'Kobe'};
pols = {'U', 'R', 'FIX'}; refname = {'U', 'R', 'FA'};
rows = {}; allpass = true;
for r = 1:numel(recs)
    R0 = ref.(recs{r}); agx = double(R0.agx(:)); agy = double(R0.agy(:));
    for p = 1:numel(pols)
        M = pc_method(cfg, pols{p}, z);
        t0 = tic; o = run_closed_loop(agx, agy, cfg, M, struct('dt', 0.01)); el = toc(t0);
        switch pols{p}
            case 'U',   op = struct('case', 'none');
            case 'R',   op = struct('case', 'rstlcd', 'fpol', 'law', 'thpol', 'law');
            case 'FIX', op = struct('case', 'rstlcd', 'fpol', 'const', 'fval', cfg.fix.f_hz, 'thpol', 'const', 'thval', cfg.fix.theta_deg*pi/180);
        end
        t1 = tic; b = rstlcd_sim(agx, agy, 0.01, op); el2 = toc(t1);
        py = R0.(refname{p});
        for c = {'ux', 'uy', 'th', 'f_dev', 'theta', 'kappa'}
            nm = c{1};
            if strcmp(pols{p}, 'U') && any(strcmp(nm, {'f_dev', 'theta', 'kappa'})), continue; end
            y = o.(nm); xb = b.(nm); xp = double(py.(nm)(:));
            if strcmp(nm, 'kappa')
                d1 = sum(y ~= xb); d2 = sum(y ~= xp); ok1 = d1 == 0; ok2 = d2 == 0; thr = 0; thr2 = 0;
            else
                d1 = max(abs(y - xb))/max(max(abs(xb)), eps); d2 = max(abs(y - xp))/max(max(abs(xp)), eps);
                thr = 1e-12; if strcmp(pols{p}, 'U'), thr2 = 1e-6; else, thr2 = 1e-3; end
                ok1 = d1 <= thr; ok2 = d2 <= thr2;
            end
            rows(end+1,:) = {recs{r}, pols{p}, [nm '_vs_rstlcd_sim'], d1, thr, ok1}; %#ok<AGROW>
            rows(end+1,:) = {recs{r}, pols{p}, [nm '_vs_python_ref'], d2, thr2, ok2}; %#ok<AGROW>
            allpass = allpass && ok1 && ok2;
        end
        mp = double(py.metrics(:))'; d = max(abs(o.metrics - mp)./abs(mp)); ok = d <= 1e-3;
        rows(end+1,:) = {recs{r}, pols{p}, 'metrics_vs_python_ref', d, 1e-3, ok}; %#ok<AGROW>
        allpass = allpass && ok;
        rows(end+1,:) = {recs{r}, pols{p}, 'wall_s_step_engine', el, NaN, true}; %#ok<AGROW>
        rows(end+1,:) = {recs{r}, pols{p}, 'wall_s_rstlcd_sim', el2, NaN, true}; %#ok<AGROW>
        fprintf('%-9s %-4s  %.1f s / %.1f s\n', recs{r}, pols{p}, el, el2);
    end
end
rows(end+1,:) = {'ALL', 'ALL', 'overall_pass', double(allpass), NaN, allpass};
write_check_csv(fullfile(root, 'results', ['stage_B_check' out_tag() '.csv']), rows, env_string());
res = struct('pass', allpass, 'rows', {rows});
fprintf('B 판정: %d (%s)\n', allpass, env_string());
end
