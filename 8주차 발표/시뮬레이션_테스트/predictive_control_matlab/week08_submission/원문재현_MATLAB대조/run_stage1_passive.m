% 1단계: 수동 TLCD Python–MATLAB 시계열 대조. 판정 기준은 사전고정_판정기준.md (실행 전 고정). 허용오차 1e-6.
here = fileparts(mfilename('fullpath'));
recs = {'01','02','03','04','11','13','14','15'}; damps = {'D0','D3','D4'};
tol = 1e-6; dt = 0.01; fid = fopen(fullfile(here,'matlab_out','stage1_report.txt'),'w');
allpass = true; hdr = 'rec,case,sig,window,e2,ep,ind_relmax\n'; fprintf(fid,hdr); fprintf(hdr);
for r = 1:numel(recs)
    a = readmatrix(fullfile(here,'inputs',['PEER' recs{r} '.csv'])); x = a(:,1); y = a(:,2);
    cases = [{'none','D0'}; [repmat({'passive'},3,1), damps(:)]];
    for c = 1:size(cases,1)
        o = tlcd_sim(x,y,dt,struct('case',cases{c,1},'damp',cases{c,2}));
        if strcmp(cases{c,1},'none'), tag = 'none'; else, tag = ['passive_' cases{c,2}]; end
        P = readmatrix(fullfile(here,'python_ref',['PEER' recs{r} '_' tag '.csv']));
        M = [o.ux o.uy o.th]; writematrix(M,fullfile(here,'matlab_out',['PEER' recs{r} '_' tag '.csv']));
        names = {'ux','uy','th'}; 
        for w = 1:2
            n = size(P,1) - (w==2)*1000; wn = {'E0','E1'};
            indrel = 0;
            for s = 1:3
                sp = P(1:n,s); sm = M(1:n,s);
                e2 = norm(sm-sp)/norm(sp); ep = max(abs(sm-sp))/max(abs(sp));
                Ip = [max(abs(sp)), sqrt(mean(sp.^2))]; Im = [max(abs(sm)), sqrt(mean(sm.^2))];
                ir = max(abs(Im-Ip)./abs(Ip)); indrel = max(indrel, ir);
                ok = e2 <= tol && ep <= tol && ir <= tol; allpass = allpass && ok;
                line = sprintf('%s,%s,%s,%s,%.3e,%.3e,%.3e%s\n',recs{r},tag,names{s},wn{w},e2,ep,ir,ternary(ok,'',',FAIL'));
                fprintf(fid,'%s',line); fprintf('%s',line);
            end
        end
    end
end
fprintf(fid,'ALLPASS=%d\n',allpass); fprintf('ALLPASS=%d\n',allpass); fclose(fid);
function s = ternary(c,a,b), if c, s=a; else, s=b; end, end
