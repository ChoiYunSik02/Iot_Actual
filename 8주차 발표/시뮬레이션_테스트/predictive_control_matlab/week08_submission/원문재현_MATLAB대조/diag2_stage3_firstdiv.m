% 사후 진단 2: 3단계 불합격 4건의 최초 분기 스텝과 오차 성장. 판정 기준은 바꾸지 않는다.
here = fileparts(mfilename('fullpath')); dt = 0.01;
cases = {'14','D0','RA'; '14','D3','RA'; '15','D0','RA'; '15','D4','RA'};
fid = fopen(fullfile(here,'matlab_out','stage3_diag2_firstdiv.txt'),'w'); pr = @(varargin) fprintf(fid,varargin{:});
for k = 1:size(cases,1)
  rec = cases{k,1}; d = cases{k,2}; rt = cases{k,3};
  a = readmatrix(fullfile(here,'inputs',['PEER' rec '.csv'])); x = a(:,1); y = a(:,2);
  o = tlcd_sim(x,y,dt,struct('case','rstlcd','damp',d,'cos_twice',strcmp(rt,'RA')));
  base = fullfile(here,'python_ref_r',['PEER' rec '_rs' rt '_' d]);
  P = readmatrix([base '_resp.csv']); Tc = readmatrix([base '_tcmd.csv']); Fc = readmatrix([base '_fcmd.csv']); Kc = readmatrix([base '_kcmd.csv']);
  M = [o.ux o.uy o.th]; pk = max(abs(P(:,1:3)));   % 신호별 피크
  pr('=== rec %s %s %s ===\n',rec,d,rt);
  pr('input_sha_note: inputs/PEER%s.csv dt=%.2f n=%d\n',rec,dt,numel(x));
  pr('fcmd steps equal=%d maxdiff_Hz=%.3e | kcmd identical=%d | thcmd steps equal=%d\n', isequal(Fc(:,1),o.f_cmd(:,1)), max(abs(Fc(:,3)-o.f_cmd(:,3))), isequal(Kc(:,1:2),o.k_cmd(:,1:2)), isequal(Tc(:,1),o.th_cmd(:,1)));
  dth = abs(Tc(:,2)-o.th_cmd(:,2)); bad = find(dth > 1e-9);
  pr('thcmd diffs > 1e-9 rad (pre-registered limit): count=%d of %d; steps:%s\n',numel(bad),numel(dth),sprintf(' %d',Tc(bad,1)));
  pr('thcmd diff by command (rad): first10=%s ... last5=%s\n',sprintf(' %.1e',dth(1:10)),sprintf(' %.1e',dth(end-4:end)));
  for s = 1:3
    nm = {'ux','uy','th'}; e = abs(M(:,s)-P(:,s)); 
    for lim = [1e-12 1e-10 1e-8]
      f = find(e > lim*pk(s),1); if isempty(f), fs = -1; else, fs = f-1; end
      pr('%s: first step abs err > %.0e*peak : %d\n',nm{s},lim,fs);
    end
    pr('%s: max abs err=%.3e (rel to peak %.3e) at step %d; err at steps 5000/10000/15000/15600/15860 = %.2e %.2e %.2e %.2e %.2e\n',nm{s},max(e),max(e)/pk(s),find(e==max(e),1)-1,e(5001),e(10001),e(15001),e(15601),e(15861));
    i1 = 15600; j0 = i1-260; pr('%s: window(15340..15600) max |signal| = %.3e (peak %.3e)\n',nm{s},max(abs(P(j0+1:i1,s))),pk(s));
  end
  writematrix([(0:size(P,1)-1)' abs(M(:,1:3)-P(:,1:3))],fullfile(here,'matlab_out',sprintf('stage3_errseries_%s_%s_%s.csv',rec,d,rt)));
end
fclose(fid); disp('diag2 done');
