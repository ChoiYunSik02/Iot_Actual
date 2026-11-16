function pv = run_provenance()
% RUN_PROVENANCE  실행 기록: 브랜치·커밋·작업트리 변경 여부·코드 요약 해시·실행 환경.
%  git 명령이 없거나 zip으로 받은 폴더면 .git/HEAD를 직접 읽고, 그것도 없으면 'unknown'으로 둔다.
%  digest : src/ (sl 포함)·tests/·config/scales.json 파일 해시를 이어 붙인 SHA-256 앞 16자리
%           (A~C 관문이 검증한 코드와 D 실행 코드가 같은지 확인하는 데 쓴다)
%  config_hash : config/experiment.json 해시 (개발 설정 변경 추적, config/CHANGELOG.md와 대조)
%  dirty : 코드·설정(src, tests, scripts, experiment.json, scales.json, 실행기)에 커밋 안 된 변경이 있는지. 결과 폴더 변경은 제외.
root = pc_root(); repo = fileparts(root);
pv = struct('branch', 'unknown', 'commit', 'unknown', 'dirty', 'unknown', 'env', env_string(), 'time', datestr(now, 31));
[st, out] = system(sprintf('git -C "%s" rev-parse --abbrev-ref HEAD', repo));
if st == 0
    pv.branch = strtrim(out);
    [~, out] = system(sprintf('git -C "%s" rev-parse HEAD', repo)); pv.commit = strtrim(out);
    [~, out] = system(sprintf('git -C "%s" status --porcelain -- predictive_control_matlab/src predictive_control_matlab/tests predictive_control_matlab/scripts predictive_control_matlab/config/experiment.json predictive_control_matlab/config/scales.json predictive_control_matlab/run_week08_laptop.m', repo));
    pv.dirty = ~isempty(strtrim(out));
else
    hf = fullfile(repo, '.git', 'HEAD');
    if exist(hf, 'file')
        h = strtrim(fileread(hf));
        if strncmp(h, 'ref: ', 5)
            ref = h(6:end); pv.branch = regexprep(ref, '^refs/heads/', '');
            rf = fullfile(repo, '.git', strrep(ref, '/', filesep));
            if exist(rf, 'file'), pv.commit = strtrim(fileread(rf)); end
        else
            pv.commit = h;
        end
    end
end
fs = [list_files(fullfile(root, 'src')); list_files(fullfile(root, 'tests')); {fullfile(root, 'config', 'scales.json')}];
cat_ = '';
for k = 1:numel(fs), cat_ = [cat_ strrep(fs{k}, [root filesep], '') ':' sha256_file(fs{k}) ';']; end %#ok<AGROW>
pv.digest = sha256_str(cat_);
pv.config_hash = sha256_file(fullfile(root, 'config', 'experiment.json'));
end

function fs = list_files(d)
s = dir(fullfile(d, '*.m')); fs = cellfun(@(n) fullfile(d, n), {s.name}', 'UniformOutput', false);
sub = dir(d); sub = sub([sub.isdir] & ~ismember({sub.name}, {'.', '..'}));
for k = 1:numel(sub), fs = [fs; list_files(fullfile(d, sub(k).name))]; end %#ok<AGROW>
fs = sort(fs);
end

function s = sha256_file(p)
fid = fopen(p, 'r'); b = fread(fid, inf, '*uint8'); fclose(fid);
s = sha256_bytes(b(:)');
end

function s = sha256_str(t)
s = sha256_bytes(uint8(unicode2native(t, 'UTF-8')));
end

function s = sha256_bytes(b)
if exist('OCTAVE_VERSION', 'builtin') > 0
    s = hash('sha256', char(b));
else
    md = java.security.MessageDigest.getInstance('SHA-256');
    s = lower(reshape(dec2hex(typecast(md.digest(b), 'uint8'), 2)', 1, []));
end
s = s(1:16);
end
