%W5_MAIN  5주차 — 지진 예측 선제 제어 실험 (리드타임 × 전략 × 예보 오차)
%
%   흐름
%     1) 경보 시각 = S파 도착(w5_record 의 info.tS) − 리드타임
%     2) 경보와 함께 "예측 PGA" 가 들어오고, 설정표(w5_lookup)에서 목표 설정을 찾음
%     3) 각 액추에이터가 자기 속도 한계 안에서 목표로 이동 (w5_setting)
%     4) 흔들림 중에는 밸브가 Δ-DBG 로 계속 개폐
%
%   전략
%     S0  사전 동작 없음 (0.2g 기준 설정 고정)
%     S1  밸브만 프리셋        (xi,    0.05 s)
%     S2  펌프만 재튜닝        (gamma, 30 s)
%     S3  밸브 + 펌프
%     S4  밸브 + 공기압 재튜닝 (gamma, 3 s)
%
%   입력: 실관측 기록 3개 (records/README.md) — 포항·경주는 부산 관측소 원거리 기록

addpath('..');
if ~exist('AXES','var'), AXES = 1; end      % 2 로 두고 실행하면 X·Y 2축
[p, ~, tl] = w5_params(AXES);
S = load(['w5_lookup' p.tag '.mat']);                 % LTA, LTB (w5_lookup 으로 생성)

recs   = {'gyeongju','pohang','elcentro'};
leads  = [-3 0 2 5 10 15 30 45 60];
pgas   = [0.2 0.4 0.6];
errs   = [0.5 1 2];                        % 예측 PGA = 실제 × err
scens  = {'A','B'};
strat  = {'S0','S1','S2','S3','S4'};
g_span = diff(p.gamma_range);
xi_span = log2(64) - log2(0.25);           % 밸브는 log2(xi) 단위로 이동

figdir = fullfile('..','..','5주차 발표','그림',p.figsub);
if ~exist(figdir,'dir'), mkdir(figdir); end

% 기본 설정 = 0.2g 설계표 최적값 (4주차처럼 0.2g 기준으로 맞춘 상태)
xi0 = interp1(S.LTA.pga, S.LTA.best_xi, 0.2);
g0  = interp1(S.LTA.pga, S.LTA.best_gamma, 0.2);   % 기본 튜닝비도 0.2g 최적값

R = [];   % 결과 행: [scen pga rec lead err strat red stroke]
for is = 1:2
    LT = S.(['LT' scens{is}]);
    for ip = 1:numel(pgas)
        b = w5_building(p, pgas(ip), scens{is});
        for ir = 1:numel(recs)
            [ag, t, info] = w5_record(recs{ir}, pgas(ip), p.dt, p.T, p.axes);
            t = t(:)';  N = numel(t);  tS = info.tS;
            U  = w5_simulate(p,b,tl,t,ag,[],[],false).rms_disp;
            for ie = 1:numel(errs)
                pp = min(max(pgas(ip)*errs(ie), LT.pga(1)), LT.pga(end));
                xi1 = 2^interp1(LT.pga, log2(LT.best_xi), pp);
                g1  = interp1(LT.pga, LT.best_gamma, pp);
                for il = 1:numel(leads)
                    L = leads(il);
                    for k = 1:numel(strat)
                        lxi = log2(xi0)*ones(1,N);  gam = g0*ones(1,N);
                        if any(k == [2 4 5])
                            lxi = w5_setting(t,tS,L,log2(xi0),log2(xi1),xi_span/p.T_valve);
                        end
                        if any(k == [3 4])
                            gam = w5_setting(t,tS,L,g0,g1,g_span/p.T_pump);
                        elseif k == 5
                            gam = w5_setting(t,tS,L,g0,g1,g_span/p.T_air);
                        end
                        o = w5_simulate(p,b,tl,t,ag,gam,2.^lxi,true);
                        R(end+1,:) = [is pgas(ip) ir L errs(ie) k ...
                                      100*(1-o.rms_disp/U) o.stroke_use]; %#ok<SAGROW>
                    end
                end
            end
        end
    end
    fprintf('scenario %s done\n', scens{is});
end
save(['w5_results' p.tag '.mat'],'R','leads','pgas','errs','scens','strat','recs');

T = array2table(R, 'VariableNames', ...
    {'scenario','pga','rec','lead_s','pred_err','strategy','rms_red_pct','stroke_use'});
writetable(T, fullfile('..','..','5주차 발표',['w5_results' p.tag '.csv']));

w5_plots;
