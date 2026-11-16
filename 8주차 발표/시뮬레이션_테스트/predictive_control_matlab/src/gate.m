function out = gate(action, stage, varargin)
% GATE  단계 관문 기록과 확인 (A·B·C·SL 통과 후에만 D).
%  gate('pass', 'B', info)      : results/gate_B.json 기록 (통과, 실행 기록, 근거 파일)
%  gate('fail', 'B', msg)       : 실패 기록 (기존 통과 파일은 지움)
%  gate('require', {'A','B','C','SL'}) : 모두 통과·MATLAB 실행·현재 코드 digest와 같은지 확인. 아니면 오류.
%    experiment.json이 관문 이후 바뀌었으면 config/CHANGELOG.md에 새 해시가 적혀 있어야 한다(변경 기록 의무).
root = pc_root(); gdir = fullfile(root, 'results');
switch action
    case {'pass', 'fail'}
        pv = run_provenance();
        g = struct('stage', stage, 'pass', strcmp(action, 'pass'), 'provenance', pv);
        if ~isempty(varargin), g.info = varargin{1}; end
        f = fullfile(gdir, ['gate_' stage out_tag() '.json']);
        fid = fopen(f, 'w'); fprintf(fid, '%s', jsonencode(g)); fclose(fid);
        out = g;
    case 'require'
        need = stage; pv = run_provenance(); bad = {};
        for k = 1:numel(need)
            f = fullfile(gdir, ['gate_' need{k} out_tag() '.json']);
            if ~exist(f, 'file'), bad{end+1} = sprintf('%s 관문 기록 없음', need{k}); continue; end %#ok<AGROW>
            g = jsondecode(fileread(f));
            if ~g.pass, bad{end+1} = sprintf('%s 실패 상태', need{k}); continue; end %#ok<AGROW>
            if isempty(strfind(g.provenance.env, 'MATLAB')) && isempty(out_tag()) %#ok<STREMP>
                bad{end+1} = sprintf('%s: MATLAB 실행 기록 아님 (%s)', need{k}, g.provenance.env); %#ok<AGROW>
            end
            if ~strcmp(g.provenance.digest, pv.digest)
                bad{end+1} = sprintf('%s: 검증 이후 코드가 바뀜 (digest %s → %s) — A~C 재실행 필요', need{k}, g.provenance.digest, pv.digest); %#ok<AGROW>
            end
            if ~strcmp(g.provenance.config_hash, pv.config_hash)
                cl = fullfile(root, 'config', 'CHANGELOG.md');
                if ~exist(cl, 'file') || isempty(strfind(fileread(cl), pv.config_hash)) %#ok<STREMP>
                    bad{end+1} = sprintf('%s 이후 experiment.json 변경(%s)이 config/CHANGELOG.md에 기록되지 않음', need{k}, pv.config_hash); %#ok<AGROW>
                end
            end
        end
        if ~isempty(bad), error('관문 미통과:\n  %s', strjoin(bad, '\n  ')); end
        out = pv;
    otherwise
        error('gate: %s', action);
end
end
