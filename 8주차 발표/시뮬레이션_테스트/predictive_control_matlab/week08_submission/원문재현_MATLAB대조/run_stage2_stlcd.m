% 2단계: S-TLCD Python–MATLAB 대조. 기준: 사전고정_판정기준_2단계_STLCD.md (실행 전 고정, 허용오차 1e-6).
here = fileparts(mfilename('fullpath'));
recs = {'01','02','03','04','11','13','14','15'}; damps = {'D0','D3','D4'};
tol = 1e-6; dt = 0.01; fid = fopen(fullfile(here,'matlab_out','stage2_report.txt'),'w');
allpass = true; minm = inf;
pr = @(varargin) fprintf(fid, varargin{:}); 
pr('rec,damp,item,detail,value,flag\n');
for r = 1:numel(recs)
    a = readmatrix(fullfile(here,'inputs',['PEER' recs{r} '.csv'])); x = a(:,1); y = a(:,2);
    for c = 1:numel(damps)
        o = tlcd_sim(x,y,dt,struct('case','stlcd','damp',damps{c})); minm = min(minm,o.minmargin);
        base = fullfile(here,'python_ref_s',['PEER' recs{r} '_stlcd_' damps{c}]);
        P = readmatrix([base '_resp.csv']); Fc = readmatrix([base '_fcmd.csv']); Kc = readmatrix([base '_kcmd.csv']);
        % 1) 명령 스텝/값
        okstep = isequal(Fc(:,1), o.f_cmd(:,1)); df = max(abs([Fc(:,2)-o.f_cmd(:,2); Fc(:,3)-o.f_cmd(:,3)]));
        ok = okstep && df <= 1e-9; allpass = allpass && ok;
        pr('%s,%s,fcmd,n=%d step_equal=%d,%.3e,%s\n',recs{r},damps{c},size(Fc,1),okstep,df,tern(ok));
        % 2) κ 스텝/값 (완전 일치)
        ok = isequal(Kc, o.k_cmd); allpass = allpass && ok;
        pr('%s,%s,kcmd,n=%d identical=%d,%d,%s\n',recs{r},damps{c},size(Kc,1),ok,ok,tern(ok));
        % 3) 장치 상태 시계열
        M = [o.fx o.fy o.kx o.ky]; Pm = P(:,4:7);
        for s = 1:2
            e2 = norm(M(:,s)-Pm(:,s))/norm(Pm(:,s)); ok = e2 <= tol; allpass = allpass && ok;
            nm = {'f_dev_x','f_dev_y'}; pr('%s,%s,%s,e2,%.3e,%s\n',recs{r},damps{c},nm{s},e2,tern(ok));
        end
        ok = isequal(M(:,3),Pm(:,3)) && isequal(M(:,4),Pm(:,4)); allpass = allpass && ok;
        pr('%s,%s,kappa_series,identical,%d,%s\n',recs{r},damps{c},ok,tern(ok));
        % 4) 건물 응답 E0/E1
        R = [o.ux o.uy o.th]; names = {'ux','uy','th'}; wn = {'E0','E1'};
        for w = 1:2
            n = size(P,1) - (w==2)*1000;
            for s = 1:3
                sp = P(1:n,s); sm = R(1:n,s);
                e2 = norm(sm-sp)/norm(sp); ep = max(abs(sm-sp))/max(abs(sp));
                Ip = [max(abs(sp)), sqrt(mean(sp.^2))]; Im = [max(abs(sm)), sqrt(mean(sm.^2))]; ir = max(abs(Im-Ip)./abs(Ip));
                ok = e2 <= tol && ep <= tol && ir <= tol; allpass = allpass && ok;
                pr('%s,%s,%s,%s e2/ep/ind,%.3e/%.3e/%.3e,%s\n',recs{r},damps{c},names{s},wn{w},e2,ep,ir,tern(ok));
            end
        end
        fprintf('done %s %s\n',recs{r},damps{c});
    end
end
pr('MIN_WAVELET_MARGIN,,,,%.3e,\n',minm); pr('ALLPASS=%d\n',allpass); fprintf('ALLPASS=%d min_margin=%.3e\n',allpass,minm); fclose(fid);
function s = tern(ok), if ok, s=''; else, s='FAIL'; end, end
