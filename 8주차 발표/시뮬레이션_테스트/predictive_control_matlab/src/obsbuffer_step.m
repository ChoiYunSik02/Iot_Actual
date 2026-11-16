function [BS, bufv] = obsbuffer_step(BS, obsv, P)
% OBSBUFFER_STEP  실제로 도착한 관측만 보관하고 AI 입력 창(100 Hz, 최대 5 s)을 만든다.
%  원본 측정 시각(stamp)과 도착 시각을 구분한다: 창의 끝은 '도착한 가장 최근 100 Hz 샘플의 측정 시각'.
%  bufv = [valid; newest_stamp; trig_stamp; win_x(500); win_y(500); mask(500)]  (길이 1503)
%   valid=1 : 트리거 이후 유효 관측이 first_after_trigger_s 이상 쌓임 (첫 예측 가능)
%   mask    : 트리거 이후 도착 샘플 1, 그 외(트리거 전·기록 시작 전 빈칸) 0, 값은 0으로 둔다.
%  미래 샘플은 이 버퍼에 존재하지 않는다(도착한 것만 쓴다).
rt = P.rt;
if isempty(BS)
    BS = struct('gx', zeros(rt.nmax100,1), 'gy', zeros(rt.nmax100,1), 'n100', 0, ...
                'newest', -1, 'trig', -1);
    bufv = zeros(3 + 3*rt.Wn, 1);
    return;
end
if obsv(1) > 0.5
    st = obsv(2); agx = obsv(3); agy = obsv(4);
    if BS.trig < 0 && max(abs(agx), abs(agy)) > rt.trigger
        BS.trig = st;
    end
    if mod(st, rt.r) == 0
        q = st/rt.r;                        % 100 Hz 샘플 번호 (0부터)
        BS.gx(q+1) = agx; BS.gy(q+1) = agy; BS.n100 = q+1; BS.newest = st;
    end
end
Wn = rt.Wn;
wx = zeros(Wn,1); wy = zeros(Wn,1); mk = zeros(Wn,1); valid = 0;
if BS.newest >= 0
    [wx, wy, mk] = make_window(BS.gx, BS.gy, BS.newest/rt.r, BS.trig, rt.r, Wn);
    if BS.trig >= 0 && (BS.newest - BS.trig)*P.dt >= rt.first_after_trigger_s - 1e-9
        valid = 1;
    end
end
bufv = [valid; BS.newest; BS.trig; wx; wy; mk];
end
