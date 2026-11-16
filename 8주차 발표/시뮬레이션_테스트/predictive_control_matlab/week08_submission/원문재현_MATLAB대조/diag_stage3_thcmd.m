% 진단(사후): 3단계 thcmd 불합격 4건의 원인 확인. 판정 기준은 바꾸지 않으며 이 스크립트는 원인 규명용이다.
here = fileparts(mfilename('fullpath')); dt = 0.01;
recs = {'01','02','03','04','11','13','14','15'}; damps = {'D0','D3','D4'}; rts = {'RA','RB'};
fid = fopen(fullfile(here,'matlab_out','stage3_diag_thcmd.txt'),'w'); pr = @(varargin) fprintf(fid,varargin{:});
pr('rec,damp,rot,steps_equal,n,maxabsdiff_rad,step_at_max,th_py,th_ml,window_amp_m,rel_amp_err\n');
for r = 1:numel(recs)
  a = readmatrix(fullfile(here,'inputs',['PEER' recs{r} '.csv'])); x = a(:,1); y = a(:,2);
  for c = 1:numel(damps)
    for q = 1:numel(rts)
      o = tlcd_sim(x,y,dt,struct('case','rstlcd','damp',damps{c},'cos_twice',strcmp(rts{q},'RA')));
      base = fullfile(here,'python_ref_r',['PEER' recs{r} '_rs' rts{q} '_' damps{c}]);
      Tc = readmatrix([base '_tcmd.csv']); P = readmatrix([base '_resp.csv']);
      se = isequal(Tc(:,1),o.th_cmd(:,1)); d = abs(Tc(:,2)-o.th_cmd(:,2)); [m,k] = max(d);
      i = Tc(k,1); j0 = max(0,i-260); amp = max([max(abs(P(j0+1:i,1))), max(abs(P(j0+1:i,2)))]);
      pr('%s,%s,%s,%d,%d,%.3e,%d,%.12f,%.12f,%.3e,%.3e\n',recs{r},damps{c},rts{q},se,size(Tc,1),m,i,Tc(k,2),o.th_cmd(k,2),amp,m/max(Tc(k,2),realmin));
    end
  end
end
fclose(fid); disp('diag done');
