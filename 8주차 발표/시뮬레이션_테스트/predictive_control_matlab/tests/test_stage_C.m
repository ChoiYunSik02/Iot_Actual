function res = test_stage_C()
% TEST_STAGE_C  지연·버퍼·큐·장치 구현 시험 (계획서 13절 C: 미래 참조 차단, 정수 갱신·속도 제한·만료 처리).
%  결과: results/stage_C_check.csv
root = fileparts(fileparts(mfilename('fullpath'))); addpath(fullfile(root, 'src'));
cfg = pc_config(); cfg.latency.timing_mode = 'nominal'; cfg.latency.inject_select_s = 0; cfg.latency.inject_forecast_s = 0;
rows = {}; allpass = true;
[P, ~] = plant_init(cfg, 0.01);
M0 = pc_method(cfg, 'R', struct('select_s', 0));
P.rt = pc_runtime(cfg, P, M0, 3000);
% ---- T1 지령 대기열 ----
QS = command_queue_step([], [], []);
[QS, r0] = command_queue_step(QS, [1; 1; 0.33; 0; 0; 0; 0; 5], 3);
[QS, r1] = command_queue_step(QS, [1; 0; 0; 1; 0.5; 0; 0; 4], 4);
[QS, r2] = command_queue_step(QS, [1; 0; 0; 0; 0; 1; 0.8; 3], 5);   % 늦게 도착 (적용 스텝 3 < 5)
[rows, allpass] = chk(rows, allpass, 'T1a 큐: 적용 스텝 전에는 내보내지 않음', ~any(r0([1 3 5])));
[rows, allpass] = chk(rows, allpass, 'T1b 큐: 적용 스텝에 정확히 내보냄 (각도)', r1(3) == 1 && r1(4) == 0.5 && r1(1) == 0);
[rows, allpass] = chk(rows, allpass, 'T1c 큐: 펌프 지령은 스텝 5에 적용', r2(1) == 1 && r2(2) == 0.33);
[rows, allpass] = chk(rows, allpass, 'T1d 큐: 늦게 도착한 지령은 적용하지 않고 만료 처리', r2(5) == 0 && QS.n_expired == 1);
% ---- T2 장치 제한 ----
A = actuator_step([], [], [], P);
[A, d] = actuator_step(A, [1; 0.40; 1; pi; 1; 0.1], 0, P);
[rows, allpass] = chk(rows, allpass, 'T2a 진동수 목표는 범위로 제한', abs(A.f_tgt - P.FR(2)) < 1e-15);
[rows, allpass] = chk(rows, allpass, 'T2b 각도 목표는 0~90°로 제한', abs(A.th_tgt - pi/2) < 1e-15);
th = d(2); fs = d(1); okr = true;
for i = 1:400
    [A, d] = actuator_step(A, zeros(6,1), i, P);
    okr = okr && abs(d(2) - th) <= P.ROT*P.dt + 1e-15; th = d(2); fs(end+1) = d(1); %#ok<AGROW>
end
[rows, allpass] = chk(rows, allpass, 'T2c 회전 속도 ≤ 30°/s', okr);
k_end = find(abs(fs - P.FR(2)) < 1e-12, 1) - 1;
[rows, allpass] = chk(rows, allpass, 'T2d 펌프 램프 2.6 s (260 스텝) 뒤 목표 도달', k_end == 260, k_end);
% ---- T3 관측 버퍼·마스크 ----
BS = obsbuffer_step([], [], P);
trig = 300; okm = true; okv = true;
for st = 0:600
    a = 0.006*(st >= trig);                                % 트리거 문턱 0.005 → st=trig에서 트리거
    ob = zeros(296,1); ob(1) = 1; ob(2) = st; ob(3) = a; ob(4) = -a;
    [BS, bv] = obsbuffer_step(BS, ob, P);
    mk = bv(4+2*P.rt.Wn:end); wx = bv(4:3+P.rt.Wn);
    nvalid = max(0, st - trig + 1);
    okm = okm && sum(mk) == min(nvalid, P.rt.Wn) && all(wx(mk < 0.5) == 0) && bv(2) == st;
    okv = okv && (bv(1) > 0.5) == ((st - trig)*P.dt >= 1 - 1e-9);
end
[rows, allpass] = chk(rows, allpass, 'T3a 트리거 전·빈칸 mask 0, 값 0, 창 끝 = 최근 도착 시각', okm);
[rows, allpass] = chk(rows, allpass, 'T3b 첫 예측은 트리거 후 1 s 유효 관측부터', okv);
% ---- T4 입출력 배열 순서 ----
sc = struct('mu', [0.1 -0.2], 'sd', [2 4]);
Yx = (1:400)'; Yy = (401:800)';
t = pack_forecast_target(Yx, Yy, sc); Y = unpack_forecast_target(t, sc, 400);
[rows, allpass] = chk(rows, allpass, 'T4a 정답 800 = [X(1..400); Y(1..400)] 왕복', max(abs(Y(:) - [Yx; Yy])) < 1e-12 && abs(t(401) - (401+0.2)/4) < 1e-12);
X = forecast_input((1:500)', -(1:500)', [zeros(100,1); ones(400,1)], sc);
[rows, allpass] = chk(rows, allpass, 'T4b 입력 3x500 (채널 x 시간), 마스크 0 칸 = 0, 마스크 비표준화', isequal(size(X), [3 500]) && all(X(1,1:100) == 0) && ...
    abs(X(1,101) - (101-0.1)/2) < 1e-12 && all(X(3,:) == [zeros(1,100) ones(1,400)]));
% ---- 기록 (El Centro 앞 25 s) ----
[ax, ay] = load_record(cfg, 'ElCentro_1940', 0.01); ax = ax(1:2500); ay = ay(1:2500);
cut = 1500;                                              % 이 스텝부터 미래 입력만 바꿈
bx = ax; by = ay; bx(cut+1:end) = 3*ax(cut+1:end) + 0.05; by(cut+1:end) = -2*ay(cut+1:end);
% ---- T5 인과성: 같은 관측 접두부 → 같은 특징·예측·지령 ----
lat = struct('sensor_s', 0.1, 'comm_s', 0.05, 'extra_info_s', 0.5, 'select_s', 0, 'forecast_s', 0.05);
cases = {'SIMPLE-persistence', 'SIMPLE-zero'};
for c = 1:numel(cases)
    for L = 0:1
        if L, ov = lat; tag = '지연有'; else, ov = struct('select_s', 0, 'forecast_s', 0); tag = '지연0'; end
        M = pc_method(cfg, cases{c}, ov);
        oa = run_closed_loop(ax, ay, cfg, M, struct('dt', 0.01));
        ob = run_closed_loop(bx, by, cfg, M, struct('dt', 0.01));
        ds = oa.rt.d_s;
        ka = oa.timeline(:,1) <= cut - 1 + ds; kb = ob.timeline(:,1) <= cut - 1 + ds;
        same_cmd = isequaln(oa.timeline(ka, 1:17), ob.timeline(kb, 1:17));
        fa = oa.forecast.log(oa.forecast.log(:,1) <= cut - 1 + ds, [1 2 3 5]);
        fb = ob.forecast.log(ob.forecast.log(:,1) <= cut - 1 + ds, [1 2 3 5]);
        [rows, allpass] = chk(rows, allpass, sprintf('T5 %s %s: 접두부 같으면 지령·예측 기록 동일 (n=%d)', cases{c}, tag, sum(ka)), same_cmd && isequaln(fa, fb) && sum(ka) > 3);
        if L
            okd = all(oa.timeline(:,3) == oa.timeline(:,1) + oa.rt.d_cmd) && all(oa.timeline(:,2) <= oa.timeline(:,1) - ds);
            [rows, allpass] = chk(rows, allpass, sprintf('T6a %s: 결정 = 적용 - d_cmd, 사용 관측 ≤ 결정 - d_s', cases{c}), okd);
            fo = oa.forecast.log(oa.forecast.log(:,5) == 1, :);
            [rows, allpass] = chk(rows, allpass, sprintf('T6b %s: 예측 기준시각 ≤ 계산 시작 - d_s, 준비 = 시작 + d_fc', cases{c}), ...
                all(fo(:,2) <= fo(:,1) - ds) && all(fo(:,3) == fo(:,1) + oa.rt.d_fc));
            tl = oa.timeline(oa.timeline(:,4) == 1 & ~isnan(oa.timeline(:,12)), :);
            [rows, allpass] = chk(rows, allpass, sprintf('T6c %s: 사용한 예측은 결정 시점에 준비된 것', cases{c}), all(tl(:,13) <= tl(:,1)));
        end
    end
end
% 검정력 확인: PREVIEW(미래 입력 사용)는 이 시험에서 달라져야 한다
M = pc_method(cfg, 'PREVIEW-C1', struct('select_s', 0, 'forecast_s', 0));
oa = run_closed_loop(ax, ay, cfg, M, struct('dt', 0.01)); ob = run_closed_loop(bx, by, cfg, M, struct('dt', 0.01));
ka = oa.timeline(:,1) <= cut - 1; kb = ob.timeline(:,1) <= cut - 1;
[rows, allpass] = chk(rows, allpass, 'T5p 시험 검정력: PREVIEW는 접두부가 같아도 예측 비용 J가 달라짐', ~isequaln(oa.timeline(ka,16:17), ob.timeline(kb,16:17)));
% ---- T6d 지연을 늘려도 적용 시점은 격자 그대로 (과거로 당겨지지 않음) ----
Ma = pc_method(cfg, 'R', struct('select_s', 0)); Mb = pc_method(cfg, 'R', lat);
oa = run_closed_loop(ax, ay, cfg, Ma, struct('dt', 0.01)); ob = run_closed_loop(ax, ay, cfg, Mb, struct('dt', 0.01));
ga = oa.timeline(oa.timeline(:,4) == 1, 3); gb = ob.timeline(ob.timeline(:,4) == 1, 3);
ch_a = find(abs(diff(oa.f_dev(2:end))) > 0, 1); ch_b = find(abs(diff(ob.f_dev(2:end))) > 0, 1);
[rows, allpass] = chk(rows, allpass, 'T6d 지연 증가: 펌프·각도 적용 격자 동일, 첫 장치 변화 시점 동일', isequal(ga, gb) && all(mod(gb, P.nF) == 0) && ch_a == ch_b, ch_b);
[rows, allpass] = chk(rows, allpass, 'T6e 지연 증가: 결정 시각은 적용 - d_cmd로 앞당겨짐', all(ob.timeline(:,1) == ob.timeline(:,3) - ob.rt.d_cmd) && ob.rt.d_cmd == 55);
[rows, allpass] = chk(rows, allpass, 'T6f 큐 만료 0 (고정 지연)', ob.queue.n_expired == 0);
% ---- T7 작업자 1개: 계산 지연 > 갱신 주기면 건너뜀을 셈 ----
M = pc_method(cfg, 'SIMPLE-zero', struct('select_s', 0, 'forecast_s', 0.25));
o = run_closed_loop(ax, ay, cfg, M, struct('dt', 0.01));
[rows, allpass] = chk(rows, allpass, 'T7 계산 지연 0.25 s > 0.2 s: 건너뛴 갱신을 miss로 기록', o.forecast.miss_busy > 0 && all(diff(o.forecast.log(o.forecast.log(:,5)==1,1)) >= 26), o.forecast.miss_busy);
% ---- T8 실제 계산시간 반영 (timing_mode='actual', 인위 계산시간 주입으로 결정론적 확인) ----
ca = cfg; ca.latency.timing_mode = 'actual';
% (a) 계산 0.3 s < 예산 0.5 s (R, 실제 계산이 짧아 결정론적): 지령은 계산이 끝나 도착한 뒤 격자에 적용
ca.latency.inject_select_s = 0.3;
o = run_closed_loop(ax, ay, ca, pc_method(ca, 'R', struct('select_s', 0.5)), struct('dt', 0.01));
tl = o.timeline; pa = tl(:,4) == 1;
o0 = run_closed_loop(ax, ay, cfg, pc_method(cfg, 'R', struct('select_s', 0.5)), struct('dt', 0.01));
[rows, allpass] = chk(rows, allpass, 'T8a 계산 0.3 s < 예산 0.5 s: 결정+30스텝 ≤ 도착 ≤ 적용 격자, 늦음 0, 장치 동작은 nominal과 동일', ...
    all(tl(pa,22) <= tl(pa,3) + 1e-9) && all(tl(pa,22) >= tl(pa,1) + 30 - 1e-9) && ~any(tl(:,19)) && isequal(o.f_dev, o0.f_dev));
% (b) 선택 계산 0.6 s > 예산 0.5 s: 늦은 후보 지령은 적용하지 않고 제때 온 R 지령 적용
ca.latency.inject_select_s = 0.6;
o = run_closed_loop(ax, ay, ca, pc_method(ca, 'SIMPLE-zero', struct('select_s', 0.5, 'forecast_s', 0)), struct('dt', 0.01));
tl = o.timeline; pa = tl(:,4) == 1;
[rows, allpass] = chk(rows, allpass, 'T8b 계산 0.6 s > 예산 0.5 s: 모든 펌프·각도 결정이 늦음 → R 지령(사유 deadline)', ...
    all(tl(pa,19) == 1) && all(tl(pa,20) == 7) && isequaln(tl(pa,6), tl(pa,9)) && isequaln(tl(pa,7), tl(pa,10)));
% (c) R도 늦으면 이전 지령 유지 (장치 목표가 바뀌지 않음)
ca.latency.inject_select_s = 0.05;
o = run_closed_loop(ax, ay, ca, pc_method(ca, 'R', struct('select_s', 0)), struct('dt', 0.01));
[rows, allpass] = chk(rows, allpass, 'T8c R 계산 0.05 s > 예산 0: 지령 보류(deadline_hold), 장치 초기값 유지', ...
    all(o.timeline(:,20) == 8) && all(o.f_dev(2:end) == o.f_dev(2)) && all(o.theta == 0));
% (d) 예측 계산 0.35 s: 준비 시각 = 시작 + ceil(실측/dt) ≥ 35스텝, 그 사이 갱신은 건너뜀
ca.latency.inject_select_s = 0; ca.latency.inject_forecast_s = 0.35;
o = run_closed_loop(ax, ay, ca, pc_method(ca, 'SIMPLE-zero', struct('select_s', 0, 'forecast_s', 0.05)), struct('dt', 0.01));
fl = o.forecast.log(o.forecast.log(:,5) == 1, :);
tl = o.timeline; use = tl(:,4) == 1 & ~isnan(tl(:,13));
[rows, allpass] = chk(rows, allpass, 'T8d 예측 계산 0.35 s: 준비 ≥ 시작+35, 갱신 건너뜀 기록, 쓴 예측은 준비 후', ...
    all(fl(:,3) - fl(:,1) >= 35) && o.forecast.miss_busy > 0 && o.forecast.miss_deadline == size(fl,1) && all(tl(use,13) <= tl(use,1)));
% ---- T9 실측 계산시간이 방식 설정에 들어가는지 (노트북 첫 D에서 예산이 항상 0이던 버그 재발 방지) ----
cm = cfg; cs = cm.latency.compute_s; cs.R = 0.0009; cs.select_C1 = 0.54; cs.forecast_persistence = 2e-5; cm.latency.compute_s = cs;
Mr = pc_method(cm, 'R'); Ms = pc_method(cm, 'SIMPLE-persistence');
[Pm, ~] = plant_init(cm, 0.01); rr = pc_runtime(cm, Pm, Mr, 100); rs = pc_runtime(cm, Pm, Ms, 100);
[rows, allpass] = chk(rows, allpass, 'T9 실측 예산 반영: R 0.0009 s → d_cmd 1, C1 0.54 s → d_cmd 54, persistence 예측 → d_fc 1', ...
    Mr.select_s == 0.0009 && rr.d_cmd == 1 && Ms.select_s == 0.54 && rs.d_cmd == 54 && Ms.forecast_s == 2e-5 && rs.d_fc == 1 && isempty(Ms.unmeasured));
% ---- T10 원래 시각 R 경로: 모든 제안을 거부하면 독립 R 실행과 지령·응답이 비트 단위로 같다 (8주차, report/design_shadowR.md 2절) ----
[ax10, ay10] = load_record(cfg, 'ElCentro_1940', 0.01); n10 = min(numel(ax10), 2001); ax10 = ax10(1:n10); ay10 = ay10(1:n10);
cf = cfg; cf.latency.timing_mode = 'nominal'; cf.latency.sensor_s = 0; cf.latency.comm_s = 0; cf.latency.extra_info_s = 0;
cs = cf.latency.compute_s; cs.R = 0.01; cs.select_C1 = 0.51; cs.forecast_zero = 0.01; cs.forecast_preview = 0.01; cf.latency.compute_s = cs;
cf.controller.C1.default_path = 'ontime';
oR = run_closed_loop(ax10, ay10, cf, pc_method(cf, 'R'), struct('dt', 0.01));
oA = run_closed_loop(ax10, ay10, cf, pc_method(cf, 'PREVIEW-C1'), struct('dt', 0.01, 'force_reject', true));
same10 = @(a, b) isequal(a.ux, b.ux) && isequal(a.uy, b.uy) && isequal(a.th, b.th) && isequal(a.f_dev, b.f_dev) && isequal(a.theta, b.theta) && isequal(a.kappa, b.kappa);
[rows, allpass] = chk(rows, allpass, 'T10a ontime·모든 제안 거부(nominal) = 독립 R (응답·장치 비트 동일)', same10(oR, oA));
ca10 = cf; ca10.latency.timing_mode = 'actual'; cs = ca10.latency.compute_s; cs.R = 0.05; ca10.latency.compute_s = cs; ca10.latency.inject_select_s = 10;
cR10 = ca10; cR10.latency.inject_select_s = 0;                    % R 방식에는 선택 계산 주입을 넣지 않음 (R 자체 계산만)
oRa = run_closed_loop(ax10, ay10, cR10, pc_method(cR10, 'R'), struct('dt', 0.01));
oAa = run_closed_loop(ax10, ay10, ca10, pc_method(ca10, 'SIMPLE-zero'), struct('dt', 0.01));
tlA = oAa.timeline(oAa.timeline(:,4) == 1, :);
[rows, allpass] = chk(rows, allpass, 'T10b ontime·모든 제안 늦음(actual, 선택 10 s 주입) = 독립 R', same10(oRa, oAa) && all(tlA(~isnan(tlA(:,18)), 19) == 1));
oL = run_closed_loop(ax10, ay10, setfield(cf, 'controller', setfield(cf.controller, 'C1', setfield(cf.controller.C1, 'default_path', 'lagged'))), ...
                     pc_method(cf, 'PREVIEW-C1'), struct('dt', 0.01, 'force_reject', true)); %#ok<SFLD>
[rows, allpass] = chk(rows, allpass, 'T10c 기존 lagged 경로는 모두 거부해도 R과 다름 (늦은 R 후보 적용 구분)', ~same10(oR, oL));
% ---- T11 그림자 R(감시 전용): 개입이 없으면 실제 응답·독립 R과 같고, 관측 시각 뒤의 입력을 쓰지 않는다 ----
oS = run_closed_loop(ax10, ay10, cf, pc_method(cf, 'SIMPLE-zero'), struct('dt', 0.01, 'force_reject', true, 'shadow_monitor', true));
[rows, allpass] = chk(rows, allpass, 'T11a 그림자 R 비틀림 = 실제 비틀림 (모든 제안 거부)', isequal(oS.shadow.th, oS.th));
[rows, allpass] = chk(rows, allpass, 'T11b 그림자 R 비틀림 = 독립 R 실행 비틀림', isequal(oS.shadow.th, oR.th));
cs11 = cf; cs11.controller.C1.constraint = 'shadow'; cs11.controller.C1.angle_mode = 'absolute';
o1 = run_closed_loop(ax10, ay10, cs11, pc_method(cs11, 'SIMPLE-zero'), struct('dt', 0.01));
ax2 = ax10; ay2 = ay10; ax2(1201:end) = 3*ax2(1201:end); ay2(1201:end) = -ay2(1201:end);     % 12 s 뒤 입력만 바꿈
o2 = run_closed_loop(ax2, ay2, cs11, pc_method(cs11, 'SIMPLE-zero'), struct('dt', 0.01));
t1 = o1.timeline(o1.timeline(:,3) <= 1150, :); t2 = o2.timeline(o2.timeline(:,3) <= 1150, :);
[rows, allpass] = chk(rows, allpass, 'T11c 그림자 R 제한·절대 각도: 12 s 뒤 입력을 바꿔도 11.5 s까지 결정 동일 (인과성)', ...
    isequaln(t1(:, [1:17 20]), t2(:, [1:17 20])) && isequal(o1.th(1:1151), o2.th(1:1151)));
nc = o1.timeline(o1.timeline(:,4) == 1, 14);
[rows, allpass] = chk(rows, allpass, sprintf('T11d 절대 각도 후보 수 기록 (최대 %d ≥ 15)', max(nc)), max(nc) >= 15);
% ---- T12 8주차 v2 공동 선택(J): 펌프·회전판·밸브 ----
cj = cf; cs = cj.latency.compute_s; cs.select_J = 0.51; cs.select_JV = 0.31; cj.latency.compute_s = cs;
oJ0 = run_closed_loop(ax10, ay10, cj, pc_method(cj, 'J-PREVIEW'), struct('dt', 0.01, 'force_reject', true));
[rows, allpass] = chk(rows, allpass, 'T12a J·모든 제안 거부 = 독립 R (응답·펌프·회전·밸브 비트 동일)', same10(oR, oJ0));
oJ = run_closed_loop(ax10, ay10, cj, pc_method(cj, 'J-zero'), struct('dt', 0.01, 'jpolicy', 'eval', 'teach_g', [520 600]));
tl = oJ.timeline; P12 = plant_init(cj, 0.01);
gp = tl(tl(:,4) == 1, :); gv = tl(tl(:,5) == 1, :); kv = gv(~isnan(gv(:,8)), 8);
okg = all(mod(gp(:,3), 260) == 0) && all(mod(gv(:,3), 100) == 0) && all(ismember(round(kv*10), [1 4 8]));
okr = all(gp(~isnan(gp(:,6)), 6) >= P12.FR(1) - 1e-15 & gp(~isnan(gp(:,6)), 6) <= P12.FR(2) + 1e-15) && all(gp(~isnan(gp(:,7)), 7) >= 0 & gp(~isnan(gp(:,7)), 7) <= pi/2 + 1e-15);
jk = find(diff(oJ.kappa(2:end)) ~= 0) + 2;                         % kappa(j) = 스텝 j−2의 장치 출력
oks = all(mod(jk - 2, 100) == 0) && all(abs(diff(oJ.theta(2:end))) <= P12.ROT*0.01 + 1e-12);
nac = sum(oJ.jlog(:,15) == 1);
[rows, allpass] = chk(rows, allpass, sprintf('T12b J 격자·범위·속도: 펌프·각도 2.6 s, 밸브 1 s 격자에서만 변경, κ∈{0.1,0.4,0.8}, 30°/s (적용 제안 %d)', nac), okg && okr && oks && nac > 0);
J1 = oJ.jlog(oJ.jlog(:,4) == 1, :); J2 = oJ.jlog(oJ.jlog(:,4) == 2, :);
[rows, allpass] = chk(rows, allpass, sprintf('T12c J 후보 수: 느린 %d~%d (≤ 47, 중복 제거), 빠른 ≤ 5', min(J1(:,5)), max(J1(:,5))), max(J1(:,5)) <= 47 && min(J1(:,5)) >= 15 && max(J2(:,5)) <= 5);
o2 = run_closed_loop(ax2, ay2, cj, pc_method(cj, 'J-zero'), struct('dt', 0.01));
q1 = oJ.jlog(oJ.jlog(:,3) <= 1150, :); q2 = o2.jlog(o2.jlog(:,3) <= 1150, :);
t1 = oJ.timeline(oJ.timeline(:,3) <= 1150, :); t2 = o2.timeline(o2.timeline(:,3) <= 1150, :);
[rows, allpass] = chk(rows, allpass, 'T12d J 인과성: 12 s 뒤 입력을 바꿔도 11.5 s까지 결정·응답 동일', ...
    isequaln(q1(:, [1:15 17 18]), q2(:, [1:15 17 18])) && isequaln(t1(:, [1:17 20]), t2(:, [1:17 20])) && isequal(oJ.th(1:1151), o2.th(1:1151)));
T = oJ.tlog; okf = ~isempty(T);
for r = 1:size(T, 1)
    jr = oJ.jlog(oJ.jlog(:,3) == T(r,1), :); s_ = jr(1, 2); i_ = jr(1, 1); X = T(r, 6:103);
    okf = okf && abs(X(1) - oJ.ux(s_+1)) < 1e-15 && abs(X(3) - oJ.th(s_+1)) < 1e-15 && abs(X(22) - (T(r,1) - i_)*0.01) < 1e-12 && X(21) >= 0 && X(86) == 1;
end
okl = okf && all(isfinite(T(T(:,4) == 1, 104))) && numel(unique(T(:,1))) == 2;
[rows, allpass] = chk(rows, allpass, sprintf('T12e 상태 특징 좌표·시각 (관측 s의 최상층 응답, 적용까지 시간 = d_cmd), teacher 라벨 %d행', size(T, 1)), okl);
oC = run_closed_loop(ax10, ay10, cj, pc_method(cj, 'C1J-AI', struct('forecaster', 'zero')), struct('dt', 0.01));
vC = oC.timeline(oC.timeline(:,5) == 1 & ~isnan(oC.timeline(:,8)), :);
[rows, allpass] = chk(rows, allpass, 'T12f C1J(밸브 절제): 모든 밸브 지령 = 그 시각 R 법칙, 빠른 결정 없음', isequal(vC(:,8), vC(:,11)) && ~any(oC.jlog(:,4) == 2));
rows(end+1,:) = {'ALL', 'ALL', 'overall_pass', double(allpass), NaN, allpass};
write_check_csv(fullfile(root, 'results', ['stage_C_check' out_tag() '.csv']), rows, env_string());
res = struct('pass', allpass);
fprintf('C 판정: %d (%s)\n', allpass, env_string());
end

function [rows, allpass] = chk(rows, allpass, name, ok, val)
if nargin < 5, val = double(ok); end
rows(end+1,:) = {'-', '-', name, val, NaN, ok};
allpass = allpass && ok;
fprintf('%-58s %d\n', name, ok);
end
