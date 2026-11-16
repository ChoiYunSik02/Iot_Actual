function man = read_manifest(file)
% READ_MANIFEST  data/record_manifest.csv → struct of cellstr 열 (UTF-8 BOM 처리, 따옴표 안 쉼표 허용).
txt = fileread(file);
if numel(txt) >= 3 && all(double(txt(1:3)) == [239 187 191]), txt = txt(4:end); end
if ~isempty(txt) && double(txt(1)) == 65279, txt = txt(2:end); end
lines = regexp(txt, '\r?\n', 'split'); lines = lines(~cellfun(@isempty, lines));
hdr = split_csv(lines{1});
man = struct();
for c = 1:numel(hdr), man.(hdr{c}) = cell(numel(lines)-1, 1); end
for r = 2:numel(lines)
    v = split_csv(lines{r});
    for c = 1:numel(hdr), man.(hdr{c}){r-1} = v{c}; end
end
end

function v = split_csv(s)
v = {}; cur = ''; q = false;
for k = 1:numel(s)
    ch = s(k);
    if ch == '"', q = ~q;
    elseif ch == ',' && ~q, v{end+1} = cur; cur = ''; %#ok<AGROW>
    else, cur(end+1) = ch; %#ok<AGROW>
    end
end
v{end+1} = cur;
end
