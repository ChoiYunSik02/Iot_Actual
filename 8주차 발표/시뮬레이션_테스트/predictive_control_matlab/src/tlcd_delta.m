function d = tlcd_delta(P, kap)
% TLCD_DELTA  밸브 개도 kap의 국부 손실계수 (원문 식 24, rstlcd_sim.m의 dlt와 같음).
LAM = P.LAM;
d = (1-LAM)^2 + 0.5*abs(1-LAM) + LAM^2*((1-kap) + 0.707*(1-kap)^0.375)^2/kap^2;
end
