function Y = forecast_simple(kind, wx, wy, mk, model, Hn)
% FORECAST_SIMPLE  비교 예측기 (AI와 같은 입력 창·같은 지평 Hn 출력, 단위 m/s²).
%  'zero'        : 0
%  'persistence' : 마지막 유효 관측값 유지
%  'var'         : 2성분 VAR(L), ridge. 학습 분할 scaler로 정규화한 유효 샘플만 쓰고(마스크 0 = 0), 재귀로 Hn 스텝 출력
%  Y : Hn x 2 [X Y]
switch kind
    case 'zero'
        Y = zeros(Hn, 2);
    case 'persistence'
        if mk(end) > 0.5, Y = repmat([wx(end), wy(end)], Hn, 1); else, Y = zeros(Hn, 2); end
    case 'var'
        L = model.lags; B = model.B;              % B : (2L) x 2,  [zx(t-1..t-L) zy(t-1..t-L)] -> [zx(t) zy(t)]
        zx = (wx - model.mu(1))/model.sd(1); zy = (wy - model.mu(2))/model.sd(2);
        zx(mk < 0.5) = 0; zy(mk < 0.5) = 0;
        hx = flipud(zx(end-L+1:end)); hy = flipud(zy(end-L+1:end));   % 최근 샘플이 맨 앞
        Z = zeros(Hn, 2);
        for k = 1:Hn
            z = [hx; hy]' * B;
            Z(k,:) = z;
            hx = [z(1); hx(1:end-1)]; hy = [z(2); hy(1:end-1)];
        end
        Y = [Z(:,1)*model.sd(1) + model.mu(1), Z(:,2)*model.sd(2) + model.mu(2)];
    otherwise
        error('forecast_simple: kind %s', kind);
end
end
