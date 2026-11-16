function out = w5_sim_run(p, b, tl, t, ag, tS, Tlead, g, lxi)
%W5_SIM_RUN  w5_tlcd_eew.slx 를 한 번 실행합니다.
%
%   g   = [g0 g1 rate]    튜닝비 시작값 · 목표값 · 속도 [1/s]
%   lxi = [l0 l1 rate]    log2(기준 손실계수) 시작값 · 목표값 · 속도
%   출력은 w5_simulate 와 같은 지표 (rms_disp, peak_disp, stroke_use)

n = p.n;  mf = tl.mf;  a = tl.alpha;  e = b.e;
M = zeros(n+1);
M(1:n,1:n) = b.M + mf*(e*e');
M(1:n,end) = a*mf*e;  M(end,1:n) = a*mf*e';  M(end,end) = mf;
K0 = zeros(n+1);  K0(1:n,1:n) = b.K;
C0 = zeros(n+1);  C0(1:n,1:n) = b.C;
Lv = [-(b.M + mf*(e*e'))*b.r; -a*mf];

in = Simulink.SimulationInput('w5_tlcd_eew');
v = {'agTS',[t(:) ag(:)], 'dt',t(2)-t(1), 'Tend',t(end), 'tA',tS-Tlead, ...
     'g0',g(1), 'g1',g(2), 'rate_g',g(3), 'lxi0',lxi(1), 'lxi1',lxi(2), 'rate_xi',lxi(3), ...
     'M',M, 'K0',K0, 'C0',C0, 'Lv',Lv, 'mf',mf, 'cA',0.5*p.rho*tl.A, 'w1d',p.w1d, ...
     'stroke',tl.stroke, 'kstop',tl.k_stop};
for k = 1:2:numel(v), in = in.setVariable(v{k}, v{k+1}); end
so = sim(in);

x = reshape(so.xout, n+1, [])';       % 7×1×N 로 저장됨 → N × 7
top = x(:,n)';
out.top        = top;
out.rms_disp   = sqrt(mean(top.^2));
out.peak_disp  = max(abs(top));
out.stroke_use = max(abs(x(:,end))) / tl.stroke;
end
