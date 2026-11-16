function run_angle_ai_simulink(datadir, recs, policies)
% Simulink 모델로 15기록 실행 후 지표 CSV 저장, 스크립트 결과(matlab_angle_*_metrics.csv)와 비교
% 사용: run_angle_ai_simulink('C:\Users\cys\Desktop\iot-actuator-week08\peer_records_table2', 1:15, [1 2])
if nargin<2, recs=1:15; end; if nargin<3, policies=[1 2]; end
here=fileparts(mfilename('fullpath')); addpath(here); cd(here);
if ~exist('rs_tlcd_angle_ai.slx','file'), build_angle_ai_model(); end
load_system('rs_tlcd_angle_ai');
T=readtab_(fullfile(datadir,'records_table2.csv')); names={'R','AI','W13'};
for pol=policies
  met=[];
  for r=recs
    [ax,dt]=readAT2(fullfile(datadir,T.x{r})); [ay,~]=readAT2(fullfile(datadir,T.y{r}));
    n=min(numel(ax),numel(ay)); ax=ax(1:n)*0.35/max(abs(ax)); ay=ay(1:n)*0.35/max(abs(ay));
    assignin('base','SIM_DT',dt); assignin('base','SIM_T',n); assignin('base','SIM_TEND',(n-1)*dt);
    assignin('base','SIM_AG',[(0:n-1)'*dt ax(:) ay(:)]); assignin('base','POLICY',pol);
    clear sim_ctrl_step
    out=sim('rs_tlcd_angle_ai','ReturnWorkspaceOutputs','on');
    y=squeeze(out.get('SIM_Y')); if size(y,1)==3 && size(y,2)~=3, y=y.'; end; if size(y,1)>n, y=y(1:n,:); end; s=[100 100 1e4]; a=abs(y).*s; rr=sqrt(mean(y.^2,1)).*s;
    met=[met; r max(a(:,1)) rr(1) max(a(:,2)) rr(2) max(a(:,3)) rr(3)]; %#ok<AGROW>
    fprintf('Simulink %s rec %d done (%d steps)\n',names{pol},r,size(y,1));
  end
  f=fullfile(here,sprintf('simulink_angle_%s_metrics.csv',names{pol}));
  fid=fopen(f,'w'); fprintf(fid,'no,Xmax,Xrms,Ymax,Yrms,thmax,thrms\n'); fprintf(fid,'%d,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g\n',met'); fclose(fid);
  ref=fullfile(fileparts(here),'angle_ai_v1',sprintf('matlab_angle_%s_metrics.csv',names{pol}));
  if exist(ref,'file'), R=readmatrix(ref); [~,ia]=ismember(met(:,1),R(:,1)); d=max(abs(met(:,2:end)./R(ia,2:end)-1),[],'all')*100; fprintf('%s: 스크립트 대비 최대 상대차 %.2e %%\n',names{pol},d); end
end
fprintf('SIMULINK_DONE\n');
end
function T=readtab_(f)
fid=fopen(f,'r'); fgetl(fid); T.x={}; T.y={};
while true
    l=fgetl(fid); if ~ischar(l), break; end
    if isempty(strtrim(l)), continue; end
    c=strsplit(strtrim(l),','); T.x{end+1}=strtrim(c{end-1}); T.y{end+1}=strtrim(c{end});
end
fclose(fid);
end
function [a,dt]=readAT2(f)
txt=fileread(f); L=regexp(txt,'\r?\n','split'); tok=regexp(L{4},'NPTS=\s*(\d+),\s*DT=\s*([\d.]+)','tokens','once');
n=str2double(tok{1}); dt=str2double(tok{2}); v=sscanf(strjoin(L(5:end),' '),'%f'); a=v(1:n)*9.80665;
end
