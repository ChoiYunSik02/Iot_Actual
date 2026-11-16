function write_check_csv(file, rows, env)
% WRITE_CHECK_CSV  {record, policy, item, value, threshold, pass} 셀 행렬 → CSV (env 열 포함).
d = fileparts(file); if ~exist(d, 'dir'), mkdir(d); end
fid = fopen(file, 'w');
fprintf(fid, 'env,record,policy,item,value,threshold,pass\n');
for k = 1:size(rows, 1)
    fprintf(fid, '%s,%s,%s,%s,%.6g,%.6g,%d\n', env, rows{k,1}, rows{k,2}, rows{k,3}, rows{k,4}, rows{k,5}, rows{k,6});
end
fclose(fid);
end
