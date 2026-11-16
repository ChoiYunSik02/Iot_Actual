function h = code_hash(root)
% CODE_HASH  src/·scripts/·config/experiment.json 파일별 SHA-256 앞 16자리 목록 (모델·결과에 함께 저장).
fs = [dir(fullfile(root, 'src', '*.m')); dir(fullfile(root, 'scripts', '*.m')); dir(fullfile(root, 'config', 'experiment.json'))];
h = cell(numel(fs), 2);
for k = 1:numel(fs)
    p = fullfile(fs(k).folder, fs(k).name);
    h{k,1} = strrep(p, [root filesep], '');
    h{k,2} = sha256_file(p);
end
end

function s = sha256_file(p)
fid = fopen(p, 'r'); b = fread(fid, inf, '*uint8'); fclose(fid);
if exist('OCTAVE_VERSION', 'builtin') > 0
    s = hash('sha256', char(b'));
else
    md = java.security.MessageDigest.getInstance('SHA-256');
    d = typecast(md.digest(b), 'uint8');
    s = lower(reshape(dec2hex(d, 2)', 1, []));
end
s = s(1:16);
end
