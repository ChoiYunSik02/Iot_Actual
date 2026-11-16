% 3단계: RS-TLCD Python–MATLAB 대조. 기준: 사전고정_판정기준_3단계_RSTLCD.md (실행 전 고정, 허용오차 1e-6).
here = fileparts(mfilename('fullpath'));
recs = {'01','02','03','04','11','13','14','15'}; damps = {'D0','D3','D4'}; rts = {'RA','RB'};
tol = 1e-6; dt = 0.01; fid = fopen(fullfile(here,'matlab_out','stage3_report.txt'),'w');
allpass = true; minm = inf; pr = @(varargin) fprintf(fid, varargin{:});
pr('rec,damp,rot,item,detail,value,flag\n');
for r = 1:numel(recs)
    a = readmatrix(fullfile(here,'inputs',['PEER' recs{r} '.csv'])); x = a(:,1); y = a(:,2);
    for c = 1:numel(damps)
      for q = 1:numel(rts)
        o = tlcd_sim(x,y,dt,struct('case','rstlcd','damp',damps{c},'cos_twice',strcmp(rts{q},'RA'))); minm = min(minm,o.minmargin);
        base = fullfile(here,'python_ref_r',['PEER' recs{r} '_rs' rts{q} '_' damps{c}]);
        P = readmatrix([base '_resp.csv']); Fc = readmatrix([base '_fcmd.csv']); Tc = readmatrix([base '_tcmd.csv']); Kc = readmatrix([base '_kcmd.csv']);
        tag = sprintf('%s,%s,%s',recs{r},damps{c},rts{q});
        ok = isequal(Fc(:,1),o.f_cmd(:,1)) && max(abs([Fc(:,2)-o.f_cmd(:,2); Fc(:,3)-o.f_cmd(:,3)])) <= 1e-9; allpass = allpass && ok;
        pr('%s,fcmd,n=%d,%d,%s\n',tag,size(Fc,1),ok,tern(ok));
        ok = isequal(Tc(:,1),o.th_cmd(:,1)) && max(abs(Tc(:,2)-o.th_cmd(:,2))) <= 1e-9; allpass = allpass && ok;
        pr('%s,thcmd,n=%d,%d,%s\n',tag,size(Tc,1),ok,tern(ok));
        ok = isequal(Kc(:,1),o.k_cmd(:,1)) && isequal(Kc(:,2),o.k_cmd(:,2)); allpass = allpass && ok;
        pr('%s,kcmd,n=%d,%d,%s\n',tag,size(Kc,1),ok,tern(ok));
        e2f = norm(o.fx-P(:,4))/norm(P(:,4)); e2t = norm(o.theta-P(:,5))/norm(P(:,5)); ok = e2f <= tol && e2t <= tol && isequal(o.kx,P(:,6)); allpass = allpass && ok;
        pr('%s,state,f_dev e2 / theta e2 / kappa identical,%.3e/%.3e/%d,%s\n',tag,e2f,e2t,isequal(o.kx,P(:,6)),tern(ok));
        R = [o.ux o.uy o.th]; names = {'ux','uy','th'}; wn = {'E0','E1'};
        for w = 1:2
            n = size(P,1) - (w==2)*1000;
            for s = 1:3
                sp = P(1:n,s); sm = R(1:n,s);
                e2 = norm(sm-sp)/norm(sp); ep = max(abs(sm-sp))/max(abs(sp));
                Ip = [max(abs(sp)), sqrt(mean(sp.^2))]; Im = [max(abs(sm)), sqrt(mean(sm.^2))]; ir = max(abs(Im-Ip)./abs(Ip));
                ok = e2 <= tol && ep <= tol && ir <= tol; allpass = allpass && ok;
                pr('%s,%s,%s e2/ep/ind,%.3e/%.3e/%.3e,%s\n',tag,names{s},wn{w},e2,ep,ir,tern(ok));
            end
        end
        fprintf('done %s\n',tag);
      end
    end
end
pr('MIN_WAVELET_MARGIN,,,,,%.3e,\n',minm); pr('ALLPASS=%d\n',allpass); fprintf('ALLPASS=%d min_margin=%.3e\n',allpass,minm); fclose(fid);
function s = tern(ok), if ok, s=''; else, s='FAIL'; end, end
