S = load('recs.mat'); fid = fopen('out.csv','w'); t0 = tic;
pols = {'U','R','PEAK'};
for j = 0:32
    r = S.(sprintf('r%d',j)); ax = double(r.agx(:)); ay = double(r.agy(:)); dt = double(r.dt);
    for p = 1:3
        switch pols{p}
            case 'U',    o = struct('case','none');
            case 'R',    o = struct('case','rstlcd','fpol','law','thpol','law');
            case 'PEAK', o = struct('case','rstlcd','fpol','law','thpol','peak');
        end
        q = rstlcd_peak(ax, ay, dt, o);
        fprintf(fid,'%d,%s,%.8g,%.8g,%.8g,%.8g,%.8g,%.8g\n', j, pols{p}, 100*max(abs(q.ux)),100*rms(q.ux),100*max(abs(q.uy)),100*rms(q.uy),1e4*max(abs(q.th)),1e4*rms(q.th));
    end
    fprintf('%d %.0fs\n', j, toc(t0));
end
fclose(fid);
